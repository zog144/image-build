"""Derive applications-v1 capabilities solely from selected package inventories.

This initial producer supports native Linux x86_64/aarch64 and CPython roots.
Only SONAMEs reachable directly in /usr/lib or /lib are advertised; private
plugins and the inspection host's libraries are never capabilities.
"""
import ast
import posixpath
import re
from pathlib import Path

from .application_software import compatibility
from .artifact_observations import scan
from .errors import ImageBuildError
from .filesystem import inventory

FIELD = 'application_software_compatibility'


def derive(built, architecture, *, readelf='readelf'):
    files = {}
    for record in built.values():
        root = Path(record['root']).resolve()
        if inventory(root) != record['outputs']:
            raise ImageBuildError('compatibility package inventory changed')
        for entry in record['outputs']:
            name = entry['path']
            if name in files and files[name][1] != entry:
                raise ImageBuildError('compatibility package collision: '+name)
            files[name] = (root, entry)

    def resolve(name):
        for _ in range(40):
            if name not in files:
                raise ImageBuildError('compatibility requires declared rootfs file: '+name)
            root, entry = files[name]
            if entry['kind'] != 'symlink':
                path = root/name
                if entry['kind'] != 'file' or path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ImageBuildError('compatibility file escapes package')
                return path
            target = entry['target']
            name = posixpath.normpath(target.lstrip('/') if target.startswith('/') else
                                     posixpath.join(posixpath.dirname(name), target))
            if name == '..' or name.startswith('../'):
                raise ImageBuildError('compatibility symlink escapes rootfs')
        raise ImageBuildError('compatibility symlink cycle')

    machine = {'x86_64': 62, 'aarch64': 183}.get(architecture)
    if machine is None:
        raise ImageBuildError('unsupported rootfs compatibility architecture')
    python = None
    configs = [n for n in files if re.fullmatch(r'usr/lib/python[^/]+/_sysconfigdata[^/]*\.py', n)]
    if len(configs) > 1:
        raise ImageBuildError('ambiguous rootfs Python ABI')
    if configs:
        node = ast.parse(resolve(configs[0]).read_text())
        values = [ast.literal_eval(n.value) for n in node.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'build_time_vars' for t in n.targets)]
        if len(values) != 1:
            raise ImageBuildError('missing literal rootfs Python configuration')
        config = values[0]
        version = config['VERSION']
        header = resolve('usr/include/python'+version+'/patchlevel.h').read_text()
        exact = re.findall(r'^#define\s+PY_VERSION\s+"([^"]+)"', header, re.M)
        if len(exact) != 1 or not exact[0].startswith(version+'.') or not config['SOABI'].startswith('cpython-'):
            raise ImageBuildError('inconsistent rootfs CPython metadata')
        executable = resolve('usr/bin/python'+version)
        with executable.open('rb') as stream:
            head = stream.read(20)
        if len(head) != 20 or head[:6] != b'\x7fELF\x02\x01' or int.from_bytes(head[18:20], 'little') != machine:
            raise ImageBuildError('rootfs Python architecture differs')
        python = dict(implementation='cpython', version=exact[0], soabi=config['SOABI'])
    elif any(re.fullmatch(r'usr/bin/python[0-9.]*', n) for n in files):
        raise ImageBuildError('Python present without declared ABI metadata')

    libraries = []
    for record in built.values():
        entries = [e for e in record['outputs'] if e['kind'] == 'file'
                   and posixpath.dirname(e['path']) in ('usr/lib', 'lib') and '.so' in posixpath.basename(e['path'])]
        for entry in entries:
            with resolve(entry['path']).open('rb') as stream:
                head = stream.read(20)
            if head.startswith(b'\x7fELF') and (len(head) != 20 or head[:6] != b'\x7fELF\x02\x01'
                    or int.from_bytes(head[18:20], 'little') != machine):
                raise ImageBuildError('rootfs library architecture differs')
        observed = scan(record['root'], entries, {}, readelf=readelf)
        if observed['issues']:
            raise ImageBuildError('rootfs library inspection incomplete')
        for relation in observed['relationships']:
            if relation['relation'] == 'provides-soname':
                soname = relation['target']['value']
                source = relation['subject']['path'].lstrip('/')
                if '/' in soname or resolve(posixpath.join(posixpath.dirname(source), soname)) != resolve(source):
                    raise ImageBuildError('rootfs SONAME is not reachable')
                libraries.append(soname)
    return compatibility(dict(schema=1, mount_contract='applications-v1', architecture=architecture,
                              python=python, libraries=libraries))


def validate_manifest(inputs, details):
    """A descriptor must be canonical and part of the immutable generation inputs."""
    if FIELD in inputs or FIELD in details:
        value = compatibility(inputs.get(FIELD))
        if inputs.get(FIELD) != value or details.get(FIELD) != value:
            raise ImageBuildError('rootfs compatibility descriptor is not frozen in generation inputs')

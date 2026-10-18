"""Replace inherited dependency outputs only in disposable build environments."""
from pathlib import Path

from .errors import ImageBuildError
from .filesystem import inventory
from .metadata import identity, relative

POLICY = 'replace-inherited-package-dependencies-v1'


def replacement_plan(toolchain, dependencies):
    """Bind old package identities before preparing or reusing a build output."""
    packages = toolchain.manifest.get('packages', {})
    selected = {}
    for name in sorted(set(dependencies) & set(packages)):
        record = packages[name]
        if ('inputs' not in record or 'outputs' not in record or
                record.get('identity') != identity({'inputs': record['inputs'], 'outputs': record['outputs']})):
            raise ImageBuildError('inherited dependency identity differs: '+name)
        selected[name] = record['identity']
    return {'policy': POLICY, 'packages': selected} if selected else {}


def remove_inherited(environment, toolchain, plan):
    """Validate the complete removal set before deleting any old package file.

    Shared non-directory ownership and composed files deliberately fail closed.
    Shared directories survive; exclusive directories are removed only if empty.
    The caller merges the new dependency outputs through the ordinary strict merger.
    """
    if not plan:
        return
    root = Path(environment)
    source = Path(toolchain.root).resolve()
    resolved = root.resolve()
    if (root.is_symlink() or not root.is_dir() or resolved.is_relative_to(source)
            or source.is_relative_to(resolved)):
        raise ImageBuildError('dependency replacement requires a separate staging root')
    if plan != replacement_plan(toolchain, plan.get('packages', {})):
        raise ImageBuildError('inherited dependency replacement plan changed')
    packages = toolchain.manifest['packages']
    base = {e['path']: e for e in toolchain.manifest['outputs']}
    actual = {e['path']: e for e in inventory(root)}
    owners = {}
    for name, record in packages.items():
        for entry in record['outputs']:
            owners.setdefault(entry['path'], set()).add(name)
    removals = []
    directories = []
    for name in plan['packages']:
        for entry in packages[name]['outputs']:
            path_name = relative(entry['path'])
            path = root/path_name
            if any((root/p).is_symlink() for p in path.relative_to(root).parents):
                raise ImageBuildError('inherited dependency parent is a symlink: '+path_name)
            if entry['kind'] == 'directory':
                if actual.get(path_name, {}).get('kind') != 'directory':
                    raise ImageBuildError('inherited dependency directory changed: '+path_name)
                if owners[path_name] == {name}:
                    directories.append(path)
                continue
            if owners[path_name] != {name}:
                raise ImageBuildError('inherited dependency has shared file ownership: '+path_name)
            if base.get(path_name) != entry or actual.get(path_name) != entry:
                raise ImageBuildError('inherited dependency file changed: '+path_name)
            removals.append(path)
    # No file is removed until every package's old inventory has been checked.
    for path in removals:
        _remove(path)
    for path in sorted(set(directories), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            _remove(path, directory=True)


def _remove(path, *, directory=False):
    mode = path.parent.stat().st_mode & 0o7777
    path.parent.chmod(mode | 0o700)
    try:
        path.rmdir() if directory else path.unlink()
    finally:
        path.parent.chmod(mode)

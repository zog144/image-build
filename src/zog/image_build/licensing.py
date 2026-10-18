"""Version-bound upstream declarations, retained evidence and offline release gates.

No first-party license is inferred for upstream content. Legacy recipes remain
readable and explicitly unresolved; new catalogue stages require license.py.
"""
import argparse
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from .errors import ImageBuildError
from .metadata import literal, identity
from .filesystem import digest, inventory, write_json

# Supported SPDX identifiers are deliberately explicit; extend after reviewing
# a new upstream declaration. LicenseRef covers custom or unmapped terms.
LICENSE_IDS = set('MPL-2.0 curl 0BSD MIT MIT-0 MIT-open-group ISC X11 X11-distribute-modifications-variant HPND-sell-variant SMLNJ BSD-2-Clause BSD-3-Clause BSD-4-Clause BSD-3-Clause-Attribution Apache-2.0 GPL-1.0-only GPL-1.0-or-later GPL-2.0-only GPL-2.0-or-later GPL-3.0-only GPL-3.0-or-later LGPL-2.0-only LGPL-2.0-or-later LGPL-2.1-only LGPL-2.1-or-later LGPL-3.0-only LGPL-3.0-or-later GFDL-1.2-only GFDL-1.2-or-later GFDL-1.3-only GFDL-1.3-or-later Artistic-1.0 Artistic-1.0-Perl Artistic-2.0 Python-2.0 PSF-2.0 TCL Zlib bzip2-1.0.6 BSL-1.0 Unlicense CC0-1.0 Unicode-3.0 CDLA-Permissive-2.0 MPL-1.1 BSD-4-Clause-UC'.split())
EXCEPTION_IDS = {'GCC-exception-3.1','Bison-exception-2.2','Linux-syscall-note','Autoconf-exception-3.0','LLVM-exception'}
SUPPLEMENTARY_NOTICE_CONTRACT = 'image-build-supplementary-notice-v1'
NOTICE_ORIGIN_ARCHIVE = 'original-source-archive'
NOTICE_ORIGIN_RAW = 'declared-raw-source'
NOTICE_ORIGIN_SUPPLEMENTARY = 'independently-retrieved-upstream-notice'
CANONICAL_WEB_PROVENANCE_CONTRACT = 'image-build-canonical-web-notice-provenance-v1'
CANONICAL_WEB_NOTICE_URLS = {
    'http://www.apache.org/licenses/LICENSE-2.0': 'https://www.apache.org/licenses/LICENSE-2.0.txt',
}


def expression(value):
    if value is None: return
    if not isinstance(value,str) or not value or '\n' in value: raise ImageBuildError('invalid license expression')
    tokens=re.findall(r'[A-Za-z0-9.-]+|[()]|\S',value);position=0
    def atom():
        nonlocal position
        if position>=len(tokens): raise ImageBuildError('incomplete license expression')
        token=tokens[position];position+=1
        if token=='(':
            compound()
            if position>=len(tokens) or tokens[position]!=')':raise ImageBuildError('unclosed license expression')
            position+=1;return
        if token not in LICENSE_IDS and not re.fullmatch(r'LicenseRef-[A-Za-z0-9.-]+',token):
            raise ImageBuildError('unknown license identifier: '+token)
        if position<len(tokens) and tokens[position]=='WITH':
            position+=1
            if position>=len(tokens) or tokens[position] not in EXCEPTION_IDS:raise ImageBuildError('unknown license exception')
            position+=1
    def compound():
        nonlocal position
        atom()
        while position<len(tokens) and tokens[position] in ('AND','OR'):
            position+=1;atom()
    compound()
    if position!=len(tokens):raise ImageBuildError('malformed license expression')


def safe_path(value):
    if not isinstance(value,str) or not value or '\\' in value or '\0' in value or value.startswith('/') or any(p in ('','..','.') for p in value.split('/')):
        raise ImageBuildError('unsafe license evidence path')
    return value


def _validate_git_notice_source(source, upstream):
    """Bind immutable raw GitHub URLs to the declared repository/revision/path."""
    try:
        raw=urlsplit(source['url'])
        repository=urlsplit(upstream['repository'])
    except ValueError as error:
        raise ImageBuildError('invalid supplementary notice upstream provenance') from error
    if raw.hostname!='raw.githubusercontent.com':
        return
    if (raw.scheme!='https' or raw.netloc!='raw.githubusercontent.com' or raw.query or
            raw.fragment or '%' in raw.path or '\\' in raw.path):
        raise ImageBuildError('ambiguous raw GitHub supplementary notice URL')
    if (repository.scheme!='https' or repository.netloc!='github.com' or repository.query or
            repository.fragment or '%' in repository.path or '\\' in repository.path):
        raise ImageBuildError('invalid raw GitHub supplementary notice repository')
    parts=repository.path.split('/')
    if len(parts)!=3 or not parts[1] or not parts[2]:
        raise ImageBuildError('invalid raw GitHub supplementary notice repository')
    expected_path='/'+parts[1]+'/'+parts[2]+'/'+upstream['revision']+'/'+upstream['path']
    if raw.path!=expected_path:
        raise ImageBuildError('raw GitHub supplementary notice provenance mismatch')


def _supplementary_notice(item, record=None, package_sources=None):
    git_fields={'contract','id','source','upstream','path','scope','notes'}
    web_fields={'contract','id','source','canonical_web','path','scope','notes'}
    if (not isinstance(item,dict) or set(item) not in (git_fields,web_fields) or
            item['contract']!=SUPPLEMENTARY_NOTICE_CONTRACT):
        raise ImageBuildError('unsupported supplementary notice')
    if not isinstance(item['id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',item['id']):
        raise ImageBuildError('invalid supplementary notice identity')
    source=item['source']
    if (not isinstance(source,dict) or set(source)!={'url','sha256','destination','archive'} or
            source['archive'] is not False or not isinstance(source['url'],str) or
            not source['url'].startswith('https://') or
            not isinstance(source['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',source['sha256'])):
        raise ImageBuildError('invalid supplementary notice source')
    safe_path(source['destination'])
    path=safe_path(item['path'])
    if Path(source['destination']).name != path or '/' in path:
        raise ImageBuildError('supplementary notice path must name the raw source file')
    if 'upstream' in item:
        upstream=item['upstream']
        if (not isinstance(upstream,dict) or set(upstream)!={'repository','revision','path'} or
                not isinstance(upstream['repository'],str) or not upstream['repository'].startswith('https://') or
                not isinstance(upstream['revision'],str) or not re.fullmatch('[0-9a-f]{40}',upstream['revision'])):
            raise ImageBuildError('invalid supplementary notice upstream provenance')
        safe_path(upstream['path'])
        if Path(upstream['path']).name != path:
            raise ImageBuildError('supplementary notice path differs from upstream path')
        _validate_git_notice_source(source,upstream)
    else:
        provenance=item['canonical_web']
        if (not isinstance(provenance,dict) or
                set(provenance)!={'contract','incorporated_url','incorporated_by'} or
                provenance['contract']!=CANONICAL_WEB_PROVENANCE_CONTRACT or
                CANONICAL_WEB_NOTICE_URLS.get(provenance['incorporated_url'])!=source['url']):
            raise ImageBuildError('invalid canonical web notice provenance')
        binding=provenance['incorporated_by']
        primary_fields={'source_sha256','path','sha256'}
        nested_fields={'source','path','sha256'}
        if (not isinstance(binding,dict) or set(binding) not in (primary_fields,nested_fields) or
                not isinstance(binding['sha256'],str) or
                not re.fullmatch('[0-9a-f]{64}',binding['sha256'])):
            raise ImageBuildError('invalid canonical web incorporation binding')
        safe_path(binding['path'])
        if source['url'].rstrip('/').rsplit('/',1)[-1] != path:
            raise ImageBuildError('canonical web notice filename differs from source URL')
        if set(binding)==primary_fields:
            if (not isinstance(binding['source_sha256'],str) or
                    not re.fullmatch('[0-9a-f]{64}',binding['source_sha256'])):
                raise ImageBuildError('invalid canonical web incorporation binding')
            if record is not None and binding['source_sha256']!=record['source']['sha256']:
                raise ImageBuildError('canonical web notice is not bound to the primary source')
        else:
            nested=binding['source']
            if (not isinstance(nested,dict) or set(nested)!={'url','sha256','destination','archive'} or
                    nested['archive'] is not True or not isinstance(nested['url'],str) or
                    not nested['url'].startswith('https://') or
                    not isinstance(nested['sha256'],str) or
                    not re.fullmatch('[0-9a-f]{64}',nested['sha256'])):
                raise ImageBuildError('invalid canonical web nested source')
            safe_path(nested['destination'])
            if record is not None and (nested['sha256']==record['source']['sha256'] or
                    nested['url']==record['source']['url']):
                raise ImageBuildError('canonical web nested source cannot be the primary source')
            if not isinstance(package_sources,(list,tuple)):
                raise ImageBuildError('canonical web nested source requires selected package sources')
            matches=[candidate for candidate in package_sources if candidate==nested]
            if len(matches)!=1:
                raise ImageBuildError('canonical web nested source must match exactly one selected source')
    if not isinstance(item['scope'],str) or not item['scope']:
        raise ImageBuildError('missing supplementary notice scope')
    if not isinstance(item['notes'],str):
        raise ImageBuildError('invalid supplementary notice notes')
    return item


def _supplementary_provenance_class(item):
    return 'exact-git-revision' if 'upstream' in item else 'source-incorporated-canonical-web-text'


def supplementary_notices(record, package_sources=None):
    notices=record.get('supplementary_notices',[])
    if not isinstance(notices,list):raise ImageBuildError('invalid supplementary notices')
    seen_ids=set();seen_destinations=set();seen_declarations=set()
    for item in notices:
        _supplementary_notice(item,record,package_sources)
        declaration=json.dumps(item,sort_keys=True,separators=(',',':'))
        if declaration in seen_declarations:
            raise ImageBuildError('duplicate supplementary notice declaration')
        if item['id'] in seen_ids:
            raise ImageBuildError('duplicate supplementary notice identity')
        destination=item['source']['destination']
        if destination in seen_destinations:
            raise ImageBuildError('conflicting supplementary notice destination')
        seen_declarations.add(declaration);seen_ids.add(item['id']);seen_destinations.add(destination)
    return notices


def _canonical_web_archive_source(item, record, package_sources):
    if not isinstance(package_sources,(list,tuple)):
        raise ImageBuildError('canonical web provenance requires selected package sources')
    binding=item['canonical_web']['incorporated_by']
    if 'source' in binding:
        nested=binding['source']
        matches=[source for source in package_sources if source==nested]
        if len(matches)!=1:
            raise ImageBuildError('canonical web nested source must match exactly one selected source')
        if nested['sha256']==record['source']['sha256'] or nested['url']==record['source']['url']:
            raise ImageBuildError('canonical web nested source cannot be the primary source')
        return matches[0]
    if binding['source_sha256']!=record['source']['sha256']:
        raise ImageBuildError('canonical web notice is not bound to the primary source')
    primary=[source for source in package_sources
             if source.get('sha256')==binding['source_sha256'] and
                source.get('url')==record['source']['url'] and source.get('archive') is True]
    if len(primary)!=1:
        raise ImageBuildError('canonical web notice primary source binding is ambiguous')
    return primary[0]


def _verify_canonical_web_binding(item, record, package_sources, source_store):
    if 'canonical_web' not in item:
        return
    import tarfile
    binding=item['canonical_web']['incorporated_by']
    source_spec=_canonical_web_archive_source(item,record,package_sources)
    archive_path=Path(source_store)/source_spec['sha256']
    if archive_path.is_symlink() or not archive_path.is_file() or digest(archive_path)!=source_spec['sha256']:
        raise ImageBuildError('canonical web notice source archive missing or changed')
    try:
        with tarfile.open(archive_path) as archive:
            member=archive.getmember(binding['path'])
            if not member.isfile():
                raise ImageBuildError('canonical web incorporation evidence is not a regular file')
            data=archive.extractfile(member).read()
    except (KeyError, tarfile.TarError) as error:
        raise ImageBuildError('canonical web incorporation evidence is missing') from error
    import hashlib
    if hashlib.sha256(data).hexdigest()!=binding['sha256']:
        raise ImageBuildError('canonical web incorporation evidence changed')
    if item['canonical_web']['incorporated_url'].encode() not in data:
        raise ImageBuildError('canonical web URL is not incorporated by the bound source evidence')

def _supplementary_installed_path(base,item):
    return base+'/supplementary/'+safe_path(item['id'])+'/'+item['source']['sha256']+'/'+safe_path(item['path'])


def validate(record, package_sources=None):
    required={'schema','package','version','source','status','expression','scope','evidence','components','patches','notes'}
    allowed=required|{'supplementary_notices'}
    if not isinstance(record,dict) or set(record) not in (required,allowed) or record['schema']!=1:
        raise ImageBuildError('unsupported license record')
    for field in ('package','version','scope'):
        if not isinstance(record[field],str) or not record[field]:raise ImageBuildError('missing license identity/scope')
    if record['status'] not in ('declared','reviewed','unresolved'):raise ImageBuildError('invalid license review status')
    expression(record['expression'])
    source=record['source']
    if not isinstance(source,dict) or set(source)!={'url','sha256'} or not isinstance(source['url'],str) or not source['url'].startswith(('https://','file:')):
        raise ImageBuildError('invalid license source')
    if source['sha256'] is not None and (not isinstance(source['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',source['sha256'])):raise ImageBuildError('invalid license source hash')
    if not isinstance(record['notes'],list) or any(not isinstance(n,str) for n in record['notes']):raise ImageBuildError('invalid license notes')
    notices=supplementary_notices(record,package_sources)
    if not isinstance(record['evidence'],list):raise ImageBuildError('invalid license evidence')
    seen=set()
    for item in record['evidence']:
        if not isinstance(item,dict) or set(item)!={'path','sha256','source_sha256'}:raise ImageBuildError('invalid evidence fields')
        safe_path(item['path'])
        key=(item['source_sha256'],item['path'])
        if key in seen:raise ImageBuildError('duplicate license evidence')
        seen.add(key)
        for field in ('sha256','source_sha256'):
            if not isinstance(item[field],str) or not re.fullmatch('[0-9a-f]{64}',item[field]):raise ImageBuildError('invalid evidence digest')
    supplementary_hashes={item['source']['sha256'] for item in notices}
    if supplementary_hashes & {item['source_sha256'] for item in record['evidence']}:
        raise ImageBuildError('supplementary notice cannot also be ordinary evidence')
    if record['source']['sha256'] in supplementary_hashes:
        raise ImageBuildError('primary source cannot be a supplementary notice')
    for field in ('components','patches'):
        if not isinstance(record[field],list):raise ImageBuildError('invalid component or patch records')
        for item in record[field]:
            if not isinstance(item,dict) or set(item)!={'scope','expression','status','notes'} or not isinstance(item['scope'],str) or not isinstance(item['notes'],str):raise ImageBuildError('invalid scoped license record')
            expression(item['expression'])
            if item['status'] not in ('declared','reviewed','unresolved'):raise ImageBuildError('invalid component review status')
            if item['status']=='reviewed' and item['expression'] is None:raise ImageBuildError('reviewed component lacks license expression')
    if record['status']=='reviewed' and (not record['evidence'] or not source['sha256'] or record['expression'] is None):
        raise ImageBuildError('reviewed license lacks source or evidence')
    return record


def load(path, package_sources=None):return validate(literal(path),package_sources)


def prepare_readability(package, source):
    """Make declared notices readable across build/orchestrator UID handoff.

    Called only on a new, privately staged source tree before registration.
    Preserve all existing mode bits and contents; add read bits solely to
    hash-verified license evidence. Never repair a running or recovered tree.
    """
    import stat
    if package.licensing is None:
        return []
    validate(package.licensing,package.sources)
    root = Path(source)
    sources = {item['sha256']: item for item in package.sources}
    changes = []
    for evidence in package.licensing['evidence']:
        spec = sources.get(evidence['source_sha256'])
        if spec is None:
            raise ImageBuildError('license evidence has an undeclared source')
        path = root / spec['destination']
        if spec['archive']:
            path = path / safe_path(evidence['path'])
        elif evidence['path'] != path.name:
            raise ImageBuildError('raw license evidence must name the source file')
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise ImageBuildError('license evidence traverses a symlink')
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as error:
            raise ImageBuildError('cannot prepare license readability: '+evidence['path']) from error
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ImageBuildError('license readability requires an unshared regular file')
            import hashlib
            with os.fdopen(os.dup(descriptor), 'rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != evidence['sha256']:
                raise ImageBuildError('license source text changed before preparation')
            mode = stat.S_IMODE(before.st_mode)
            readable = mode | 0o444
            if readable != mode:
                os.fchmod(descriptor, readable)
                os.fsync(descriptor)
                changes.append(dict(path=path.relative_to(root).as_posix(),
                                    sha256=actual, before_mode=mode, after_mode=readable))
        finally:
            os.close(descriptor)
    return changes


def prepare_finalization(package, output, checkpoint, inputs):
    """Freeze installed outputs before releasing their controller registration."""
    current = inventory(output)
    checkpoint = Path(checkpoint)
    if not checkpoint.exists():
        write_json(checkpoint, {'inputs': inputs, 'outputs': current})
        return
    saved = json.loads(checkpoint.read_text())
    if saved['inputs'] != inputs:
        raise ImageBuildError('package finalization inputs changed')
    actual = {r['path']: r for r in current}
    original = {r['path']: r for r in saved['outputs']}
    if any(actual.get(name) != record for name, record in original.items()):
        raise ImageBuildError('installed outputs changed during finalization')
    prefix = 'sysroot/' if all(p.startswith('sysroot/') for p in package.outputs) else ('tools/' if all(p.startswith('tools/') for p in package.outputs) else '')
    base = prefix + 'usr/share/licenses/zog-packages/' + package.name
    files = {base + '/record.json'} | {base + '/texts/' + e['source_sha256'] + '/' + safe_path(e['path']) for e in package.licensing['evidence']}
    files |= {_supplementary_installed_path(base,item) for item in supplementary_notices(package.licensing,package.sources)}
    directories = {str(parent) for name in files for parent in Path(name).parents}
    for name in set(actual) - set(original):
        if not ((name in files and actual[name]['kind'] == 'file') or
                (name in directories and actual[name]['kind'] == 'directory')):
            raise ImageBuildError('unexpected output during license finalization')


def patch_declarations(package, state):
    """Validate reviewed patch identity, order, scope, source bytes and file claims."""
    patches = package.integration.get('patches', [])
    if not isinstance(patches, list):
        raise ImageBuildError('invalid patch declarations')
    previous_order = 0
    seen = set()
    for patch in patches:
        if not isinstance(patch, dict):
            raise ImageBuildError('invalid patch declaration')
        order = patch.get('order')
        patch_id = patch.get('id')
        if (type(order) is not int or order <= previous_order or
                not isinstance(patch_id, str) or not patch_id or patch_id in seen):
            raise ImageBuildError('invalid patch identity or order')
        previous_order = order
        seen.add(patch_id)
        if not package.licensing:
            raise ImageBuildError('patch declarations require version-bound licensing metadata')
        if patch.get('applies_to') != {'version': package.licensing['version'],
                                      'stage': package.integration.get('stage_id')}:
            raise ImageBuildError('patch scope differs from package stage')
        spec = patch.get('source')
        if not isinstance(spec, dict) or spec not in package.sources or spec.get('archive') is not False:
            raise ImageBuildError('patch must reference a declared file source')
        cached = Path(state)/'image-build/sources'/spec['sha256']
        if cached.is_symlink() or not cached.is_file() or digest(cached) != spec['sha256']:
            raise ImageBuildError('patch source missing or changed')
        files = patch.get('files')
        if not isinstance(files, list) or not files:
            raise ImageBuildError('patch lacks affected files')
        paths = set()
        for file in files:
            if not isinstance(file, dict) or set(file) != {'path','before_sha256','after_sha256'}:
                raise ImageBuildError('invalid patch file declaration')
            path = safe_path(file['path'])
            if path in paths:
                raise ImageBuildError('duplicate patch file')
            paths.add(path)
            for field in ('before_sha256','after_sha256'):
                if not isinstance(file[field], str) or not re.fullmatch('[0-9a-f]{64}', file[field]):
                    raise ImageBuildError('invalid patched-file digest')
    return patches


def patched_evidence(package, item, state):
    """Check the declared license-file hash chain against the original evidence."""
    expected = item['sha256']
    applied = []
    for patch in patch_declarations(package, state):
        patch_id, spec = patch['id'], patch['source']
        for file in patch['files']:
            path = file['path']
            evidence_path = item['path']
            matches = evidence_path == path or evidence_path.partition('/')[2] == path
            if not matches:
                continue
            if item['source_sha256'] != package.licensing['source']['sha256']:
                raise ImageBuildError('patch evidence must belong to the primary source')
            if file['before_sha256'] != expected:
                raise ImageBuildError('patch evidence hash chain differs')
            expected = file['after_sha256']
            applied.append({'id':patch_id, 'source_sha256':spec['sha256'],
                            'before_sha256':file['before_sha256'],
                            'after_sha256':expected})
    return expected, applied


def _supplementary_source_roles(package, state, record, notices):
    """Validate disjoint roles without forbidding archive evidence/proof coexistence."""
    supplementary_hashes={item['source']['sha256'] for item in notices}
    supplementary_sources=[item['source'] for item in notices]
    nested_sources=[_canonical_web_archive_source(item,record,package.sources)
                    for item in notices
                    if 'canonical_web' in item and 'source' in item['canonical_web']['incorporated_by']]
    evidence_hashes={item['source_sha256'] for item in record['evidence']}
    for item in notices:
        spec=item['source']
        if spec not in package.sources:
            raise ImageBuildError('supplementary notice must be a declared recipe source')
        if spec['sha256'] in evidence_hashes:
            raise ImageBuildError('supplementary notice overlaps ordinary evidence')
    for spec in nested_sources:
        if spec['sha256'] in supplementary_hashes:
            raise ImageBuildError('canonical web nested source cannot reuse a supplementary raw source')
    patch_sources=[patch['source'] for patch in patch_declarations(package,state)]
    patch_hashes={source['sha256'] for source in patch_sources}
    if any(source in patch_sources for source in supplementary_sources):
        raise ImageBuildError('supplementary notice cannot also be a patch input')
    if any(source in patch_sources or source['sha256'] in patch_hashes for source in nested_sources):
        raise ImageBuildError('canonical web nested source overlaps a patch input')
    return supplementary_sources,nested_sources


def preserve(package, source, output, state):
    """Verify exact original source-cache evidence, then retain it before cleanup.

    Build scripts can patch their extracted files; license notices are checked
    against fresh archive members, not trusted from a possibly modified tree.
    """
    import tarfile
    record=package.licensing
    if record is None:return None
    validate(record,package.sources)
    sources={s['sha256']:s for s in package.sources}
    if record['source']['sha256'] not in sources:raise ImageBuildError('license record does not match a recipe source')
    prefix='sysroot/' if all(p.startswith('sysroot/') for p in package.outputs) else ('tools/' if all(p.startswith('tools/') for p in package.outputs) else '')
    name=prefix+'usr/share/licenses/zog-packages/'+package.name
    target=Path(output)/name
    for parent in [target,*target.parents]:
        if parent==Path(output).parent:break
        if parent.is_symlink():raise ImageBuildError('license output parent is a symlink')
    notices=supplementary_notices(record,package.sources)
    generated={name+'/record.json'} | {name+'/texts/'+e['source_sha256']+'/'+safe_path(e['path']) for e in record['evidence']}
    generated |= {_supplementary_installed_path(name,item) for item in notices}
    supplementary_sources,nested_sources=_supplementary_source_roles(
        package,state,record,notices)
    existing=inventory(output)
    if any(r['kind']!='directory' and r['path'].startswith(name+'/') and r['path'] not in generated for r in existing):
        raise ImageBuildError('unexpected file in reserved license output')
    owned_outputs=[r for r in existing if r['kind']!='directory' and r['path'] not in generated]
    evidence=[]
    for item in record['evidence']:
        if item['source_sha256'] not in sources:raise ImageBuildError('license evidence has an undeclared source')
        cache=Path(state)/'image-build/sources'/item['source_sha256']
        if not cache.is_file() or digest(cache)!=item['source_sha256']:raise ImageBuildError('license source archive missing or changed')
        source_spec=sources[item['source_sha256']]
        if source_spec['archive']:
            extracted=Path(source)/source_spec['destination']/safe_path(item['path'])
        else:
            if item['path'] != Path(source_spec['destination']).name:
                raise ImageBuildError('raw license evidence must name the source file')
            extracted=Path(source)/source_spec['destination']
        # Require the path in the extracted tree to be a regular file as well.
        if any(p.is_symlink() for p in [extracted,*extracted.parents] if p!=Path(source).parent):raise ImageBuildError('license evidence traverses a symlink')
        working_hash, transformations = patched_evidence(package, item, state)
        if not extracted.is_file() or digest(extracted)!=working_hash:raise ImageBuildError('required license text missing or changed: '+item['path'])
        if source_spec['archive']:
            with tarfile.open(cache) as archive:
                member=archive.getmember(item['path'])
                if not member.isfile():raise ImageBuildError('license archive evidence is not a regular file')
                data=archive.extractfile(member).read()
        else:
            data=cache.read_bytes()
        import hashlib
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ImageBuildError('license archive text changed')
        dest=target/'texts'/item['source_sha256']/item['path']
        if any(p.is_symlink() for p in [dest,*dest.parents]):raise ImageBuildError('license notice traverses a symlink')
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.is_symlink() or (dest.exists() and dest.read_bytes()!=data):raise ImageBuildError('license notice output conflict')
        dest.write_bytes(data);dest.chmod(0o644)
        evidence_item = dict(item,installed_path=dest.relative_to(output).as_posix(),
                             origin=NOTICE_ORIGIN_ARCHIVE if source_spec['archive'] else NOTICE_ORIGIN_RAW)
        if transformations:
            evidence_item.update(working_sha256=working_hash, transformations=transformations)
        evidence.append(evidence_item)
    supplementary=[]
    for item in notices:
        spec=item['source'];sha=spec['sha256']
        cache=Path(state)/'image-build/sources'/sha
        if cache.is_symlink() or not cache.is_file() or digest(cache)!=sha:
            raise ImageBuildError('supplementary notice input missing or changed')
        _verify_canonical_web_binding(item,record,package.sources,
                                      Path(state)/'image-build/sources')
        data=cache.read_bytes()
        dest=Path(output)/_supplementary_installed_path(name,item)
        if any(p.is_symlink() for p in [dest,*dest.parents]):
            raise ImageBuildError('supplementary notice output traverses a symlink')
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.is_symlink() or (dest.exists() and dest.read_bytes()!=data):
            raise ImageBuildError('supplementary notice output conflict')
        dest.write_bytes(data);dest.chmod(0o644)
        supplementary.append(dict(item,installed_path=dest.relative_to(output).as_posix(),
                                  origin=NOTICE_ORIGIN_SUPPLEMENTARY,
                                  provenance_class=_supplementary_provenance_class(item)))
    # Explicitly retained inputs are separate from the disposable source cache.
    retained=Path(state)/'image-build/release-inputs';retained.mkdir(parents=True,exist_ok=True)
    if any(p.is_symlink() for p in [retained,*retained.parents]):raise ImageBuildError('release input directory traverses a symlink')
    for sha in sources:
        archive=Path(state)/'image-build/sources'/sha;dest=retained/sha
        if not archive.is_file() or digest(archive)!=sha:raise ImageBuildError('corresponding-source input missing or changed')
        if dest.is_symlink():raise ImageBuildError('retained source is a symlink')
        if not dest.exists():
            temporary=retained/(sha+'.pending')
            if temporary.is_symlink():raise ImageBuildError('retained source staging is a symlink')
            with archive.open('rb') as src, temporary.open('wb') as dst:
                shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
            temporary.replace(dest)
        if dest.is_symlink() or digest(dest)!=sha:raise ImageBuildError('retained release input changed')
    fd=os.open(retained,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    from dataclasses import asdict
    receipt={'schema':2 if notices else 1,'record':record,'record_identity':identity(record),'sources':list(package.sources),
             'recipe':{k:v for k,v in asdict(package).items() if k != 'recipe_directory'},'evidence':evidence,
             'supplementary_notices':supplementary,'owned_outputs':owned_outputs,
             'unreviewed_sources': sorted({spec['sha256'] for spec in package.sources
                 if spec['sha256']!=record['source']['sha256'] and spec not in supplementary_sources}),
             'source_retention':'release-inputs; no automatic expiry'}
    receipt=json.loads(json.dumps(receipt))
    receipt_path=target/'record.json';target.mkdir(parents=True,exist_ok=True)
    if receipt_path.is_symlink() or (receipt_path.exists() and json.loads(receipt_path.read_text())!=receipt):raise ImageBuildError('license receipt collision')
    write_json(receipt_path,receipt)
    return {'identity':identity(record),'record':record,'receipt':receipt_path.relative_to(output).as_posix()}


def release_check(directory,state):
    """Audit all shipped regular files and retained notices without network access."""
    from .engine import read_selection
    selection=read_selection(directory);issues=[];packages=[];covered=set()
    actual={r['path']:r for r in inventory(selection.root) if r['kind']!='directory'}
    for receipt in selection.root.rglob('usr/share/licenses/zog-packages/*/record.json'):
        if any(p.is_symlink() for p in [receipt,*receipt.parents]):raise ImageBuildError('release receipt traverses a symlink')
        r=json.loads(receipt.read_text());record=validate(r['record'],r.get('sources'));packages.append(record)
        if identity(record)!=r['record_identity']:raise ImageBuildError('release license identity changed')
        if record['status']!='reviewed' or any(c['status']!='reviewed' for c in record['components']+record['patches']):issues.append(record['package']+': review incomplete')
        if r.get('unreviewed_sources'):issues.append(record['package']+': additional source/patch licensing unresolved')
        source_by_sha={source['sha256']:source for source in r['sources']}
        for e in r['evidence']:
            f=selection.root/safe_path(e['installed_path'])
            if any(p.is_symlink() for p in [f,*f.parents]) or not f.is_file() or digest(f)!=e['sha256']:issues.append(record['package']+': missing/changed retained notice')
            spec=source_by_sha.get(e['source_sha256'])
            expected_origin=(NOTICE_ORIGIN_ARCHIVE if spec and spec.get('archive') else NOTICE_ORIGIN_RAW)
            if e.get('origin',expected_origin)!=expected_origin:issues.append(record['package']+': notice origin changed')
        expected_supplementary=supplementary_notices(record,r.get('sources'))
        delivered=r.get('supplementary_notices',[])
        if expected_supplementary and r.get('schema')!=2:
            issues.append(record['package']+': supplementary notice receipt schema changed')
        if len(delivered)!=len(expected_supplementary):
            issues.append(record['package']+': supplementary notice delivery incomplete')
        else:
            expected_by_id={item['id']:item for item in expected_supplementary}
            for item in delivered:
                declared=expected_by_id.get(item.get('id'))
                if (declared is None or item.get('origin')!=NOTICE_ORIGIN_SUPPLEMENTARY or
                        item.get('provenance_class',_supplementary_provenance_class(declared))!=_supplementary_provenance_class(declared) or
                        {k:item.get(k) for k in declared}!=declared):
                    issues.append(record['package']+': supplementary notice delivery changed')
                    continue
                if declared['source'] not in r['sources']:
                    issues.append(record['package']+': supplementary notice source binding missing')
                    continue
                try:
                    _verify_canonical_web_binding(
                        declared,record,r['sources'],
                        Path(state)/'image-build/release-inputs')
                except ImageBuildError:
                    issues.append(record['package']+': canonical web notice provenance changed')
                    continue
                f=selection.root/safe_path(item['installed_path'])
                if (any(p.is_symlink() for p in [f,*f.parents]) or not f.is_file() or
                        digest(f)!=declared['source']['sha256']):
                    issues.append(record['package']+': missing/changed supplementary notice')
        for source in r['sources']:
            f=Path(state)/'image-build/release-inputs'/source['sha256']
            if not f.is_file() or f.is_symlink() or digest(f)!=source['sha256']:issues.append(record['package']+': missing corresponding source')
        for output in r.get('owned_outputs',[]):
            path=safe_path(output['path'])
            if output['kind']!='directory' and actual.get(path)==output:covered.add(path)
        covered.add(receipt.relative_to(selection.root).as_posix())
        covered.update(safe_path(e['installed_path']) for e in r['evidence'])
        covered.update(safe_path(e['installed_path']) for e in r.get('supplementary_notices',[]))
    unknown=sorted(set(actual)-covered)
    if unknown:issues.append('Inherited/seed or other files lack verified package ownership and license coverage')
    if not packages:issues.append('No package license receipts; historical generation is unreviewed')
    return {'generation':selection.generation,'eligible':not issues,'packages':packages,
            'unresolved_files':unknown,'issues':issues}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('generation');parser.add_argument('--state',required=True)
    args=parser.parse_args();result=release_check(args.generation,args.state);print(json.dumps(result,indent=2));raise SystemExit(0 if result['eligible'] else 1)


if __name__=='__main__':main()

import copy
import io
import json
import shutil
import tarfile
from dataclasses import asdict, replace
from pathlib import Path
import pytest
from zog.image_build.engine import ImageBuild
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import digest, inventory
from zog.image_build.licensing import expression, load, preserve, release_check, validate
from zog.image_build.metadata import Package, identity, literal, load_package


@pytest.fixture
def fixture(tmp_path):
    state=tmp_path/'license-state'; cache=state/'image-build/sources';cache.mkdir(parents=True)
    archive=tmp_path/'source.tar'; text=b'Copyright Example. Permission to use, copy and distribute.\n'
    with tarfile.open(archive,'w') as t:
        member=tarfile.TarInfo('demo/LICENSE');member.size=len(text);t.addfile(member,io.BytesIO(text))
    sha=digest(archive);shutil.copyfile(archive,cache/sha)
    source=tmp_path/'source';(source/'src/demo').mkdir(parents=True);(source/'src/demo/LICENSE').write_bytes(text)
    output=tmp_path/'output';(output/'usr/bin').mkdir(parents=True);(output/'usr/bin/demo').write_text('program')
    record=dict(schema=1,package='demo',version='1',source=dict(url=archive.as_uri(),sha256=sha),status='reviewed',expression='MIT',scope='All files',evidence=[dict(path='demo/LICENSE',sha256=digest(source/'src/demo/LICENSE'),source_sha256=sha)],components=[],patches=[],notes=[])
    package=Package('demo', (dict(url=archive.as_uri(),sha256=sha,destination='src',archive=True),),(),(),{}, {},('usr/bin/demo',),{},licensing=record)
    return package,source,output,state


def publish(output,state):
    builder=ImageBuild(package_dir=state/'recipes',state_dir=state)
    return builder._publish(output,{'schema':2,'kind':'image','outputs':inventory(output)},'image',{})


def test_evidence_survives_cleanup_and_offline_gate(fixture):
    p,source,output,state=fixture
    receipt=preserve(p,source,output,state)
    before=inventory(output)
    assert preserve(p,source,output,state)==receipt
    assert inventory(output)==before
    shutil.rmtree(source);shutil.rmtree(state/'image-build/sources')
    selection=publish(output,state)
    result=release_check(selection.root.parent,state)
    assert result['eligible'] and not result['unresolved_files']
    (state/'image-build/release-inputs'/p.sources[0]['sha256']).unlink()
    assert not release_check(selection.root.parent,state)['eligible']


@pytest.mark.parametrize('change',['missing','changed','symlink','output-symlink','unexpected-output'])
def test_evidence_failures(fixture,tmp_path,change):
    p,source,output,state=fixture;notice=source/'src/demo/LICENSE'
    if change=='missing':notice.unlink()
    if change=='changed':notice.write_text('changed')
    if change=='symlink':notice.unlink();notice.symlink_to(tmp_path/'external')
    target=output/'usr/share/licenses/zog-packages/demo'
    if change=='output-symlink':
        target.mkdir(parents=True);(target/'texts').symlink_to(tmp_path)
    if change=='unexpected-output':
        target.mkdir(parents=True);(target/'unclaimed').write_text('unclaimed')
    with pytest.raises(ImageBuildError):preserve(p,source,output,state)


def test_inherited_files_and_incomplete_reviews_block_release(fixture):
    p,source,output,state=fixture
    p.licensing['components']=[dict(scope='runtime',expression='GPL-3.0-or-later WITH GCC-exception-3.1',status='declared',notes='Requires review')]
    preserve(p,source,output,state)
    (output/'seed-library').write_text('inherited')
    selection=publish(output,state);result=release_check(selection.root.parent,state)
    assert not result['eligible'] and result['unresolved_files']==['seed-library']
    assert any('review incomplete' in issue for issue in result['issues'])


def test_historical_generation_readable_but_unreviewed(fixture):
    _,_,output,state=fixture
    selection=publish(output,state)
    assert not release_check(selection.root.parent,state)['eligible']


@pytest.mark.parametrize('value',['MIT AND','MIT OR (GPL-3.0-only','Made-Up','MIT; x','MIT WITH Unknown','MIT OR OR ISC'])
def test_invalid_expressions(value):
    with pytest.raises(ImageBuildError):expression(value)


def test_inert_data_paths_and_fingerprints(fixture,tmp_path):
    p,*_=fixture
    path=tmp_path/'license.py';path.write_text("__import__('os').system('false')")
    with pytest.raises(ImageBuildError):load(path)
    for unsafe in ('../LICENSE','/LICENSE','a/../b','a//b'):
        r=copy.deepcopy(p.licensing);r['evidence'][0]['path']=unsafe
        with pytest.raises(ImageBuildError):validate(r)
    updated=copy.deepcopy(p.licensing);updated['notes'].append('Reviewed scope change')
    assert replace(p,licensing=updated).fingerprint!=p.fingerprint
    old=replace(p,licensing=None);data=asdict(old);data.pop('licensing');data.pop('test_dependencies'); data.pop('recipe_directory'); data.pop('source_provenance')
    assert old.fingerprint==identity(data)


def test_catalogue_and_every_stage_have_bound_records():
    root=Path(__file__).parents[1]/'project/package'
    projects=[p for p in root.iterdir() if p.is_dir() and not p.name.startswith('.')]
    assert {'openssl', 'sqlite', 'readline'} <= {p.name for p in projects}
    for directory in projects:
        stages=list(directory.glob('stages/*'))
        if not stages:
            catalogue_path=directory/'package.py'
            catalogue=literal(catalogue_path) if catalogue_path.exists() else {}
            if catalogue.get('recipe_status') in {
                'source-pinned-application-plan',
                'source-pinned-follow-on-plan',
                'cargo-source-closure-frozen',
            }:
                assert catalogue.get('status') == 'catalogue-only'
                assert catalogue.get('artifact_contract') == 'applications-v1'
                assert isinstance(catalogue.get('license_scope'), str)
                assert catalogue['license_scope']
                assert (directory/'sources.py').exists()
                assert not (directory/'license.py').exists()
                continue
            sources_path=directory/'sources.py'
            record=(load(directory/'license.py',literal(sources_path))
                    if sources_path.exists() else load(directory/'license.py'))
            assert record['package']==directory.name and record['evidence']
            continue
        for stage in stages:
            package=load_package(stage)
            record=load(directory/'license.py',package.sources)
            expected=(load(stage/'license.py',package.sources)
                      if (stage/'license.py').exists() else record)
            assert package.licensing==expected
            assert record['package']==directory.name and record['evidence']
            assert expected['package']==record['package']
            if expected['version'] == record['version']:
                assert expected['source'] == record['source']
                assert all(item in expected['evidence'] for item in record['evidence'])
            else:
                # Explicit version overrides bind the actual stage archive.
                assert (stage/'license.py').exists()
                assert any(source['url'] == expected['source']['url'] and
                           source['sha256'] == expected['source']['sha256']
                           for source in package.sources)
                assert expected['evidence']
                assert all(item['source_sha256'] == expected['source']['sha256']
                           for item in expected['evidence'])


from test_source_build import prepared
from zog.image_build.artifacts import import_completed


def test_engine_composition_and_cache_bind_license_identity(prepared,fixture):
    builder,runner,_,toolchain=prepared
    package,source,output,state=fixture
    directory=builder.package_dir/'library'
    (directory/'sources.py').write_text(repr(list(package.sources)))
    from zog.image_build.metadata import literal
    pins=literal(builder.package_dir/'commit-pin.py')
    pins['packages']['library']['sources']=list(package.sources)
    (builder.package_dir/'commit-pin.py').write_text(repr(pins))
    record=copy.deepcopy(package.licensing);record['package']='library'
    (directory/'license.py').write_text(repr(record))
    first=builder.ensure(['library'],toolchain=toolchain)
    assert release_check(first.root.parent,builder.state)['eligible']
    pipeline=next(p for p in (builder.state/'image-build/pipelines').glob('*/pipeline.json') if json.loads(p.read_text())['operation']=='image')
    builder.release_pipeline(pipeline.parent.name);import_completed(builder,pipeline.parent.name)
    count=len(runner.calls)
    record['notes'].append('Updated licensing review')
    (directory/'license.py').write_text(repr(record))
    second=builder.ensure(['library'],toolchain=toolchain)
    assert len(runner.calls)==count+3
    assert first.generation!=second.generation
    receipt=json.loads((second.root/'usr/share/licenses/zog-packages/library/record.json').read_text())
    assert receipt['record_identity']==identity(record)


def test_finalization_releases_before_notices_and_resumes_without_recompile(prepared,fixture,monkeypatch):
    import zog.image_build.licensing as licensing
    from zog.image_build.runner import BoxControlRunner, BuildExecutionResult
    builder,_,_,toolchain=prepared
    package,*_=fixture
    directory=builder.package_dir/'library'
    (directory/'sources.py').write_text(repr(list(package.sources)))
    from zog.image_build.metadata import literal
    pins=literal(builder.package_dir/'commit-pin.py')
    pins['packages']['library']['sources']=list(package.sources)
    (builder.package_dir/'commit-pin.py').write_text(repr(pins))
    record=copy.deepcopy(package.licensing);record['package']='library'
    (directory/'license.py').write_text(repr(record))
    calls=[];released=[];attempts=[]
    def execute(request):
        calls.append(request.command)
        if request.command[0]=='install':
            path=request.output/'usr/share/library';path.parent.mkdir(parents=True);path.write_text('library')
        return BuildExecutionResult('runtime','invocation',0,True,'journal')
    builder.runner=BoxControlRunner(execute)
    monkeypatch.setattr(builder,'_release_resources',lambda p:released.append(Path(p)))
    original=licensing.preserve
    def interrupted(p,source,output,state):
        assert output.parent in released
        assert calls[-1][0]=='install'
        attempts.append(output)
        if len(attempts)==1:raise OSError('interrupted notice preservation')
        return original(p,source,output,state)
    monkeypatch.setattr(licensing,'preserve',interrupted)
    with pytest.raises(OSError,match='interrupted notice'):
        builder.ensure(['library'],toolchain=toolchain)
    assert len(calls)==3
    pipeline=next(p for p in (builder.state/'image-build/pipelines').glob('*/pipeline.json') if json.loads(p.read_text())['status']=='pending')
    result=builder.resume(pipeline.parent.name)
    assert len(calls)==3  # Saved controller completions, no repeated compilation.
    assert release_check(result.root.parent,builder.state)['eligible']


def test_unreleased_workspace_cannot_enter_notice_preservation(prepared,fixture,monkeypatch):
    import zog.image_build.licensing as licensing
    builder,_,_,toolchain=prepared
    package,*_=fixture
    directory=builder.package_dir/'library'
    (directory/'sources.py').write_text(repr(list(package.sources)))
    from zog.image_build.metadata import literal
    pins=literal(builder.package_dir/'commit-pin.py')
    pins['packages']['library']['sources']=list(package.sources)
    (builder.package_dir/'commit-pin.py').write_text(repr(pins))
    record=copy.deepcopy(package.licensing);record['package']='library'
    (directory/'license.py').write_text(repr(record))
    def blocked(_):raise ImageBuildError('process cleanup incomplete')
    monkeypatch.setattr(builder,'_release_resources',blocked)
    monkeypatch.setattr(licensing,'preserve',lambda *args:pytest.fail('unreleased workspace was modified'))
    with pytest.raises(ImageBuildError,match='cleanup incomplete'):
        builder.ensure(['library'],toolchain=toolchain)
    assert not list((builder.state/'image-build/attempts').glob('*/packages/library/result.json'))


def test_finalization_rejects_changed_installed_output(fixture):
    from zog.image_build.licensing import prepare_finalization
    package,source,output,state=fixture
    checkpoint=state/'finalization.json'
    prepare_finalization(package,output,checkpoint,{'recipe':package.fingerprint})
    preserve(package,source,output,state)
    prepare_finalization(package,output,checkpoint,{'recipe':package.fingerprint})
    (output/'usr/bin/demo').write_text('changed')
    with pytest.raises(ImageBuildError,match='outputs changed'):
        prepare_finalization(package,output,checkpoint,{'recipe':package.fingerprint})


def patched_fixture(fixture):
    p,source,output,state=fixture
    original=(source/'src/demo/LICENSE').read_bytes()
    patch=state/'image-build/sources/patch';patch.write_bytes(b'reviewed patch input')
    sha=digest(patch);patch.rename(patch.with_name(sha))
    spec=dict(url='https://example.test/fix.patch',sha256=sha,destination='patches/fix.patch',archive=False)
    (source/'src/demo/LICENSE').write_bytes(original+b'Updated source code\n')
    declaration=dict(id='fix',order=1,applies_to=dict(version='1',stage='final'),source=spec,
                     files=[dict(path='LICENSE',before_sha256=p.licensing['evidence'][0]['sha256'],after_sha256=digest(source/'src/demo/LICENSE'))])
    p=replace(p,sources=p.sources+(spec,),integration=dict(stage_id='final',patches=[declaration]))
    return p,source,output,state,original


def test_patched_evidence_preserves_original_and_records_transformation(fixture):
    p,source,output,state,original=patched_fixture(fixture)
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    evidence=receipt['evidence'][0]
    assert (output/evidence['installed_path']).read_bytes()==original
    assert evidence['working_sha256']==digest(source/'src/demo/LICENSE')
    assert evidence['transformations'][0]['before_sha256']==evidence['sha256']
    assert preserve(p,source,output,state)==result
    assert receipt['unreviewed_sources']==[p.sources[1]['sha256']]


@pytest.mark.parametrize('fault',['working','before','patch','undeclared','scope','order','archive','path','duplicate'])
def test_patched_evidence_rejects_unbound_changes(fixture,fault):
    p,source,output,state,_=patched_fixture(fixture)
    patch=p.integration['patches'][0]
    if fault=='working':(source/'src/demo/LICENSE').write_text('unexplained modification')
    if fault=='before':patch['files'][0]['before_sha256']='0'*64
    if fault=='patch':(state/'image-build/sources'/p.sources[1]['sha256']).write_text('changed patch')
    if fault=='undeclared':p=replace(p,sources=p.sources[:1])
    if fault=='scope':patch['applies_to']['stage']='other'
    if fault=='order':patch['order']=0
    if fault=='archive':patch['source']=dict(p.sources[0])
    if fault=='path':patch['files'][0]['path']='../LICENSE'
    if fault=='duplicate':patch['files'].append(copy.deepcopy(patch['files'][0]))
    with pytest.raises(ImageBuildError):preserve(p,source,output,state)


def test_patched_evidence_requires_contiguous_ordered_chain(fixture):
    p,source,output,state,_=patched_fixture(fixture)
    first=p.integration['patches'][0]
    second=copy.deepcopy(first);second.update(id='second',order=2)
    second['files'][0]['before_sha256']=first['files'][0]['after_sha256']
    (source/'src/demo/LICENSE').write_text('second declared result')
    second['files'][0]['after_sha256']=digest(source/'src/demo/LICENSE')
    p.integration['patches'].append(second)
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    assert len(receipt['evidence'][0]['transformations'])==2


def test_raw_notice_preserved_and_tampering_rejected(fixture):
    p,source,output,state=fixture
    notice=source/'NOTICE';notice.write_text('Raw upstream license notice')
    sha=digest(notice);shutil.copyfile(notice,state/'image-build/sources'/sha)
    spec=dict(url='https://example.invalid/NOTICE',sha256=sha,destination='NOTICE',archive=False)
    p=replace(p,sources=(*p.sources,spec),licensing=copy.deepcopy(p.licensing))
    p.licensing['evidence'].append(dict(path='NOTICE',sha256=sha,source_sha256=sha))
    receipt=preserve(p,source,output,state)
    assert (output/'usr/share/licenses/zog-packages/demo/texts'/sha/'NOTICE').read_text()==notice.read_text()
    notice.write_text('changed')
    with pytest.raises(ImageBuildError):preserve(p,source,output,state)


def test_raw_notice_cannot_name_another_path(fixture):
    p,source,output,state=fixture
    notice=source/'NOTICE';notice.write_text('Raw notice');sha=digest(notice)
    shutil.copyfile(notice,state/'image-build/sources'/sha)
    p=replace(p,sources=(*p.sources,dict(url='https://example.invalid/NOTICE',sha256=sha,destination='NOTICE',archive=False)),licensing=copy.deepcopy(p.licensing))
    p.licensing['evidence'].append(dict(path='elsewhere',sha256=sha,source_sha256=sha))
    with pytest.raises(ImageBuildError,match='must name the source file'):preserve(p,source,output,state)


def test_notice_readability_is_scoped_and_content_preserving(fixture):
    from zog.image_build.licensing import prepare_readability
    p, source, output, state = fixture
    notice = source/'src/demo/LICENSE'
    notice.chmod(0o640)
    unrelated = source/'src/demo/private-fixture'
    unrelated.write_text('unchanged fixture permissions')
    unrelated.chmod(0o600)
    before = notice.read_bytes()
    changes = prepare_readability(p, source)
    assert changes == [dict(path='src/demo/LICENSE', sha256=digest(notice),
                            before_mode=0o640, after_mode=0o644)]
    assert notice.read_bytes() == before
    assert unrelated.stat().st_mode & 0o777 == 0o600
    assert prepare_readability(p, source) == []
    assert preserve(p, source, output, state)


@pytest.mark.parametrize('change', ['changed', 'symlink', 'hardlink'])
def test_notice_readability_rejects_unsafe_evidence(fixture, change):
    from zog.image_build.licensing import prepare_readability
    import os
    p, source, _, _ = fixture
    notice = source/'src/demo/LICENSE'
    other = source/'src/demo/other'
    if change == 'changed':
        notice.write_text('altered')
    elif change == 'symlink':
        notice.rename(other)
        notice.symlink_to(other.name)
    else:
        os.link(notice, other)
    with pytest.raises(ImageBuildError):
        prepare_readability(p, source)


def test_notice_readable_after_distinct_build_uid_handoff(fixture):
    import os
    import subprocess
    import tempfile
    from zog.image_build.licensing import prepare_readability
    if os.geteuid() != 0:
        pytest.skip('real cross-UID access check requires root')
    p, original, _, _ = fixture
    with tempfile.TemporaryDirectory(prefix='zog-notice-access-') as name:
        root = Path(name)
        root.chmod(0o755)
        directory = root/'src/demo'
        directory.mkdir(parents=True)
        notice = directory/'LICENSE'
        notice.write_bytes((original/'src/demo/LICENSE').read_bytes())
        notice.chmod(0o640)
        other = directory/'private-fixture'
        other.write_text('private'); other.chmod(0o640)
        prepare_readability(p, root)
        # Model controller import followed by directory-only ownership return.
        try:
            os.chown(notice, 21001, 21001)
            os.chown(other, 21001, 21001)
        except OSError as error:
            import errno
            if error.errno in (errno.EINVAL, errno.EPERM):
                pytest.skip('execution environment cannot map distinct build UID')
            raise
        def reader():
            os.setgroups([]); os.setgid(65534); os.setuid(65534)
        result = subprocess.run(['python3', '-c',
            'from pathlib import Path; import sys; '
            'Path(sys.argv[1]).read_bytes()', str(notice)],
            preexec_fn=reader, capture_output=True)
        assert result.returncode == 0, result.stderr
        denied = subprocess.run(['python3', '-c',
            'from pathlib import Path; import sys; '
            'Path(sys.argv[1]).read_bytes()', str(other)],
            preexec_fn=reader, capture_output=True)
        assert denied.returncode != 0 and b'PermissionError' in denied.stderr

@pytest.mark.parametrize('value', [
    'MIT-open-group',
    'X11',
    'X11-distribute-modifications-variant',
    'HPND-sell-variant',
    'SMLNJ',
    'MIT AND MIT-open-group',
    'MIT AND HPND-sell-variant AND SMLNJ AND MIT-open-group AND X11',
])
def test_reviewed_xorg_license_identifiers(value):
    expression(value)

@pytest.mark.parametrize('value', [
    'Unicode-3.0',
    'CDLA-Permissive-2.0',
    'Apache-2.0 WITH LLVM-exception',
    '(MIT OR Apache-2.0) AND Unicode-3.0',
    'Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT',
    'MPL-1.1',
    'BSD-4-Clause-UC',
    'MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later',
])
def test_semantic_review_canonical_license_expressions(value):
    expression(value)


@pytest.mark.parametrize('value', [
    'Unicode-3.0-extra',
    'CDLA-Permissive-2.0-extra',
    'Apache-2.0 WITH LLVM-exception-extra',
    'MPL-1.1-extra',
    'BSD-4-Clause-UC-extra',
])
def test_semantic_review_license_allowlist_remains_exact(value):
    with pytest.raises(ImageBuildError):
        expression(value)

def supplementary_fixture(fixture):
    p,source,output,state=fixture
    text=b'Independent upstream notice text\n'
    sha=__import__('hashlib').sha256(text).hexdigest()
    spec=dict(url='https://upstream.example.invalid/demo/LICENSE',
              sha256=sha,destination='supplementary/demo/LICENSE',archive=False)
    cache=state/'image-build/sources'/sha;cache.write_bytes(text)
    p=replace(p,sources=(*p.sources,spec),licensing=copy.deepcopy(p.licensing))
    p.licensing['supplementary_notices']=[dict(
        contract='image-build-supplementary-notice-v1',
        id='upstream-license',
        source=spec,
        upstream=dict(repository='https://github.com/upstream/demo',
                      revision='1'*40,path='LICENSE'),
        path='LICENSE',
        scope='Supplementary upstream grant for reviewed package scope',
        notes='Retrieved independently from the exact upstream notice URL.',
    )]
    return p,source,output,state,text,spec


def test_supplementary_notice_is_hash_bound_and_delivered_separately(fixture):
    from zog.image_build.licensing import prepare_finalization
    p,source,output,state,text,spec=supplementary_fixture(fixture)
    checkpoint=state/'supplementary-finalization.json'
    prepare_finalization(p,output,checkpoint,{'recipe':p.fingerprint})
    result=preserve(p,source,output,state)
    prepare_finalization(p,output,checkpoint,{'recipe':p.fingerprint})
    receipt=json.loads((output/result['receipt']).read_text())
    assert receipt['schema']==2
    assert receipt['evidence'][0]['origin']=='original-source-archive'
    assert receipt['unreviewed_sources']==[]
    item=receipt['supplementary_notices'][0]
    assert item['origin']=='independently-retrieved-upstream-notice'
    assert item['source']==spec
    path=output/item['installed_path']
    assert '/supplementary/upstream-license/' in '/'+item['installed_path']
    assert path.read_bytes()==text
    selection=publish(output,state)
    assert release_check(selection.root.parent,state)['eligible']


def test_supplementary_notice_source_binding_is_release_checked(fixture):
    p,source,output,state,_,_=supplementary_fixture(fixture)
    result=preserve(p,source,output,state)
    receipt_path=output/result['receipt']
    receipt=json.loads(receipt_path.read_text())
    receipt['sources']=[source for source in receipt['sources']
                        if source!=receipt['supplementary_notices'][0]['source']]
    receipt_path.write_text(json.dumps(receipt))
    selection=publish(output,state)
    assert any('source binding missing' in issue
               for issue in release_check(selection.root.parent,state)['issues'])


def test_supplementary_notice_tampering_blocks_preservation_and_release(fixture):
    p,source,output,state,_,spec=supplementary_fixture(fixture)
    cache=state/'image-build/sources'/spec['sha256']
    cache.write_text('changed')
    with pytest.raises(ImageBuildError,match='supplementary notice input missing or changed'):
        preserve(p,source,output,state)
    cache.write_bytes(b'Independent upstream notice text\n')
    result=preserve(p,source,output,state)
    selection=publish(output,state)
    installed=selection.root/json.loads((output/result['receipt']).read_text())['supplementary_notices'][0]['installed_path']
    installed.write_text('changed')
    with pytest.raises(ImageBuildError,match='generation outputs changed'):
        release_check(selection.root.parent,state)


def test_supplementary_notice_detailed_audit_on_consistent_malformed_generation(fixture):
    p,source,output,state,_,_=supplementary_fixture(fixture)
    result=preserve(p,source,output,state)
    installed=output/json.loads((output/result['receipt']).read_text())['supplementary_notices'][0]['installed_path']
    installed.write_text('changed after receipt but before generation inventory')
    selection=publish(output,state)
    assert any('supplementary notice' in issue
               for issue in release_check(selection.root.parent,state)['issues'])


@pytest.mark.parametrize('fault',['archive','file-url','path','revision','upstream-path','duplicate','primary','ordinary-evidence'])
def test_supplementary_notice_validation_is_fail_closed(fixture,fault):
    p,source,output,state,_,spec=supplementary_fixture(fixture)
    notices=p.licensing['supplementary_notices']
    if fault=='archive':notices[0]['source']['archive']=True
    elif fault=='file-url':notices[0]['source']['url']='file:///tmp/LICENSE'
    elif fault=='path':notices[0]['path']='OTHER'
    elif fault=='revision':notices[0]['upstream']['revision']='main'
    elif fault=='upstream-path':notices[0]['upstream']['path']='COPYING'
    elif fault=='duplicate':notices.append(copy.deepcopy(notices[0]))
    elif fault=='primary':
        notices[0]['source']=dict(url='https://upstream.example.invalid/primary',
                                  sha256=p.licensing['source']['sha256'],
                                  destination='LICENSE',archive=False)
    else:
        p.licensing['evidence'].append(dict(path='LICENSE',
            sha256=spec['sha256'],source_sha256=spec['sha256']))
    with pytest.raises(ImageBuildError):
        validate(p.licensing)


def test_supplementary_notice_must_be_declared_raw_source_and_not_patch(fixture):
    p,source,output,state,_,spec=supplementary_fixture(fixture)
    p=replace(p,sources=p.sources[:-1])
    with pytest.raises(ImageBuildError,match='declared recipe source'):
        preserve(p,source,output,state)

    p,source,output,state,_,spec=supplementary_fixture(fixture)
    p.integration['stage_id']='final'
    p.integration['patches']=[dict(
        id='misclassified-notice',order=1,
        applies_to=dict(version='1',stage='final'),
        source=spec,
        files=[dict(path='LICENSE',before_sha256='0'*64,after_sha256='1'*64)],
    )]
    with pytest.raises(ImageBuildError,match='supplementary notice cannot also be a patch input'):
        preserve(p,source,output,state)


def test_unrelated_extra_source_remains_unreviewed_with_supplementary_notice(fixture):
    p,source,output,state,_,_=supplementary_fixture(fixture)
    extra=b'unreviewed source input'
    sha=__import__('hashlib').sha256(extra).hexdigest()
    spec=dict(url='https://upstream.example.invalid/demo/extra.patch',
              sha256=sha,destination='extra.patch',archive=False)
    (state/'image-build/sources'/sha).write_bytes(extra)
    p=replace(p,sources=(*p.sources,spec))
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    assert receipt['unreviewed_sources']==[sha]
    selection=publish(output,state)
    assert not release_check(selection.root.parent,state)['eligible']


def test_declared_raw_evidence_is_distinct_from_supplementary_notice(fixture):
    p,source,output,state=fixture
    notice=source/'NOTICE';notice.write_text('Raw upstream license notice')
    sha=digest(notice);shutil.copyfile(notice,state/'image-build/sources'/sha)
    spec=dict(url='https://example.invalid/NOTICE',sha256=sha,destination='NOTICE',archive=False)
    p=replace(p,sources=(*p.sources,spec),licensing=copy.deepcopy(p.licensing))
    p.licensing['evidence'].append(dict(path='NOTICE',sha256=sha,source_sha256=sha))
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    raw=[item for item in receipt['evidence'] if item['source_sha256']==sha][0]
    assert raw['origin']=='declared-raw-source'
    assert receipt['supplementary_notices']==[]

def test_same_payload_distinct_supplementary_declarations_are_preserved(fixture):
    p,source,output,state,text,first_spec=supplementary_fixture(fixture)
    sha=first_spec['sha256']
    second_spec=dict(url='https://mirror.example.invalid/other/LICENSE',
                     sha256=sha,destination='supplementary/other/LICENSE',archive=False)
    p=replace(p,sources=(*p.sources,second_spec),licensing=copy.deepcopy(p.licensing))
    p.licensing['supplementary_notices'].append(dict(
        contract='image-build-supplementary-notice-v1',
        id='same-bytes-other-scope',
        source=second_spec,
        upstream=dict(repository='https://github.com/other/project',
                      revision='2'*40,path='LICENSE'),
        path='LICENSE',
        scope='Distinct reviewed scope sharing byte-identical standard text',
        notes='Distinct declaration identity; payload storage remains content-addressed.',
    ))
    validate(p.licensing)
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    assert len(receipt['supplementary_notices'])==2
    assert len({item['source']['sha256'] for item in receipt['supplementary_notices']})==1
    assert len({item['source']['destination'] for item in receipt['supplementary_notices']})==2
    assert len({item['installed_path'] for item in receipt['supplementary_notices']})==2
    assert receipt['unreviewed_sources']==[]
    selection=publish(output,state)
    assert release_check(selection.root.parent,state)['eligible']


def test_supplementary_notice_conflicting_destination_is_rejected(fixture):
    p,_,_,_,_,_=supplementary_fixture(fixture)
    other=copy.deepcopy(p.licensing['supplementary_notices'][0])
    other['id']='different-id'
    other['scope']='different scope'
    p.licensing['supplementary_notices'].append(other)
    with pytest.raises(ImageBuildError,match='conflicting supplementary notice destination'):
        validate(p.licensing)


def test_actual_39_notice_declaration_set_accepts_repeated_payload_hashes(fixture):
    fixture_path=Path(__file__).with_name('fixtures')/'supplementary-notice-39-declarations.json'
    declarations=json.loads(fixture_path.read_text())
    assert len(declarations)==39
    assert len({item['id'] for item in declarations})==39
    assert len({item['source']['destination'] for item in declarations})==39
    assert len({item['source']['sha256'] for item in declarations})==20
    p,*_=fixture
    record=copy.deepcopy(p.licensing)
    record['supplementary_notices']=declarations
    assert validate(record)['supplementary_notices']==declarations

def canonical_web_fixture(fixture):
    p,source,output,state=fixture
    canonical_url='https://www.apache.org/licenses/LICENSE-2.0.txt'
    incorporated_url='http://www.apache.org/licenses/LICENSE-2.0'
    readme=('License terms: '+incorporated_url+'\n').encode()
    license_bytes=(source/'src/demo/LICENSE').read_bytes()
    archive=state/'canonical-primary.tar'
    with tarfile.open(archive,'w') as tar:
        member=tarfile.TarInfo('demo/LICENSE');member.size=len(license_bytes)
        tar.addfile(member,io.BytesIO(license_bytes))
        member=tarfile.TarInfo('demo/README.md');member.size=len(readme)
        tar.addfile(member,io.BytesIO(readme))
    primary_sha=digest(archive)
    cache=state/'image-build/sources'
    shutil.copyfile(archive,cache/primary_sha)
    primary=dict(url=archive.as_uri(),sha256=primary_sha,destination='src',archive=True)
    record=copy.deepcopy(p.licensing)
    record['source']=dict(url=archive.as_uri(),sha256=primary_sha)
    record['evidence'][0]['source_sha256']=primary_sha
    notice=b'Canonical web license text fixture\n'
    notice_sha=__import__('hashlib').sha256(notice).hexdigest()
    notice_spec=dict(url=canonical_url,sha256=notice_sha,
                     destination='supplementary/linux-keyutils/LICENSE-2.0.txt',archive=False)
    (cache/notice_sha).write_bytes(notice)
    record['supplementary_notices']=[dict(
        contract='image-build-supplementary-notice-v1',
        id='canonical-apache-2.0',
        source=notice_spec,
        canonical_web=dict(
            contract='image-build-canonical-web-notice-provenance-v1',
            incorporated_url=incorporated_url,
            incorporated_by=dict(source_sha256=primary_sha,
                                 path='demo/README.md',
                                 sha256=__import__('hashlib').sha256(readme).hexdigest()),
        ),
        path='LICENSE-2.0.txt',
        scope='Source-bound canonical Apache-2.0 incorporation',
        notes='Canonical web text referenced by the exact packaged source README.',
    )]
    p=replace(p,sources=(primary,notice_spec),licensing=record)
    return p,source,output,state


def test_canonical_web_notice_is_bound_to_primary_archive_incorporation(fixture):
    p,source,output,state=canonical_web_fixture(fixture)
    validate(p.licensing)
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    item=receipt['supplementary_notices'][0]
    assert item['provenance_class']=='source-incorporated-canonical-web-text'
    assert item['source']['url']=='https://www.apache.org/licenses/LICENSE-2.0.txt'
    assert item['canonical_web']['incorporated_url']=='http://www.apache.org/licenses/LICENSE-2.0'
    selection=publish(output,state)
    assert release_check(selection.root.parent,state)['eligible']


@pytest.mark.parametrize('fault',['wrong-binding-hash','wrong-binding-path','url-not-incorporated'])
def test_canonical_web_notice_binding_fails_closed(fixture,fault):
    p,source,output,state=canonical_web_fixture(fixture)
    item=p.licensing['supplementary_notices'][0]
    if fault=='wrong-binding-hash':
        item['canonical_web']['incorporated_by']['sha256']='0'*64
    elif fault=='wrong-binding-path':
        item['canonical_web']['incorporated_by']['path']='demo/MISSING.md'
    else:
        item['canonical_web']['incorporated_url']='http://www.apache.org/licenses/OTHER'
        item['path']='OTHER.txt'
        item['source']['destination']='supplementary/linux-keyutils/OTHER.txt'
    with pytest.raises(ImageBuildError):
        preserve(p,source,output,state)


def test_linux_keyutils_canonical_web_declaration_shape_is_supported(fixture):
    p,*_=fixture
    record=copy.deepcopy(p.licensing)
    record['status']='declared'
    record['source']={
        'url':'https://static.crates.io/crates/linux-keyutils/linux-keyutils-0.2.5.crate',
        'sha256':'83270a18e9f90d0707c41e9f35efada77b64c0e6f3f1810e71c8368a864d5590',
    }
    record['supplementary_notices']=[{
        'contract':'image-build-supplementary-notice-v1',
        'id':'eeb4fb3866d81e6d8ff49719-apache-2.0',
        'source':{
            'url':'https://www.apache.org/licenses/LICENSE-2.0.txt',
            'sha256':'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
            'destination':'supplementary/eeb4fb3866d81e6d8ff49719-apache-2.0/LICENSE-2.0.txt',
            'archive':False,
        },
        'canonical_web':{
            'contract':'image-build-canonical-web-notice-provenance-v1',
            'incorporated_url':'http://www.apache.org/licenses/LICENSE-2.0',
            'incorporated_by':{
                'source_sha256':'83270a18e9f90d0707c41e9f35efada77b64c0e6f3f1810e71c8368a864d5590',
                'path':'linux-keyutils-0.2.5/README.md',
                'sha256':'60eaaa21859394c2a1679d47763c4d2c31b3fdab7de327ac72f4b4244cac5695',
            },
        },
        'path':'LICENSE-2.0.txt',
        'scope':'linux-keyutils 0.2.5 Apache-2.0 option',
        'notes':'Exact packaged README incorporates the canonical Apache-2.0 text by URL.',
    }]
    validate(record)

LINUX_KEYUTILS_SOURCE = {
    'url':'https://static.crates.io/crates/linux-keyutils/linux-keyutils-0.2.5.crate',
    'sha256':'83270a18e9f90d0707c41e9f35efada77b64c0e6f3f1810e71c8368a864d5590',
    'destination':'crates/linux-keyutils-0.2.5',
    'archive':True,
}
LINUX_KEYUTILS_README_SHA256 = '60eaaa21859394c2a1679d47763c4d2c31b3fdab7de327ac72f4b4244cac5695'
APACHE_CANONICAL_NOTICE_SOURCE = {
    'url':'https://www.apache.org/licenses/LICENSE-2.0.txt',
    'sha256':'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
    'destination':'supplementary/eeb4fb3866d81e6d8ff49719-apache-2.0/LICENSE-2.0.txt',
    'archive':False,
}


def _linux_keyutils_nested_declaration(nested=LINUX_KEYUTILS_SOURCE,
                                       notice=APACHE_CANONICAL_NOTICE_SOURCE):
    return {
        'contract':'image-build-supplementary-notice-v1',
        'id':'eeb4fb3866d81e6d8ff49719-apache-2.0',
        'source':copy.deepcopy(notice),
        'canonical_web':{
            'contract':'image-build-canonical-web-notice-provenance-v1',
            'incorporated_url':'http://www.apache.org/licenses/LICENSE-2.0',
            'incorporated_by':{
                'source':copy.deepcopy(nested),
                'path':'linux-keyutils-0.2.5/README.md',
                'sha256':LINUX_KEYUTILS_README_SHA256,
            },
        },
        'path':'LICENSE-2.0.txt',
        'scope':'linux-keyutils 0.2.5 Apache-2.0 option',
        'notes':'Exact packaged README incorporates the canonical Apache-2.0 text by URL.',
    }


def _real_maturin_nested_record():
    stage=Path(__file__).parents[1]/'project/package/python-maturin/stages/final'
    package=load_package(stage)
    nested=[source for source in package.sources if source==LINUX_KEYUTILS_SOURCE]
    assert nested==[LINUX_KEYUTILS_SOURCE]
    record=copy.deepcopy(package.licensing)
    record['supplementary_notices']=[_linux_keyutils_nested_declaration()]
    return record,tuple(package.sources)+(copy.deepcopy(APACHE_CANONICAL_NOTICE_SOURCE),)


def test_real_maturin_linux_keyutils_nested_binding_matches_selected_stage_source():
    record,sources=_real_maturin_nested_record()
    assert record['source']['sha256']!=LINUX_KEYUTILS_SOURCE['sha256']
    assert validate(record,sources)['supplementary_notices'][0]['canonical_web']['incorporated_by']['source']==LINUX_KEYUTILS_SOURCE


@pytest.mark.parametrize('fault',[
    'missing-selected-sources','wrong-url','wrong-destination','wrong-hash',
    'wrong-archive','duplicate-candidate','primary-swap','missing-source',
])
def test_real_maturin_linux_keyutils_nested_binding_fails_closed(fault):
    record,sources=_real_maturin_nested_record()
    binding=record['supplementary_notices'][0]['canonical_web']['incorporated_by']
    nested=binding['source']
    if fault=='missing-selected-sources':
        sources=None
    elif fault=='wrong-url':
        nested['url']='https://static.crates.io/crates/linux-keyutils/other.crate'
    elif fault=='wrong-destination':
        nested['destination']='crates/linux-keyutils-0.2.5-other'
    elif fault=='wrong-hash':
        nested['sha256']='0'*64
    elif fault=='wrong-archive':
        nested['archive']=False
    elif fault=='duplicate-candidate':
        sources=sources+(copy.deepcopy(LINUX_KEYUTILS_SOURCE),)
    elif fault=='primary-swap':
        binding['source']=copy.deepcopy(next(source for source in sources
            if source['sha256']==record['source']['sha256']))
    else:
        sources=tuple(source for source in sources if source!=LINUX_KEYUTILS_SOURCE)
    with pytest.raises(ImageBuildError):
        validate(record,sources)


def nested_canonical_web_fixture(fixture):
    p,source,output,state=fixture
    incorporated_url='http://www.apache.org/licenses/LICENSE-2.0'
    readme=('linux-keyutils Apache option: '+incorporated_url+'\n').encode()
    archive=state/'linux-keyutils-0.2.5.crate'
    with tarfile.open(archive,'w') as tar:
        member=tarfile.TarInfo('linux-keyutils-0.2.5/README.md')
        member.size=len(readme);tar.addfile(member,io.BytesIO(readme))
    nested_sha=digest(archive)
    cache=state/'image-build/sources';shutil.copyfile(archive,cache/nested_sha)
    nested=dict(LINUX_KEYUTILS_SOURCE,sha256=nested_sha)
    notice=b'Canonical Apache notice fixture\n'
    notice_sha=__import__('hashlib').sha256(notice).hexdigest()
    notice_spec=dict(APACHE_CANONICAL_NOTICE_SOURCE,sha256=notice_sha)
    (cache/notice_sha).write_bytes(notice)
    record=copy.deepcopy(p.licensing)
    item=_linux_keyutils_nested_declaration(nested,notice_spec)
    item['canonical_web']['incorporated_by']['sha256']=__import__('hashlib').sha256(readme).hexdigest()
    record['supplementary_notices']=[item]
    p=replace(p,sources=(*p.sources,nested,notice_spec),licensing=record)
    return p,source,output,state,nested,notice_spec,readme


def test_nested_canonical_web_notice_preserves_exact_archive_and_audits_offline(fixture):
    p,source,output,state,nested,_,_=nested_canonical_web_fixture(fixture)
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    assert nested['sha256'] in receipt['unreviewed_sources']
    assert receipt['supplementary_notices'][0]['provenance_class']=='source-incorporated-canonical-web-text'
    shutil.rmtree(source);shutil.rmtree(state/'image-build/sources')
    selection=publish(output,state)
    audited=release_check(selection.root.parent,state)
    assert not audited['eligible']
    assert any('additional source/patch licensing unresolved' in issue for issue in audited['issues'])
    assert not any('canonical web notice provenance changed' in issue for issue in audited['issues'])


@pytest.mark.parametrize('fault',['missing-readme','changed-readme','nonregular-readme','url-not-incorporated'])
def test_nested_canonical_web_member_binding_fails_closed(fixture,fault):
    p,source,output,state,nested,_,readme=nested_canonical_web_fixture(fixture)
    replacement=state/('replacement-'+fault+'.crate')
    with tarfile.open(replacement,'w') as tar:
        if fault=='missing-readme':
            data=b'other\n';member=tarfile.TarInfo('linux-keyutils-0.2.5/OTHER')
            member.size=len(data);tar.addfile(member,io.BytesIO(data))
        elif fault=='changed-readme':
            data=readme+b'changed\n';member=tarfile.TarInfo('linux-keyutils-0.2.5/README.md')
            member.size=len(data);tar.addfile(member,io.BytesIO(data))
        elif fault=='nonregular-readme':
            member=tarfile.TarInfo('linux-keyutils-0.2.5/README.md')
            member.type=tarfile.SYMTYPE;member.linkname='OTHER';tar.addfile(member)
        else:
            data=b'No canonical license URL here\n'
            member=tarfile.TarInfo('linux-keyutils-0.2.5/README.md')
            member.size=len(data);tar.addfile(member,io.BytesIO(data))
    changed=dict(nested,sha256=digest(replacement))
    shutil.copyfile(replacement,state/'image-build/sources'/changed['sha256'])
    p=replace(p,sources=tuple(changed if source_spec==nested else source_spec for source_spec in p.sources),
              licensing=copy.deepcopy(p.licensing))
    binding=p.licensing['supplementary_notices'][0]['canonical_web']['incorporated_by']
    binding['source']=changed
    if fault=='url-not-incorporated':
        binding['sha256']=__import__('hashlib').sha256(data).hexdigest()
    with pytest.raises(ImageBuildError):
        preserve(p,source,output,state)


def test_real_maturin_full40_source_roles_do_not_drop_ordinary_evidence(tmp_path):
    from zog.image_build.licensing import _supplementary_source_roles, supplementary_notices
    stage=Path(__file__).parents[1]/'project/package/python-maturin/stages/final'
    package=load_package(stage)
    record=copy.deepcopy(package.licensing)
    before=copy.deepcopy(record['evidence'])
    declarations=json.loads((Path(__file__).with_name('fixtures')/'supplementary-notice-39-declarations.json').read_text())
    assert len(declarations)==39
    record['supplementary_notices']=declarations+[_linux_keyutils_nested_declaration()]
    sources=list(package.sources)
    for item in record['supplementary_notices']:
        if item['source'] not in sources:
            sources.append(copy.deepcopy(item['source']))
    package=replace(package,sources=tuple(sources),licensing=record)
    notices=supplementary_notices(record,package.sources)
    supplementary,nested=_supplementary_source_roles(package,tmp_path,record,notices)
    assert len(notices)==40
    assert record['evidence']==before
    assert len(before)>=830  # Work's reconstructed integration candidate exercises all 990 rows.
    assert LINUX_KEYUTILS_SOURCE in nested
    assert all(source['archive'] is False for source in supplementary)


def test_nested_canonical_web_archive_can_also_supply_ordinary_evidence(fixture):
    p,source,output,state,nested,_,readme=nested_canonical_web_fixture(fixture)
    cargo={
        'linux-keyutils-0.2.5/Cargo.toml':b'[package]\nname = "linux-keyutils"\n',
        'linux-keyutils-0.2.5/Cargo.toml.orig':b'[package]\nname = "linux-keyutils"\n# original\n',
    }
    replacement=state/'linux-keyutils-with-evidence.crate'
    with tarfile.open(replacement,'w') as tar:
        for name,data in {'linux-keyutils-0.2.5/README.md':readme,**cargo}.items():
            member=tarfile.TarInfo(name);member.size=len(data)
            tar.addfile(member,io.BytesIO(data))
    updated=dict(nested,sha256=digest(replacement))
    shutil.copyfile(replacement,state/'image-build/sources'/updated['sha256'])
    extracted=source/updated['destination']
    for name,data in {'linux-keyutils-0.2.5/README.md':readme,**cargo}.items():
        path=extracted/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    p=replace(p,sources=tuple(updated if spec==nested else spec for spec in p.sources),
              licensing=copy.deepcopy(p.licensing))
    binding=p.licensing['supplementary_notices'][0]['canonical_web']['incorporated_by']
    binding['source']=updated
    for name,data in cargo.items():
        p.licensing['evidence'].append({
            'path':name,
            'sha256':__import__('hashlib').sha256(data).hexdigest(),
            'source_sha256':updated['sha256'],
        })
    result=preserve(p,source,output,state)
    receipt=json.loads((output/result['receipt']).read_text())
    kept={(item['source_sha256'],item['path']) for item in receipt['evidence']}
    assert {(updated['sha256'],name) for name in cargo} <= kept
    assert updated['sha256'] in receipt['unreviewed_sources']


def test_supplementary_raw_notice_still_cannot_be_ordinary_evidence(fixture):
    p,source,output,state,_,notice_spec,_=nested_canonical_web_fixture(fixture)
    p.licensing['evidence'].append({
        'path':notice_spec['destination'].rsplit('/',1)[-1],
        'sha256':notice_spec['sha256'],
        'source_sha256':notice_spec['sha256'],
    })
    with pytest.raises(ImageBuildError,match='supplementary notice cannot also be ordinary evidence'):
        preserve(p,source,output,state)


def test_recipe_snapshot_materialization_passes_selected_sources_to_nested_license(tmp_path):
    from zog.image_build.recipe_snapshots import _materialize_one
    root=Path(__file__).parents[1]/'project/package'
    catalogue=tmp_path/'catalogue'
    shutil.copytree(root/'python-maturin',catalogue/'python-maturin')
    stage=catalogue/'python-maturin/stages/final'
    selected=literal(stage/'sources.py')
    assert LINUX_KEYUTILS_SOURCE in selected
    apache_destination=APACHE_CANONICAL_NOTICE_SOURCE['destination']
    existing=[source for source in selected
              if source.get('destination')==apache_destination]
    assert all(source==APACHE_CANONICAL_NOTICE_SOURCE for source in existing)
    assert len(existing)<=1
    if not existing:
        selected.append(copy.deepcopy(APACHE_CANONICAL_NOTICE_SOURCE))
    (stage/'sources.py').write_text(repr(selected))
    record=literal(catalogue/'python-maturin/license.py')
    record['supplementary_notices']=[_linux_keyutils_nested_declaration()]
    (catalogue/'python-maturin/license.py').write_text(repr(record))
    destination=tmp_path/'snapshot';destination.mkdir()
    _materialize_one(catalogue,destination,{
        'id':'python-maturin',
        'project':'python-maturin',
        'recipe':'python-maturin/stages/final',
    })
    snap=load_package(destination/'python-maturin')
    assert snap.licensing['supplementary_notices'][0]['canonical_web']['incorporated_by']['source']==LINUX_KEYUTILS_SOURCE


@pytest.mark.parametrize('fault',['symlink-archive','changed-archive','wrong-web-notice-hash','patch-alias','supplementary-reuse'])
def test_nested_canonical_web_source_overlap_and_archive_tampering_fail_closed(fixture,fault,tmp_path):
    p,source,output,state,nested,notice_spec,_=nested_canonical_web_fixture(fixture)
    cache=state/'image-build/sources'/nested['sha256']
    if fault=='symlink-archive':
        external=tmp_path/'external.crate';shutil.copyfile(cache,external);cache.unlink();cache.symlink_to(external)
    elif fault=='changed-archive':
        cache.write_bytes(b'changed archive bytes')
    elif fault=='wrong-web-notice-hash':
        p.licensing['supplementary_notices'][0]['source']['sha256']='f'*64
    elif fault=='patch-alias':
        alias=dict(url='https://example.invalid/linux-keyutils.patch',sha256=nested['sha256'],
                   destination='patches/linux-keyutils.patch',archive=False)
        p=replace(p,sources=(*p.sources,alias),integration=copy.deepcopy(p.integration))
        p.integration['stage_id']='final'
        p.integration['patches']=[dict(id='nested-hash-alias',order=1,
            applies_to=dict(version=p.licensing['version'],stage='final'),source=alias,
            files=[dict(path='README.md',before_sha256='0'*64,after_sha256='1'*64)])]
    else:
        reused=dict(notice_spec,sha256=nested['sha256'])
        p=replace(p,sources=tuple(reused if source_spec==notice_spec else source_spec for source_spec in p.sources),
                  licensing=copy.deepcopy(p.licensing))
        p.licensing['supplementary_notices'][0]['source']=reused
    with pytest.raises(ImageBuildError):
        preserve(p,source,output,state)


def test_nested_canonical_web_retained_archive_tampering_is_release_checked(fixture):
    p,source,output,state,nested,_,_=nested_canonical_web_fixture(fixture)
    preserve(p,source,output,state)
    selection=publish(output,state)
    (state/'image-build/release-inputs'/nested['sha256']).write_bytes(b'tampered')
    result=release_check(selection.root.parent,state)
    assert not result['eligible']
    assert any('canonical web notice provenance changed' in issue for issue in result['issues'])


def test_nested_canonical_web_receipt_tampering_is_release_checked(fixture):
    p,source,output,state,_,_,_=nested_canonical_web_fixture(fixture)
    result=preserve(p,source,output,state)
    receipt_path=output/result['receipt']
    receipt=json.loads(receipt_path.read_text())
    receipt['supplementary_notices'][0]['canonical_web']['incorporated_by']['source']['destination']='changed'
    receipt_path.write_text(json.dumps(receipt))
    selection=publish(output,state)
    result=release_check(selection.root.parent,state)
    assert not result['eligible']
    assert any('supplementary notice delivery changed' in issue for issue in result['issues'])


@pytest.mark.parametrize('fault',['revision','repository','path','encoded-path','double-slash','moving-head'])
def test_raw_github_supplementary_notice_url_is_bound_to_declared_git_provenance(fixture,fault):
    declarations=json.loads((Path(__file__).with_name('fixtures')/'supplementary-notice-39-declarations.json').read_text())
    item=copy.deepcopy(declarations[0])
    revision=item['upstream']['revision']
    if fault=='revision':
        item['upstream']['revision']='0'*40
    elif fault=='repository':
        item['upstream']['repository']='https://github.com/other/project'
    elif fault=='path':
        item['upstream']['path']='other/'+item['upstream']['path']
    elif fault=='encoded-path':
        item['source']['url']=item['source']['url'].replace('/LICENSE','/%4cICENSE')
    elif fault=='double-slash':
        item['source']['url']=item['source']['url'].replace('/'+revision+'/','//'+revision+'/')
    else:
        item['source']['url']=item['source']['url'].replace('/'+revision+'/','/main/')
    p,*_=fixture
    record=copy.deepcopy(p.licensing);record['supplementary_notices']=[item]
    with pytest.raises(ImageBuildError):
        validate(record)


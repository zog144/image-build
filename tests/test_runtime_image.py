import json
from pathlib import Path

import pytest
from zog.image_build import read_selection
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory
from zog.image_build import generation_provenance as gp, installed_verification as iv
from zog.image_build.rootfs_compatibility import derive
from zog.image_build.runtime_image import publish, _same_contents, MOUNTPOINTS
from zog.image_build.runtime_facilities import FIELD as FACILITY_FIELD, ROOTS
from zog.image_build.application_data_targets import (
    FIELD as DATA_TARGET_FIELD,
    definition as data_target_definition,
)
from zog.image_build.metadata import Package, identity


def accepted(tmp_path):
    from test_installed_verification import scenario
    s = scenario(tmp_path, contract=False)
    # Model the retained production failure exactly: D-Bus contributes an empty
    # /run/dbus package directory to the accepted runtime. Rebind only the fixture
    # package provenance; runtime_image must not mutate this accepted input.
    (s.root/'run/dbus').mkdir(parents=True)
    record=dict(inputs={},outputs=inventory(s.root));record['identity']=identity(record)
    record.update(root=str(s.root),provenance=s.p.legacy_output('base',record))
    s.built={'base':record}
    # Produce a separate fixture base with an actual canonical installed report.
    descriptor = derive(s.built, 'x86_64')
    owner = dict(s.owner, kind='toolchain', stage=2, architecture='x86_64',
                 application_software_compatibility=descriptor,
                 provenance=s.p.configuration(), verification_report_contract=iv.CONTRACT)
    attempt = s.builder.state/'image-build/attempts/runtime-base'
    binding = gp.prepare(s.p, attempt, {'base':Package('base',(),(),(),{},{},(),{})}, ['base'], s.built, owner)
    from zog.image_build.developer.seed_build import verify
    from zog.image_build.final_compiler import successful_execution
    check = s.builder.state/'image-build/attempts/runtime-check'
    verify(s.builder,check,s.root,[['/bin/bash','-eu','-c','fixture-check']],owner)
    execution = successful_execution(check)
    report = iv.capture(s.p,binding,s.root,owner,check,execution)
    pointer = gp.finish(s.p,attempt,binding,s.root,verification=[report])
    # This fixture models the legacy live producer, which does not auto-publish
    # observation snapshots. New image publication below uses the real path.
    from unittest.mock import patch
    with patch.object(s.builder, '_publish_observation_snapshot', return_value=None):
        base = s.builder._publish(s.root,owner,'toolchain',dict(stage=2,self_hosted=True,
            application_software_compatibility=descriptor,build_record=pointer,
            verification_execution=execution,
            packages={n:{k:v for k,v in r.items() if k!='root'} for n,r in s.built.items()}))
    return s,base


def test_publication_is_new_inactive_image_with_base_evidence_and_consumer_binding(tmp_path):
    s,base=accepted(tmp_path)
    original=(base.root.parent/'manifest.json').read_bytes()
    active=s.builder.state/'image-build/active';active.symlink_to(base.root.parent)
    calls=len(s.calls)
    result=publish(s.builder,base.root.parent,{'base':s.root},tmp_path/'runtime-image','a'*40)
    selected=read_selection(Path(result['root']).parent)
    assert selected.manifest['kind']==selected.manifest['inputs']['kind']=='image'
    assert selected.generation!=base.generation
    assert selected.manifest['application_software_compatibility']==base.manifest['application_software_compatibility']
    assert len(s.calls)==calls and active.resolve()==base.root.parent
    assert (base.root.parent/'manifest.json').read_bytes()==original
    assert selected.manifest['verification_inherited_from']==base.generation
    assert (base.root/'run/dbus').is_dir()
    assert selected.manifest[FACILITY_FIELD]==selected.manifest['inputs'][FACILITY_FIELD]
    assert selected.manifest[FACILITY_FIELD]['directories']==[dict(
        path='/run/dbus',mode=0o755,packages=['base'],materialization='runtime-owner')]
    for name in ROOTS:
        facility=selected.root/name
        assert facility.is_dir() and not facility.is_symlink() and not list(facility.iterdir())
    assert not (selected.root/'run/dbus').exists()
    assert (
        selected.manifest[DATA_TARGET_FIELD]
        == selected.manifest['inputs'][DATA_TARGET_FIELD]
        == data_target_definition()
    )
    for target in selected.manifest[DATA_TARGET_FIELD]['targets']:
        path = selected.root / target['path'].lstrip('/')
        assert path.is_dir() and not path.is_symlink()
        assert list(path.iterdir()) == []
        assert path.stat().st_mode & 0o7777 == target['mode']
    from zog.box_control.runtime.scaffold import rootfs_layout, rootfs_bind_paths
    binds,symlinks=rootfs_layout(selected.root)
    assert not any(target in {'/'+name for name in ROOTS} for _source,target,_kind in binds)
    assert rootfs_bind_paths(selected.root)==tuple((source,target) for source,target,_kind in binds)
    assert symlinks==()
    artifact=selected.manifest['inputs']['accepted_runtime_evidence']
    evidence=json.loads((s.p.root/'artifacts'/artifact['digest'][7:]).read_text())
    assert base.manifest['build_record']['record'] in evidence['records']
    assert evidence['records'][base.manifest['build_record']['record']]['data']['verification']
    assert gp.verify(s.p,selected)
    assert publish(s.builder,base.root.parent,{'base':s.root},tmp_path/'runtime-image','a'*40)==result
    from zog.box_control.images import published_selection, ImageProviderError
    with pytest.raises(ImageProviderError,match='not a toolchain'):
        published_selection(tmp_path,base.generation)
    consumer=published_selection(tmp_path,selected.generation)
    from zog.box_control.application_software import rootfs_compatibility
    value=rootfs_compatibility(consumer)
    from zog.image_build.application_software import ApplicationSoftwareStore
    from zog.image_build.application_views import ApplicationSoftwareViewStore
    store=ApplicationSoftwareStore(tmp_path/'apps')
    prepared=store.begin('probe',application='fixture',revision='git:'+'b'*40,
        sources=[dict(name='probe',url='https://example.invalid/probe',sha256='1'*64)],
        compatibility_requirements=value,notices=(),provenance={'fixture':True})
    (prepared.root/'probe').write_text('consumer fixture')
    artifact=store.finalize('probe')
    views=ApplicationSoftwareViewStore(tmp_path/'apps')
    view=views.publish('probe-view',application='fixture',artifacts=[artifact.artifact])
    assert views.consumer_manifest(view.view,value)['rootfs_compatibility']==value


def test_reject_changed_components_and_frozen_operation(tmp_path):
    s,base=accepted(tmp_path)
    with pytest.raises(ImageBuildError,match='exact accepted'):
        publish(s.builder,base.root.parent,{},tmp_path/'runtime-image','a'*40)
    result=publish(s.builder,base.root.parent,{'base':s.root},tmp_path/'runtime-image','a'*40)
    with pytest.raises(ImageBuildError,match='frozen runtime'):
        publish(s.builder,base.root.parent,{'base':s.root},tmp_path/'runtime-image','b'*40)
    (s.root/'payload').write_text('changed')
    with pytest.raises(ImageBuildError,match='package output changed'):
        publish(s.builder,base.root.parent,{'base':s.root},tmp_path/'other-image','a'*40)
    assert read_selection(Path(result['root']).parent)


def test_contents_gate_rejects_added_file_removed_file_or_changed_mode():
    base=[dict(path='payload',kind='file',mode=0o644,sha256='1'*64,size=1)]
    directories=[dict(path=n,kind='directory',mode=m) for n,m in MOUNTPOINTS.items()]
    empty_intent={'directories': []}
    _same_contents(base,base+directories,empty_intent)
    for candidate in [directories,base+directories+[dict(path='extra',kind='directory',mode=0o755)],
                      [dict(base[0],mode=0o755)]+directories]:
        with pytest.raises(ImageBuildError,match='differs from accepted'):_same_contents(base,candidate,empty_intent)

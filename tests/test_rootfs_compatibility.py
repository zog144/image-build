import json
from pathlib import Path
import pytest
from zog.image_build import ImageBuild, read_selection
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory
from zog.image_build.rootfs_compatibility import derive, FIELD
from zog.image_build.application_software import compatibility_gaps


def fixture(tmp_path):
    root = tmp_path/'package'; root.mkdir()
    def put(name, raw):
        p = root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    put('usr/lib/python3.15/_sysconfigdata_test.py', b"build_time_vars = {'VERSION': '3.15', 'SOABI': 'cpython-315-x86_64-linux-gnu'}\n")
    put('usr/include/python3.15/patchlevel.h', b'#define PY_VERSION "3.15.0"\n')
    put('usr/bin/python3.15', b'\x7fELF\x02\x01'+bytes(12)+bytes([62, 0]))
    return root, {'python': dict(root=str(root), outputs=inventory(root))}


def test_selected_package_metadata_is_frozen_and_round_trips(tmp_path):
    root, built = fixture(tmp_path)
    value = derive(built, 'x86_64')
    assert value['python'] == dict(implementation='cpython', version='3.15.0', soabi='cpython-315-x86_64-linux-gnu')
    builder = ImageBuild(package_dir=tmp_path/'recipes', state_dir=tmp_path/'state')
    inputs = {'kind': 'image', FIELD: value}
    selection = builder._publish(root, inputs, 'image', {FIELD: value})
    assert read_selection(selection.root.parent).manifest[FIELD] == value
    from zog.image_build.host_export import export, verify
    exported = export(selection.root.parent, tmp_path/'export', {'packages': [], 'acceptance': []})
    assert verify(tmp_path/'export', exported['artifact_id'])['generation'][FIELD] == value
    manifest_path = selection.root.parent/'manifest.json'
    manifest = json.loads(manifest_path.read_text()); manifest[FIELD]['python']['version'] = 'host'
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ImageBuildError, match='not frozen'):
        read_selection(selection.root.parent)


def test_cannot_supply_unbound_host_descriptor(tmp_path):
    root, built = fixture(tmp_path)
    value = derive(built, 'x86_64')
    builder = ImageBuild(package_dir=tmp_path/'recipes', state_dir=tmp_path/'state')
    with pytest.raises(ImageBuildError):
        builder._publish(root, {'kind': 'image'}, 'image', {FIELD: value})
    guessed = dict(value, libraries=['host-only.so.1'])
    with pytest.raises(ImageBuildError, match='differs from candidate contents'):
        builder._publish(root, {'kind': 'image', FIELD: guessed}, 'image', {FIELD: guessed})
    (root/'usr/include/python3.15/patchlevel.h').write_text('#define PY_VERSION "host"')
    with pytest.raises(ImageBuildError, match='inventory changed'):
        derive(built, 'x86_64')


def test_reject_wrong_architecture_and_missing_python_metadata(tmp_path):
    root, built = fixture(tmp_path)
    with pytest.raises(ImageBuildError, match='architecture differs'):
        derive(built, 'aarch64')
    (root/'usr/lib/python3.15/_sysconfigdata_test.py').unlink()
    built['python']['outputs'] = inventory(root)
    with pytest.raises(ImageBuildError, match='without declared ABI'):
        derive(built, 'x86_64')


def test_no_host_python_or_library_fallback(tmp_path):
    root = tmp_path/'empty'; root.mkdir()
    value = derive({'empty': dict(root=str(root), outputs=[])}, 'x86_64')
    assert value['python'] is None and value['libraries'] == []
    required = dict(value, libraries=['undeclared.so.1'])
    assert compatibility_gaps(required, value)


def test_derived_descriptor_binds_multiple_application_artifacts(tmp_path):
    from zog.image_build.application_software import ApplicationSoftwareStore
    from zog.image_build.application_views import ApplicationSoftwareViewStore
    _, built = fixture(tmp_path)
    value = derive(built, 'x86_64')
    store = ApplicationSoftwareStore(tmp_path/'apps')
    artifacts = []
    for name in ('backend', 'frontend'):
        prepared = store.begin(name, application='fixture-app', revision='git:'+'a'*40,
            sources=[dict(name=name, url='https://example.invalid/'+name+'.tar', sha256='1'*64)],
            compatibility_requirements=value, notices=(), provenance={'fixture': name})
        (prepared.root/name).write_text('fixture only')
        artifacts.append(store.finalize(name).artifact)
    views = ApplicationSoftwareViewStore(tmp_path/'apps')
    view = views.publish('fixture-view', application='fixture-app', artifacts=artifacts)
    binding = views.consumer_manifest(view.view, value)
    assert binding['contract'] == 'application-software-consumer-v1'
    assert binding['rootfs_compatibility'] == value
    for wrong in (dict(value, architecture='aarch64'),
                  dict(value, python=dict(value['python'], version='different'))):
        with pytest.raises(ImageBuildError):
            views.consumer_manifest(view.view, wrong)

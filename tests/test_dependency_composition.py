import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from zog.image_build.dependency_composition import replacement_plan, remove_inherited, POLICY
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory, merge
from zog.image_build.metadata import identity
from test_source_build import prepared, recipe


def record(root, package):
    value = {'inputs': {'package': package}, 'outputs': inventory(root)}
    return dict(value, identity=identity(value))


def scenario(tmp_path):
    old = tmp_path/'old'; (old/'usr/lib/old-module').mkdir(parents=True)
    (old/'usr/lib/old-module/module.py').write_text('obsolete')
    (old/'usr/lib/library').write_text('old')
    (old/'usr/lib/alias').symlink_to('library')
    other = tmp_path/'other'; (other/'usr/lib').mkdir(parents=True)
    (other/'usr/lib/unrelated').write_text('keep')
    base = tmp_path/'base'; merge(old, base); merge(other, base)
    packages = {'library': record(old, 'library'), 'other': record(other, 'other')}
    selection = SimpleNamespace(root=base, manifest={'packages': packages, 'outputs': inventory(base)})
    stage = tmp_path/'stage'; shutil.copytree(base, stage, symlinks=True)
    return selection, stage


def test_replaces_changed_files_and_removes_obsolete_paths_without_changing_base(tmp_path):
    selection, stage = scenario(tmp_path); before = inventory(selection.root)
    plan = replacement_plan(selection, ['library', 'new-package'])
    assert plan == {'policy': POLICY, 'packages': {'library': selection.manifest['packages']['library']['identity']}}
    remove_inherited(stage, selection, plan)
    assert not (stage/'usr/lib/old-module').exists()
    assert not (stage/'usr/lib/alias').is_symlink()
    new = tmp_path/'new'; (new/'usr/lib').mkdir(parents=True)
    (new/'usr/lib/library').write_text('new'); merge(new, stage, preserve_existing_directories=True)
    assert (stage/'usr/lib/library').read_text() == 'new'
    assert (stage/'usr/lib/unrelated').read_text() == 'keep'
    assert inventory(selection.root) == before


@pytest.mark.parametrize('failure', ['changed', 'shared', 'symlink-parent', 'identity'])
def test_invalid_replacements_fail_before_removing_any_file(tmp_path, failure):
    selection, stage = scenario(tmp_path)
    if failure == 'changed': (stage/'usr/lib/library').write_text('tampered')
    if failure == 'shared':
        item = next(e for e in selection.manifest['packages']['library']['outputs'] if e['path']=='usr/lib/library')
        selection.manifest['packages']['other']['outputs'].append(item)
    if failure == 'symlink-parent':
        (stage/'usr').rename(stage/'saved-usr'); (stage/'usr').symlink_to('saved-usr')
    if failure == 'identity': selection.manifest['packages']['library']['identity'] = 'wrong'
    before = inventory(stage)
    with pytest.raises(ImageBuildError):
        remove_inherited(stage, selection, replacement_plan(selection, ['library']))
    assert inventory(stage) == before


def test_cannot_remove_from_retained_root_or_change_frozen_plan(tmp_path):
    selection, stage = scenario(tmp_path); plan = replacement_plan(selection, ['library'])
    with pytest.raises(ImageBuildError, match='separate staging'):
        remove_inherited(selection.root, selection, plan)
    plan['packages']['library'] = 'different'
    with pytest.raises(ImageBuildError, match='plan changed'):
        remove_inherited(stage, selection, plan)


def test_engine_replaces_dependency_and_binds_policy_in_package_and_generation(prepared):
    builder, runner, _, toolchain = prepared
    before = inventory(toolchain.root)
    recipe(builder.package_dir, 'new-consumer', build=('compiler-second',))
    original = runner.run
    def run(root, source, output, arguments, environment, log):
        if arguments == ['compile', 'new-consumer']:
            assert (root/'usr/share/compiler-second').read_text() == 'replacement'
        original(root, source, output, arguments, environment, log)
        if arguments == ['install', 'compiler-second']:
            (output/'usr/share/compiler-second').write_text('replacement')
    runner.run = run
    result = builder.ensure(['new-consumer'], toolchain=toolchain)
    assert result.manifest['inputs']['inherited_dependency_replacements']['policy'] == POLICY
    expected = result.manifest['inputs']['inherited_dependency_replacements']
    assert result.manifest['packages']['new-consumer']['inputs']['inherited_dependency_replacements'] == expected
    assert inventory(toolchain.root) == before
    count = len(runner.calls)
    assert builder.ensure(['new-consumer'], toolchain=toolchain).reused
    assert len(runner.calls) == count

import ast
from pathlib import Path
import pytest
from zog.image_build.errors import ImageBuildError
from zog.image_build.pins import load, snapshot, validate
from zog.image_build.stages import stage_recipes
from zog.image_build.metadata import identity, load_packages
from test_source_build import prepared


def test_missing_pin_blocks_before_job(prepared):
    builder, runner, _, toolchain = prepared
    (builder.package_dir/'commit-pin.py').unlink()
    before = len(runner.calls)
    with pytest.raises(ImageBuildError):
        builder.ensure(['consumer'], toolchain=toolchain)
    assert len(runner.calls) == before


def test_source_drift_blocks_before_job(prepared):
    builder, runner, _, toolchain = prepared
    path = builder.package_dir/'library/sources.py'
    source = ast.literal_eval(path.read_text())
    source[0]['sha256'] = '0'*64
    path.write_text(repr(source))
    before = len(runner.calls)
    with pytest.raises(ImageBuildError, match='monthly pin'):
        builder.ensure(['consumer'], toolchain=toolchain)
    assert len(runner.calls) == before


def test_monthly_set_covers_catalogue_and_stage_snapshot(tmp_path):
    project = Path(__file__).resolve().parents[1]/'project'
    pins = load(project/'pins/2026-10-01/commit-pin.py')
    assert set(pins['packages']) == {p.name for p in (project/'package').iterdir()}
    stage_recipes(project/'bootstrap/lfs-final-gcc.py', project/'package', tmp_path/'recipes')
    selected = validate(tmp_path/'recipes', load_packages(tmp_path/'recipes'))
    assert selected['date'] == '2026-10-01'
    assert 'gcc-15.3.0' in selected['packages']['gcc-final']['sources'][0]['url']
    with pytest.raises(ImageBuildError):
        stage_recipes(project/'bootstrap/lfs-final-gcc.py', project/'package', tmp_path/'other', pin_date='../escape')


def test_non_first_day_rejected(tmp_path):
    p = tmp_path/'commit-pin.py'
    p.write_text(repr({'schema':1,'date':'2026-10-02','packages':{}}))
    with pytest.raises(ImageBuildError):
        load(p)


def test_materialized_recipe_snapshot_keeps_distinct_monthly_identity(tmp_path):
    project = Path(__file__).resolve().parents[1]/'project'
    monthly = load(project/'pins/2026-10-01/commit-pin.py')
    destination = tmp_path/'recipes'
    destination.mkdir()
    record = snapshot(
        project/'package',
        [{
            'id':'gcc-final',
            'project':'gcc',
            'recipe':'gcc/stages/final',
        }],
        destination,
        pin_date='2026-10-01',
    )
    assert record['monthly_identity'] == identity(monthly)
    assert record['packages']['gcc-final']['project'] == 'gcc'
    assert record['packages']['gcc-final']['recipe'] == 'gcc/stages/final'
    assert load(destination/'commit-pin.py') == record
    assert (destination/'commit-pin.py').read_bytes() != (
        project/'pins/2026-10-01/commit-pin.py'
    ).read_bytes()
    assert snapshot(
        project/'package',
        [{
            'id':'gcc-final',
            'project':'gcc',
            'recipe':'gcc/stages/final',
        }],
        destination,
        pin_date='2026-10-01',
    ) == record


def test_late_reviewed_stage_can_reuse_exact_catalogue_source_without_rewriting_monthly_pin(tmp_path):
    project = Path(__file__).resolve().parents[1]/'project'
    monthly = load(project/'pins/2026-10-01/commit-pin.py')
    destination = tmp_path/'recipes'
    destination.mkdir()
    record = snapshot(
        project/'package',
        [{
            'id':'shadow-login',
            'project':'shadow',
            'recipe':'shadow/stages/login',
            'pin_policy':'catalogue-source',
        }],
        destination,
        pin_date='2026-10-01',
    )
    selected = record['packages']['shadow-login']
    assert record['monthly_identity'] == identity(monthly)
    assert selected['pin_policy'] == 'catalogue-source'
    assert {k:selected['sources'][0][k] for k in ('url','sha256')} == monthly['packages']['shadow']['source']


def test_catalogue_source_policy_rejects_unpinned_source_identity(tmp_path):
    project = Path(__file__).resolve().parents[1]/'project'
    catalogue = tmp_path/'package'
    import shutil
    shutil.copytree(project/'package/shadow', catalogue/'shadow')
    source = ast.literal_eval((catalogue/'shadow/stages/login/sources.py').read_text())
    source[0]['sha256'] = '0'*64
    (catalogue/'shadow/stages/login/sources.py').write_text(repr(source))
    # snapshot expects pins next to the supplied catalogue.
    (tmp_path/'pins').symlink_to(project/'pins', target_is_directory=True)
    destination = tmp_path/'recipes'
    destination.mkdir()
    with pytest.raises(ImageBuildError, match='catalogue-source recipe differs'):
        snapshot(
            catalogue,
            [{
                'id':'shadow-login',
                'project':'shadow',
                'recipe':'shadow/stages/login',
                'pin_policy':'catalogue-source',
            }],
            destination,
            pin_date='2026-10-01',
        )


def test_supplemental_build_source_pin_is_hash_bound_without_rewriting_monthly_pin(tmp_path):
    project = Path(__file__).resolve().parents[1]/'project'
    monthly = load(project/'pins/2026-10-01/commit-pin.py')
    destination = tmp_path/'recipes'
    destination.mkdir()
    record = snapshot(
        project/'package',
        [{
            'id':'pyelftools-build',
            'project':'build-environment',
            'recipe':'build-environment/stages/pyelftools',
            'pin_policy':'supplemental-build-source',
        }],
        destination,
        pin_date='2026-10-01',
    )
    selected = record['packages']['pyelftools-build']
    assert record['monthly_identity'] == identity(monthly)
    assert selected['pin_policy'] == 'supplemental-build-source'
    assert selected['supplemental_pin']['repository_path'] == (
        'project/package/build-environment/stages/pyelftools/supplemental-pin.py'
    )
    supplemental = ast.literal_eval(
        (project/'package/build-environment/stages/pyelftools/supplemental-pin.py').read_text()
    )
    assert selected['supplemental_pin']['identity'] == identity(supplemental)
    assert supplemental['scope'] == 'build-only'
    assert supplemental['sources'] == selected['sources']


def test_supplemental_build_source_policy_rejects_source_drift(tmp_path):
    project = Path(__file__).resolve().parents[1]/'project'
    catalogue = tmp_path/'package'
    import shutil
    shutil.copytree(project/'package/build-environment', catalogue/'build-environment')
    source = ast.literal_eval(
        (catalogue/'build-environment/stages/pyelftools/sources.py').read_text()
    )
    source[0]['sha256'] = '0'*64
    (catalogue/'build-environment/stages/pyelftools/sources.py').write_text(repr(source))
    (tmp_path/'pins').symlink_to(project/'pins', target_is_directory=True)
    destination = tmp_path/'recipes'
    destination.mkdir()
    with pytest.raises(ImageBuildError, match='supplemental build source pin'):
        snapshot(
            catalogue,
            [{
                'id':'pyelftools-build',
                'project':'build-environment',
                'recipe':'build-environment/stages/pyelftools',
                'pin_policy':'supplemental-build-source',
            }],
            destination,
            pin_date='2026-10-01',
        )

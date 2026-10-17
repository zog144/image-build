import ast
from pathlib import Path
from zog.image_build.stages import stage_recipes
from zog.image_build.metadata import load_packages, order

PROJECT = Path(__file__).parents[1]/'project'


def test_coordinated_namespace_refresh_pins_and_dependency_order(tmp_path):
    plan = stage_recipes(PROJECT/'bootstrap/host-enrollment.py', PROJECT/'package', tmp_path/'recipes')
    packages = load_packages(tmp_path/'recipes')
    assert order(packages, plan['targets']) == ('host-identify-final','host-install-final','host-discover-final')
    for name in ('host-identify', 'host-install', 'host-discover'):
        package = packages[name+'-final']
        component = name.replace('-', '_')
        assert any('site-packages/zog/'+component+'/' in path for path in package.outputs)
        tests = '\n'.join(c[-1] for c in package.steps['test'])
        assert 'zog.'+component in tests
        assert package.sources[0]['url'].endswith('/'+package.integration['revision'])
        assert package.licensing['evidence'][0]['source_sha256'] == package.sources[0]['sha256']
    assert packages['host-discover-final'].integration['runtime_requirements'] == ['host-identify==0.3.4', 'host-install==0.4.4']


def test_installed_refresh_rejects_legacy_modules():
    text = (PROJECT/'bootstrap/host-enrollment-check.sh').read_text()
    for name in ('host_identify', 'host_install', 'host_discover'):
        assert 'zog.'+name in text
    assert 'find_spec(legacy) is None' in text
    assert "('host-install','0.4.4')" in text
    assert "('host-discover','0.4.6')" in text
    ast.parse(text.split("<<'ZOG_ENROLLMENT'\n",1)[1].rsplit('\nZOG_ENROLLMENT',1)[0])

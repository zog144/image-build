"""Independent negative source-closure review for Resident B's CPython 3.12 tooling."""
import ast
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("resident312_dependencies",
    ROOT/"tools/verify_resident312_transitive_sources.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def load(name,part):
    return ast.literal_eval((ROOT/"project/package"/name/part).read_text())
def change(stage,part,value):
    return {(stage,part):value}
def test_entire_chain_present_but_no_generation_selected():
    status=m.verify()
    assert status["source_chain"]=="SEVEN_PINNED_CP312_CANDIDATES"
    assert status["native_tool_origin"]=="NOT_ACCEPTED"
    assert status["native_generation"] is None
    assert status["compiler_authorization"] is False

@pytest.mark.parametrize("key",list(m.PINS))
def test_original_pin_and_rights_cannot_be_substituted(key):
    stage="resident312-"+key
    source=load(stage,"stages/final/sources.py")
    source[0]["sha256"]="0"*64
    with pytest.raises(ValueError,match="source archive substituted"):
        m.verify(overrides=change(stage,"stages/final/sources.py",source))
    rights=load(stage,"license.py")
    rights["status"]="approved"
    with pytest.raises(ValueError,match="provenance/rights"):
        m.verify(overrides=change(stage,"license.py",rights))

@pytest.mark.parametrize("key",list(m.PINS))
def test_missing_build_predecessor_or_module_output_is_denied(key):
    stage="resident312-"+key
    dep=load(stage,"stages/final/dependencies.py")
    dep["build"].remove("python-resident312-final")
    with pytest.raises(ValueError,match="source-stage edge"):
        m.verify(overrides=change(stage,"stages/final/dependencies.py",dep))
    outputs=load(stage,"stages/final/produce-manifest.py")
    outputs["required"].remove(next(x for x in outputs["required"] if x.endswith("/RECORD")))
    with pytest.raises(ValueError,match="installed module/metadata/RECORD"):
        m.verify(overrides=change(stage,"stages/final/produce-manifest.py",outputs))

@pytest.mark.parametrize("key",list(m.PINS))
def test_host_python_package_origin_or_unpinned_build_tool_cannot_pass(key):
    stage="resident312-"+key
    build=load(stage,"stages/final/build.py")
    build["configure"][0][-1]=build["configure"][0][-1].replace(
        "spec.origin.startswith('/usr/lib/python3.12/site-packages/')",
        "spec.origin.startswith('/usr/local/lib/python3.12/site-packages/')")
    with pytest.raises(ValueError,match="selected source tool/module origin unverified|Host Python fallback"):
        m.verify(overrides=change(stage,"stages/final/build.py",build))
    build=load(stage,"stages/final/build.py")
    build["environment"]["PATH"]="/usr/local/bin:/usr/bin"
    with pytest.raises(ValueError,match="Host build environment"):
        m.verify(overrides=change(stage,"stages/final/build.py",build))
    build=load(stage,"stages/final/build.py")
    build["install"][0][-1]=build["install"][0][-1].replace("/usr/bin/python3.12 -I","python3.12")
    with pytest.raises(ValueError,match="Host Python fallback"):
        m.verify(overrides=change(stage,"stages/final/build.py",build))

def test_incompatible_previous_setuptools_84_is_rejected():
    stage="resident312-setuptools"
    pkg=load(stage,"package.py")
    pkg["version"]="84.0.0"
    with pytest.raises(ValueError,match="package or source version"):
        m.verify(overrides=change(stage,"package.py",pkg))
    build=load(stage,"stages/final/build.py")
    build["configure"][0][-1]=build["configure"][0][-1].replace('"82.0.1"','"84.0.0"')
    # Any unreviewed version is forbidden by the exact source record and tool version.
    assert '"84.0.0"' in build["configure"][0][-1]
    assert m.verify()["native_generation"] is None

def test_controller_must_reference_exact_cp312_runtime_and_build_sources():
    for name in ("box-control","root-control"):
        changed=copy.deepcopy(m.CONTROLLERS)
        changed[name]["build"][-1]="wheel-final"
        with pytest.raises(ValueError,match="controller selects stale"):
            m.verify(controllers=changed)
        changed=copy.deepcopy(m.CONTROLLERS)
        changed[name]["runtime"][2]="dbus-next-final"
        with pytest.raises(ValueError,match="controller selects stale"):
            m.verify(controllers=changed)
        changed=copy.deepcopy(m.CONTROLLERS)
        changed[name]["runtime"].append("Host-allowed")
        with pytest.raises(ValueError,match="controller selects stale"):
            m.verify(controllers=changed)

@pytest.mark.parametrize("key",list(m.PINS))
def test_self_declared_generation_and_native_approval_never_pass(key):
    name="resident312-"+key
    state=load(name,"stages/final/integration.py")
    state["selected_generation_id"]="f"*64
    with pytest.raises(ValueError,match="fabricated native"):
        m.verify(overrides=change(name,"stages/final/integration.py",state))
    state=load(name,"stages/final/integration.py")
    state["toolchain_origin_proven"]=True
    with pytest.raises(ValueError,match="fabricated native"):
        m.verify(overrides=change(name,"stages/final/integration.py",state))

def test_no_premature_python315_repin():
    assert "setuptools-84.0.0" in load("python-setuptools","stages/final/sources.py")[0]["url"]
    assert load("python","stages/final/upstream.py")["version"]=="3.15.0rc2"

def test_selected_source_produces_explicit_dependency_acyclic_order():
    order=list(m.PINS)
    for ix,key in enumerate(order):
        assert all(order.index(n)<ix for n in m.PINS[key][3])
    assert m.CONTROLLERS["root-control"]["runtime"].index("box-control-final")>0

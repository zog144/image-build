"""Selected dual Python runtime and safe native missing-stage planning."""
import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("resident_b_runtime_split",
     ROOT / "tools/verify_resident_b_runtime_split.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
planner_spec = importlib.util.spec_from_file_location("resident_b_native_planner",
     ROOT / "tools/plan_resident_b_native_admission.py")
planner = importlib.util.module_from_spec(planner_spec)
planner_spec.loader.exec_module(planner)

def test_selected_abis_are_separate_and_not_native_proof():
    report = mod.verify()
    assert report["stage_count"] == 8
    assert report["stage_abi"]["root-control-final"] == "3.12"
    assert report["stage_abi"]["host-install-final"] == "3.15"
    assert report["host_default_interpreter"] == "/usr/bin/python3"
    assert not report["installed_shebang_elf_record_verified"]
    assert not report["native_build_or_activation_permitted"]

@pytest.mark.parametrize("stage,path", [
    ("host-install-final", "usr/lib/python3.12/site-packages/zog/host_install/__init__.py"),
    ("root-control-final", "usr/lib/python3.15/site-packages/zog/root_control/__init__.py"),
])
def test_no_cross_abi_sources_admitted(stage, path):
    manifests = {k: mod.read(k, "produce-manifest.py") for k in mod.SPECS}
    manifests[stage]["required"].append(path)
    with pytest.raises(ValueError, match="crossed selected Python ABI"):
        mod.verify(manifests=manifests)

def test_missing_python_extension_refused():
    manifests = {k: mod.read(k, "produce-manifest.py") for k in mod.SPECS}
    manifests["python-resident312-final"]["required"].remove(
        "usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so")
    with pytest.raises(ValueError, match="missing selected ABI output"):
        mod.verify(manifests=manifests)

def test_host_cannot_lose_python315_dependency():
    deps = {k: mod.read(k, "dependencies.py")
            for k in set(mod.HOST_DEPENDENCIES) | {"box-control-final", "root-control-final"}}
    deps["host-install-final"]["runtime"].clear()
    with pytest.raises(ValueError, match="host Python 3.15 dependency"):
        mod.verify(dependencies=deps)
    deps["host-install-final"]["runtime"] = ["python-final"]
    deps["root-control-final"]["runtime"] = ["python-final"]
    with pytest.raises(ValueError, match="controller Python 3.12"):
        mod.verify(dependencies=deps)

def test_only_missing_stages_are_scheduled_in_dependency_order():
    graph = {
        "host-tool": {"build": ["python315"], "runtime": ["python315"]},
        "controller": {"build": ["python312"], "runtime": ["python312"]},
        "python315": {"build": [], "runtime": []},
        "python312": {"build": [], "runtime": []},
    }
    decisions = {name: {"state": "present-exact-reviewed-receipt"}
                 for name in graph}
    decisions["python312"]["state"] = "missing-or-source-mismatch"
    decisions["host-tool"]["state"] = "missing-or-source-mismatch"
    order, revalidate = planner.missing_build_order(graph, decisions)
    assert order == ["host-tool", "python312"] or order == ["python312", "host-tool"]
    assert revalidate == ["controller"]
    decisions["python315"]["state"] = "missing-or-source-mismatch"
    order, revalidate = planner.missing_build_order(graph, decisions)
    assert order.index("python315") < order.index("host-tool")
    assert order.index("python312") < order.index("host-tool") or order == order
    assert "controller" in revalidate

def test_missing_stage_plan_refuses_dangling_or_cyclic_dependencies():
    decisions = {"a": {"state": "missing-or-source-mismatch"}}
    with pytest.raises(ValueError, match="unrecognized native build dependency"):
        planner.missing_build_order({"a": {"build": ["b"], "runtime": []}}, decisions)
    decisions["b"] = {"state": "missing-or-source-mismatch"}
    with pytest.raises(ValueError, match="cycle"):
        planner.missing_build_order({
            "a": {"build": ["b"], "runtime": []},
            "b": {"build": [], "runtime": ["a"]}}, decisions)

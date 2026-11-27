"""Fail-closed tests for selected Boot A input and transitive Resident B DAG."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/verify_resident_b_native_input_closure.py"
spec = importlib.util.spec_from_file_location("resident_b_input", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
DIGEST = "sha256:65a6101ed5079a6f23490deccd45f9104d58ae2709ddf4e507d9fbccd3c71ecc"


def selected():
    return json.loads(mod.SELECTION.read_text())


def test_real_source_selection_has_exact_predecessor_and_closed_29_stage_graph():
    report = mod.verify()
    assert report["native_input_generation"] == mod.GENERATION
    assert report["stage_count"] == 29
    assert report["closure_graph_sha256"] == DIGEST
    assert {"systemd-test-environment", "pyelftools-build",
            "python-resident312-final", "root-control-final",
            "box-control-final"} <= set(report["stages"])
    assert report["native_packages_verified"] is False
    assert report["compiler_authorized"] is False


@pytest.mark.parametrize("change", [
    lambda x: x["native_input"].update(generation="0"*64),
    lambda x: x["native_input"].update(producer_source_revision="f"*40),
    lambda x: x["native_input"].update(retained_parent_generation="a"*64),
    lambda x: x["native_input"].update(rejected_predecessor=mod.GENERATION),
    lambda x: x["native_input"]["source_plan"].update(reviewed_commit="e"*40),
    lambda x: x["native_input"].update(canonical_archive_sha256="f"*64),
    lambda x: x["native_input"].update(installed_package_receipt_sha256="1"*64),
    lambda x: x["native_input"].update(package_inventory_verified_against_predecessor=True),
    lambda x: x["native_input"].update(booted_resident_runtime_verified=True),
    lambda x: x["package_closure"].update(closure_stage_count=28),
    lambda x: x["package_closure"].update(closure_graph_sha256="sha256:"+"e"*64),
    lambda x: x["package_closure"].update(package_binary_closure_verified=True),
    lambda x: x["package_closure"].update(predecessor_package_receipts_verified=True),
    lambda x: x["package_closure"]["source_roots"].remove("root-control-final"),
    lambda x: x["package_closure"].update(source_graph_status="NATIVE_APPROVED"),
])
def test_unverified_boot_generation_or_dependency_substitution_is_rejected(change):
    source = copy.deepcopy(selected())
    change(source)
    with pytest.raises(ValueError, match="NOT READY"):
        mod.verify(selection=source)


def test_dependency_edge_deletion_changes_original_pinned_graph():
    def changed(stage):
        output = copy.deepcopy(mod.read_stage(stage))
        if stage == "systemd-final":
            output["build"].remove("pyelftools-build")
        return output
    with pytest.raises(ValueError, match="checksum/count"):
        mod.verify(reader=changed)


def test_unresolved_source_stage_and_cycles_fail_closed():
    def unknown(stage):
        edges = copy.deepcopy(mod.read_stage(stage))
        if stage == "systemd-final":
            edges["build"].append("not-a-real-package-final")
        return edges
    with pytest.raises(ValueError, match="definition missing"):
        mod.verify(reader=unknown)
    def cyclic(stage):
        edges = copy.deepcopy(mod.read_stage(stage))
        if stage == "pyelftools-build":
            edges["build"].append("systemd-final")
        return edges
    with pytest.raises(ValueError, match="cycle"):
        mod.verify(reader=cyclic)


def test_host_install_reviewed_generation_is_not_same_as_original_failed_boot():
    from pathlib import Path
    plan = ROOT / "companions/host-install-boot-a-successor" / mod.PLAN_PATH
    if not plan.is_file():
        pytest.skip("selected host-install checkout belongs to cross-repository CI")
    source = json.loads(plan.read_text())
    assert mod.check_original_plan(source)
    source["generation_binding"]["producer_source_revision"] = "0"*40
    with pytest.raises(ValueError, match="NOT READY"):
        mod.check_original_plan(source)
    source["generation_binding"]["producer_source_revision"] = mod.PRODUCER
    source["device_writes_authorized"] = True
    with pytest.raises(ValueError, match="NOT READY"):
        mod.check_original_plan(source)

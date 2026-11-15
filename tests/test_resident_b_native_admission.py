"""Fail-closed native-receipt selection and per-stage exact installed-output plan.

Source-only tests cannot replace the installed protected compiler-base signer;
the live adapter reuses compiler_base_acceptance.resolve in the native Host.
"""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/plan_resident_b_native_admission.py"
spec = importlib.util.spec_from_file_location("resident_b_admission", SCRIPT)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)

STATIC = ROOT / "tools/verify_resident_b_native_input_closure.py"
source_spec = importlib.util.spec_from_file_location("resident_b_admission_source", STATIC)
native = importlib.util.module_from_spec(source_spec)
source_spec.loader.exec_module(native)


def fresh():
    return json.loads(native.SELECTION.read_text())


def test_original_compiler_receipt_is_pinned_and_corrected_generation_remains_unknown():
    x = fresh()
    assert native.verify(selection=x)["stage_count"] == 29
    contract = x["native_admission"]
    assert contract["compiler"]["generation"].startswith("3805294f")
    assert contract["compiler"]["original_receipt_sha256"].startswith("sha256:a205c07b")
    assert contract["compiler"]["reader_source_blob_sha1"] == planner.COMPILER_READER_BLOB
    assert contract["corrected_predecessor"]["generation"] is None
    assert contract["corrected_predecessor"]["historical_generation"].startswith("273de2a0")
    assert contract["authority"]["native_build_permitted"] is False
    with pytest.raises(ValueError, match="unpublished/unselected"):
        planner.admit(selection=x, compiler_project="/does/not/exist",
                      predecessor_project="/does/not/exist",
                      authority_file="/does/not/exist",
                      controller="/does/not/exist", recipes_directory="/does/not/exist")


@pytest.mark.parametrize("change", [
    lambda a: a["compiler"].update(generation="0"*64),
    lambda a: a["compiler"].update(original_receipt_sha256="sha256:"+"f"*64),
    lambda a: a["compiler"].update(reader_source_blob_sha1="e"*40),
    lambda a: a["compiler"].update(project_id="made-up"),
    lambda a: a["compiler"].update(authenticated=True),
    lambda a: a["corrected_predecessor"].update(generation="f"*64),
    lambda a: a["corrected_predecessor"].update(accepted=True),
    lambda a: a["package_decisions"].update(present=["systemd-final"]),
    lambda a: a["package_decisions"].update(complete_native_closure=True),
    lambda a: a["authority"].update(native_build_permitted=True),
    lambda a: a.update(status="NATIVE_APPROVED"),
])
def test_receipt_and_native_boot_claim_substitutions_fail_closed(change):
    selected = fresh()
    change(selected["native_admission"])
    with pytest.raises(ValueError, match="NOT READY"):
        native.verify(selection=selected)


def test_future_corrected_generation_requires_all_explicit_source_pins_and_stays_hold():
    selected = fresh()
    evidence = selected["native_admission"]
    evidence["status"] = "CORRECTED_BOOT_A_SOURCE_SELECTED_READBACK_REQUIRED"
    p = evidence["corrected_predecessor"]
    p.update(generation="f"*64, source_revision="e"*40,
             canonical_manifest_sha256="sha256:"+"a"*64,
             canonical_archive_sha256="sha256:"+"b"*64,
             installed_package_receipts_sha256="sha256:"+"c"*64)
    assert native.verify(selection=selected)["compiler_authorized"] is False
    assert p["accepted"] is False
    p["canonical_archive_sha256"] = None
    with pytest.raises(ValueError, match="NOT READY"):
        native.verify(selection=selected)


def _package():
    return SimpleNamespace(
        fingerprint="reviewed-recipe-fingerprint",
        integration={"project": "stage", "stage_id": "final"},
        outputs=("usr/bin/program", "usr/lib/libnative.so"),
    )


def _receipt(outputs):
    return {
        "inputs": {"package": "reviewed-recipe-fingerprint"},
        "integration": {"project": "stage", "stage_id": "final"},
        "outputs": outputs,
        "provenance": {
            "output": "sha256:" + "e"*64,
            "result": "sha256:" + "f"*64,
        },
    }


def _files():
    return [
        {"path": "usr/bin/program", "kind": "file",
         "sha256": "a"*64, "mode": 0o755},
        {"path": "usr/lib/libnative.so", "kind": "file",
         "sha256": "b"*64, "mode": 0o644},
    ]


def test_exact_recipe_and_receipt_readback_can_reuse_predecessor_package():
    files = _files()
    result = planner.classify(
        {"stage-final": {"build": [], "runtime": []}},
        {"stage-final": _package()},
        [("accepted-original-compiler", {
            "root_outputs": files,
            "packages": {"stage-final": _receipt(files)},
        })],
    )
    assert result["stage-final"]["state"] == "present-exact-reviewed-receipt"
    assert result["stage-final"]["source"] == "accepted-original-compiler"


@pytest.mark.parametrize("alter", [
    lambda receipt, root: receipt["inputs"].update(package="substituted"),
    lambda receipt, root: receipt["integration"].update(stage_id="legacy"),
    lambda receipt, root: receipt["outputs"].pop(),
    lambda receipt, root: root[0].update(sha256="f"*64),
    lambda receipt, root: receipt.update(provenance={}),
])
def test_missing_recipe_or_output_receipt_never_becomes_present(alter):
    files = _files()
    receipt = _receipt(files)
    root = copy.deepcopy(files)
    alter(receipt, root)
    result = planner.classify(
        {"stage-final": {"build": [], "runtime": []}},
        {"stage-final": _package()},
        [("corrected-Boot-A", {
            "root_outputs": root,
            "packages": {"stage-final": receipt},
        })],
    )
    assert result["stage-final"]["state"] == "missing-or-source-mismatch"

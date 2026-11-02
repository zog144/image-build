"""Adversarial negative handoff validation, offline and source-only."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("handoff", ROOT/"tools/verify_workspace_native_handoff.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
original=json.loads((ROOT/"project/graphics-first-workspace/source-to-native-handoff.json").read_text())

def test_source_handoff_remains_non_submittable():
    assert mod.verify(original)

@pytest.mark.parametrize("key,mutation",[
    ("producer_order",["XCB","fonts","X11","LLVM","Mesa","Xvnc-i3-xterm","mesa-demos-smoke"]),
    ("producer_order",["fonts","XCB","LLVM","Mesa","Xvnc-i3-xterm","mesa-demos-smoke"]),
    ("source_revisions",{"workspace_pr9_reviewed_input":"fake","mesa_pr8":"fake"}),
    ("producer_edges",[["XCB","X11"]]),
    ("required_tool_provenance",{"meson-ninja-cmake-pkgconf":"Host defaults"}),
    ("native_readiness","READY"),
    ("rights_gate","APPROVED"),
    ("inherited_stages",["zlib-native-environment"]),
    ("expected_outputs",["usr/bin/Xvnc"]),
    ("build_submission_allowed",True),
    ("native_accepted",True),
])
def test_refuses_missing_predecessor_or_escalated_source_claim(key, mutation):
    altered=copy.deepcopy(original)
    altered[key]=mutation
    with pytest.raises(ValueError):
        mod.verify(altered)

@pytest.mark.parametrize("slot",mod.RECEIPTS)
def test_fabricated_generation_identifier_is_never_accepted(slot):
    altered=copy.deepcopy(original)
    altered["accepted_generation_receipts"][slot]="sha256:"+"a"*64
    with pytest.raises(ValueError,match="fabricated"):
        mod.verify(altered)

def test_actual_handoff_is_denied_native_readiness_without_authenticated_generations():
    with pytest.raises(ValueError,match="native-readiness DENIED: authentic protected generation receipts missing"):
        mod.refuse_native_readiness(original)


def test_even_well_formed_looking_sha_ids_cannot_be_trusted_from_source_ci():
    forged=copy.deepcopy(original)
    forged["accepted_generation_receipts"]={key:"sha256:"+("a"*64) for key in mod.RECEIPTS}
    with pytest.raises(ValueError,match="source CI cannot authenticate or authorize"):
        mod.refuse_native_readiness(forged)


def test_mesa_precedes_xvnc_and_smoke_occurs_last():
    order=original["producer_order"]
    assert order.index("X11") < order.index("Mesa") < order.index("Xvnc-i3-xterm")
    assert order.index("LLVM") < order.index("Mesa")
    assert order[-1]=="mesa-demos-smoke"

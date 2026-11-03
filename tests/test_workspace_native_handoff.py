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

@pytest.mark.parametrize("injected",[
    ("native_ready",True), ("accepted_generation_id","a"*64),
    ("approval_receipt",{"issuer":"forged","verified":True}),
    ("signed",True), ("submission_authorized",True),
])
def test_unrecognized_authority_or_success_field_rejected(injected):
    record=copy.deepcopy(original)
    key,value=injected
    record[key]=value
    with pytest.raises(ValueError,match="unrecognized source handoff field"):
        mod.verify(record)


@pytest.mark.parametrize("stage,missing",[
    ("turbovnc","mesa-final"), ("turbovnc","xkbcomp-final"),
    ("turbovnc","zlib-native-environment"),
    ("i3","libxkbcommon-final"), ("xterm","ncurses-temporary"),
    ("xterm","basic-font-final"),
])
def test_independent_stage_source_dependency_omission(stage,missing):
    deps=__import__("ast").literal_eval((mod.STAGE_PATHS[stage]/"dependencies.py").read_text())
    replaced={key:[x for x in values if x!=missing] for key,values in deps.items()}
    with pytest.raises(ValueError,match="missing actual package predecessor"):
        mod.review_local_stage_closure(original,dependency_overrides={stage:replaced})


def test_actual_stage_manifest_cannot_be_missing_from_handoff():
    record=copy.deepcopy(original)
    record["expected_outputs"].remove("usr/share/licenses/xkbcomp/COPYING")
    with pytest.raises(ValueError,match="handoff omits actual package output"):
        mod.verify(record)


@pytest.mark.parametrize("pkg",["i3","turbovnc","xterm","basic-font","xkbcomp"])
def test_missing_selected_package_is_rejected(pkg):
    record=copy.deepcopy(original)
    record["source_packages"]["desktop"].remove(pkg)
    with pytest.raises(ValueError,match="missing or duplicate selected source package"):
        mod.verify(record)


def test_duplicate_stage_entry_and_fake_tool_origin_rejected():
    record=copy.deepcopy(original)
    record["source_packages"]["desktop"].append("xkbcomp")
    with pytest.raises(ValueError,match="duplicate selected source package"):
        mod.verify(record)
    record=copy.deepcopy(original)
    record["required_tool_provenance"]["build-utilities"]="Host defaults"
    with pytest.raises(ValueError,match="unreviewed host tool provenance"):
        mod.verify(record)


def test_forged_receipt_object_not_accepted_even_with_authentic_looking_fields():
    record=copy.deepcopy(original)
    record["accepted_generation_receipts"]["X11"]={
        "generation":"a"*64,"issuer":"zog","verified":True,"signature":"b"*128}
    with pytest.raises(ValueError,match="fabricated or unauthenticated"):
        mod.verify(record)
    with pytest.raises(ValueError,match="native-readiness DENIED"):
        mod.refuse_native_readiness(record)

@pytest.mark.parametrize("stage,expected",[
    ("i3","usr/bin/i3"), ("xterm","usr/share/terminfo/x/xterm"),
    ("turbovnc","usr/share/licenses/turbovnc/Xserver-COPYING"),
    ("basic-font","usr/share/fonts/X11/misc/fonts.dir"),
    ("xkbcomp","usr/bin/xkbcomp"),
    ("xkeyboard-config","usr/share/X11/xkb"),
])
def test_producer_cannot_remove_manifest_output_even_if_handoff_mentions_it(stage,expected):
    import ast
    manifest=ast.literal_eval((mod.STAGE_PATHS[stage]/"produce-manifest.py").read_text())
    altered={**manifest,"required":[x for x in manifest["required"] if x!=expected]}
    with pytest.raises(ValueError,match="actual stage manifest omits reviewed"):
        mod.review_local_stage_closure(original,manifest_overrides={stage:altered})

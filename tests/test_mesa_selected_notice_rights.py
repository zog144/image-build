"""Source-level selected-feature rights delivery assertions, not native approval.

Independent of the eight-sidecar consistency verifier. All evidence read here
is original source metadata, *not* bytes installed on a compiler Host.
"""
import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]/"project/graphics-drafts"
SIX=("llvm","mesa","libdrm","libxshmfence","libXxf86vm","mesa-demos")


def original_records():
    rights=json.loads((ROOT/"rights-admission-evidence.json").read_text())
    licenses={name:ast.literal_eval((ROOT/name/"license.py").read_text()) for name in SIX}
    builds={name:ast.literal_eval((ROOT/name/"stages/final/build.py").read_text()) for name in SIX}
    manifests={name:ast.literal_eval((ROOT/name/"stages/final/produce-manifest.py").read_text()) for name in SIX}
    return rights, licenses, builds, manifests


def verify_holds(rights, licenses, builds, manifests):
    if rights.get("status")!="independent-rights-and-native-output-NO-GO":
        raise ValueError("unapproved selected rights promotion")
    if set(rights.get("components",{}))!=set(SIX):
        raise ValueError("rights audit omits a graphics component")
    for name in SIX:
        item=rights["components"][name]
        license_record=licenses[name]
        if license_record["status"]!="unresolved":
            raise ValueError("unauthorized license status upgrade: "+name)
        if item.get("installed_outputs_observed") is not False or item.get("notice_delivery_verified") is not False:
            raise ValueError("source metadata cannot assert observed native installed bytes")
        if item.get("actual_compile_commands_status")!="not received":
            raise ValueError("source metadata cannot assert genuine compiler evidence")
        if item.get("delivery_plan_status")!="source-authored-but-not-native-observed":
            raise ValueError("source notice plan cannot assert physical installation")
        if not item["outstanding"] or not item["original_member_delivery_plan"]:
            raise ValueError("missing rights blockers and notice delivery plan")
        original={p["path"]:p["sha256"] for p in license_record["evidence"]}
        source_sha=license_record["source"]["sha256"]
        if any(p["source_sha256"]!=source_sha for p in license_record["evidence"]):
            raise ValueError("license notice member not bound to selected archive")
        script="\n".join(row[-1] for row in builds[name]["install"])
        expected=set(manifests[name]["required"])
        declared = {plan["installed_path"] for plan in item["original_member_delivery_plan"]}
        notice_outputs = {p for p in item["expected_output_paths"]
                          if p.startswith("usr/share/licenses/" + name + "/")}
        if declared != notice_outputs:
            raise ValueError("original notice delivery plan omits a selected output")
        for plan in item["original_member_delivery_plan"]:
            src,dst=plan["original_member"],plan["installed_path"]
            if src not in original:
                raise ValueError("notice source not in original verified license evidence")
            if dst not in expected:
                raise ValueError("planned delivered notice absent from installed-output contract")
            if src not in script or dst not in script:
                raise ValueError("notice source/destination not represented by authored install command")
            if plan["status"]!="draft install command only; actual byte and rights verification required":
                raise ValueError("draft notice cannot claim verified installed bytes")
        for candidate in item["original_scoped_source_candidates"]:
            if candidate["selected_native_compilation"]!="unobserved":
                raise ValueError("original source hash is not a native selected object witness")
    return True


def test_six_selected_original_notice_plans_are_source_consistent_but_held():
    assert verify_holds(*original_records())


@pytest.mark.parametrize("mutation",[
    "fake_installed","fake_compiled","fake_license","missing_notice","changed_notice",
    "missing_expected_output","unbound_archive","invented_delivery","missing_component",
])
def test_source_notice_evidence_forgery_fails_closed(mutation):
    rights,licenses,builds,manifests=deepcopy(original_records())
    item=rights["components"]["mesa"]
    if mutation=="fake_installed":item["notice_delivery_verified"]=True
    elif mutation=="fake_compiled":item["actual_compile_commands_status"]="captured"
    elif mutation=="fake_license":licenses["mesa"]["status"]="reviewed"
    elif mutation=="missing_notice":item["original_member_delivery_plan"].pop()
    elif mutation=="changed_notice":item["original_member_delivery_plan"][0]["original_member"]="mesa-25.3.0/UNVERIFIED-LICENSE"
    elif mutation=="missing_expected_output":
        manifests["mesa"]["required"].remove(item["original_member_delivery_plan"][0]["installed_path"])
    elif mutation=="unbound_archive":licenses["mesa"]["evidence"][0]["source_sha256"]="0"*64
    elif mutation=="invented_delivery":item["original_member_delivery_plan"][0]["status"]="actual notice bytes verified"
    elif mutation=="missing_component":del rights["components"]["mesa"]
    with pytest.raises(ValueError):
        verify_holds(rights,licenses,builds,manifests)

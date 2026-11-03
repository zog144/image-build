#!/usr/bin/env python3
"""Exact source-only remaining graphics rights evidence; no archive download."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SUP=ROOT/"project/graphics-first-workspace/remaining-distribution-evidence-2026-11-03.json"
BASE=ROOT/"project/graphics-first-workspace/selected-component-rights-handoff.json"
REVIEWED="6b64a7e1b6f9842554bd3b9eee5599e24ca2402c"
MESA="9cbd652226b863a7b4bb2d6d9539722e1a262508"
COMPONENTS={"turbovnc-xserver","turbovnc-libsha1","turbovnc-zlib-ng-excluded",
"llvm-generated-blake3","mesa-glapi-generated","mesa-llvmpipe","libdrm-common",
"mesa-demos-glxgears","mesa-demos-glxinfo"}
FIELDS={"schema","reviewed_workspace_source","reviewed_mesa_source","base_matrix_path",
"scope","installed_generation_receipt","actual_native_compile_map",
"independent_copyright_holder_approval","redistribution_authorized",
"components","required_independent_reviewer_evidence","review_status"}
ROW={"id","package","original_member","original_member_sha256","source_archive_sha256",
"original_member_role","planned_notice_output_paths","generated_attribution_questions",
"native_inclusion_exclusion_questions","native_outputs_to_reconcile",
"negative_evidence_cases","compiled_inclusion_evidence","installed_notice_sha256_evidence",
"rights_decision"}
def fail(reason):
    raise ValueError("graphics distribution source-review NO-GO: "+reason)
def verify(supplement=None,base=None):
    supplement=supplement if supplement is not None else json.loads(SUP.read_text())
    base=base if base is not None else json.loads(BASE.read_text())
    if (type(supplement) is not dict or set(supplement)!=FIELDS or
        supplement["schema"]!="zog-graphics-unresolved-distribution-evidence-v1" or
        supplement["reviewed_workspace_source"]!=REVIEWED or
        supplement["reviewed_mesa_source"]!=MESA or
        supplement["base_matrix_path"]!="project/graphics-first-workspace/selected-component-rights-handoff.json" or
        supplement["review_status"]!="SOURCE_GAPS_EXPLICIT_NATIVE_RIGHTS_NO_GO"):
        fail("unknown source scope or revised exact PR heads")
    for field in ("installed_generation_receipt","actual_native_compile_map"):
        if supplement[field] is not None:
            fail("source review invents native generation/compile evidence")
    if (supplement["independent_copyright_holder_approval"] is not False or
        supplement["redistribution_authorized"] is not False or
        base.get("independent_redistribution_approved") is not False or
        base.get("native_compiled_selection_observed") is not False):
        fail("source evidence cannot grant native or rights authority")
    rows=supplement["components"]
    if (type(rows) is not list or len(rows)!=len(COMPONENTS) or
        {r.get("id") for r in rows}!=COMPONENTS):
        fail("missing, duplicated or unreviewed original-source component")
    byid={r["id"]:r for r in base["components"]}
    if set(byid)!=COMPONENTS:
        fail("base source notice inventory changed")
    for row in rows:
        if type(row) is not dict or set(row)!=ROW:
            fail("component evidence field altered: "+str(row.get("id")))
        original=byid[row["id"]]
        actual=(row["package"],row["original_member"],row["original_member_sha256"],
            row["source_archive_sha256"],row["original_member_role"],
            row["planned_notice_output_paths"])
        expected=(original["package"],original["member"],original["member_sha256"],
            original["source_sha256"],original["member_role"],
            original["planned_notice_output_paths"])
        if actual!=expected:
            fail("original source member or notice-output identity diverges: "+row["id"])
        if (row["compiled_inclusion_evidence"] is not None or
            row["installed_notice_sha256_evidence"] is not None or
            row["rights_decision"]!="HOLD_ORIGINAL_NOTICE_NOT_AUTHORITY"):
            fail("native or redistribution approval falsely asserted: "+row["id"])
        for key in ("generated_attribution_questions","native_inclusion_exclusion_questions",
                    "native_outputs_to_reconcile","negative_evidence_cases"):
            values=row.get(key)
            if type(values) is not list or not values or any(type(v) is not str or len(v)<10
                                                            for v in values):
                fail("missing selected generated-code/inclusion/notice obligation: "+row["id"])
        if row["id"]=="turbovnc-zlib-ng-excluded" and row["planned_notice_output_paths"]:
            fail("excluded original archive presence is not installed notice proof")
        if row["id"].startswith("mesa-demos") and not any(
            "copyright" in v.lower() or "public-domain" in v.lower()
            for v in row["native_inclusion_exclusion_questions"]):
            fail("mesa-demos missing per-file attribution decision")
        if row["id"]=="mesa-glapi-generated" and not any(
            "generator" in v.lower() and "templates" in v.lower()
            for v in row["generated_attribution_questions"]):
            fail("Mesa GLAPI input/template generation omitted")
        if row["id"]=="llvm-generated-blake3" and not any(
            "tblgen" in v.lower() for v in row["generated_attribution_questions"]):
            fail("LLVM TableGen generated-code mapping omitted")
        if row["id"]=="turbovnc-xserver" and not any(
            "dri3" in v.lower() and "device" in v.lower()
            for v in row["native_inclusion_exclusion_questions"]):
            fail("Xserver excluded device feature proof omitted")
    obligations=supplement["required_independent_reviewer_evidence"]
    if (type(obligations) is not list or len(obligations)!=5 or
        not any("notice" in v.lower() for v in obligations) or
        not any("copyright" in v.lower() for v in obligations)):
        fail("independent native and rights obligations truncated")
    return {"source_gap_inventory":"CONSISTENT","native_compiled_selection":"UNOBSERVED",
            "installed_notice_bytes":"UNOBSERVED","redistribution":"NOT_AUTHORIZED",
            "component_count":len(rows)}
if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))

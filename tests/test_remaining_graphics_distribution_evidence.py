"""Targeted graphics original-source rights omission tests; no archive downloads."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("graphics_rights_pending",
    ROOT/"tools/verify_remaining_graphics_rights.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
record=json.loads(mod.SUP.read_text())
base=json.loads(mod.BASE.read_text())

def test_current_component_questions_explicitly_remain_unverified():
    status=mod.verify()
    assert status["source_gap_inventory"]=="CONSISTENT"
    assert status["component_count"]==9
    assert status["redistribution"]=="NOT_AUTHORIZED"
    assert status["native_compiled_selection"]=="UNOBSERVED"

@pytest.mark.parametrize("id,field",[
    ("turbovnc-xserver","generated_attribution_questions"),
    ("turbovnc-libsha1","native_inclusion_exclusion_questions"),
    ("turbovnc-zlib-ng-excluded","native_inclusion_exclusion_questions"),
    ("llvm-generated-blake3","generated_attribution_questions"),
    ("mesa-glapi-generated","generated_attribution_questions"),
    ("mesa-llvmpipe","native_outputs_to_reconcile"),
    ("libdrm-common","negative_evidence_cases"),
    ("mesa-demos-glxgears","native_inclusion_exclusion_questions"),
    ("mesa-demos-glxinfo","negative_evidence_cases"),
])
def test_required_component_evidence_question_cannot_be_erased(id,field):
    mutated=copy.deepcopy(record)
    next(r for r in mutated["components"] if r["id"]==id)[field]=[]
    with pytest.raises(ValueError,match="missing selected"):
        mod.verify(mutated)

def test_missing_llvm_tblgen_or_glapi_generator_provenance_refused():
    for id in ("llvm-generated-blake3","mesa-glapi-generated"):
        mutated=copy.deepcopy(record)
        row=next(r for r in mutated["components"] if r["id"]==id)
        row["generated_attribution_questions"]=["Some generated code exists but attribution is unknown"]
        with pytest.raises(ValueError,match="generated-code mapping|GLAPI input"):
            mod.verify(mutated)

def test_device_exclusion_cannot_be_inferred_from_turbovnc_cmake_option():
    altered=copy.deepcopy(record)
    row=next(r for r in altered["components"] if r["id"]=="turbovnc-xserver")
    row["native_inclusion_exclusion_questions"]=["TVNC_DRI3=OFF was declared in source settings"]
    with pytest.raises(ValueError,match="excluded device feature"):
        mod.verify(altered)

@pytest.mark.parametrize("id",["mesa-demos-glxgears","mesa-demos-glxinfo"])
def test_mesa_demo_file_copy_is_not_copyright_holder_authorization(id):
    altered=copy.deepcopy(record)
    row=next(r for r in altered["components"] if r["id"]==id)
    row["native_inclusion_exclusion_questions"]=["Only source files copied to licences directory"]
    with pytest.raises(ValueError,match="per-file attribution"):
        mod.verify(altered)

@pytest.mark.parametrize("change",["redistribution","native_generation","native_compilation",
                                   "notice_delivered","altered_source_hash","altered_notice_path",
                                   "hidden_approval"])
def test_source_matrix_rejects_fabricated_native_or_rights_claims(change):
    altered=copy.deepcopy(record)
    row=altered["components"][0]
    if change=="redistribution":altered["independent_copyright_holder_approval"]=True
    if change=="native_generation":altered["installed_generation_receipt"]={"sha256":"a"*64,"verified":True}
    if change=="native_compilation":row["compiled_inclusion_evidence"]={"compiled":True}
    if change=="notice_delivered":row["installed_notice_sha256_evidence"]={"sha256":"b"*64}
    if change=="altered_source_hash":row["source_archive_sha256"]="c"*64
    if change=="altered_notice_path":row["planned_notice_output_paths"]=["usr/share/licenses/other"]
    if change=="hidden_approval":row["approved"]=True
    with pytest.raises(ValueError,match="NO-GO"):
        mod.verify(altered)

def test_unreported_original_member_rejected():
    changed=copy.deepcopy(record)
    changed["components"].pop()
    with pytest.raises(ValueError,match="missing, duplicated"):
        mod.verify(changed)

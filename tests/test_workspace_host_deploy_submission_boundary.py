"""Synthetic source-only denial against frozen host-deploy typed submission."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("source_submit",
    ROOT/"tools/verify_host_deploy_submission_audit.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
AUDIT=json.loads(mod.AUDIT.read_text())
HANDOFF=json.loads(mod.HANDOFF.read_text())

def proposal(**overrides):
    return {
        "task":mod.TASKS[2],
        "source_revision":mod.SELECTED_SOURCE,
        "mesa_source":mod.MESA,
        "accepted_x11":True,
        "checkpoint_protected_verified":True,
        **overrides,
    }

def test_actual_frozen_contract_remains_non_submittable():
    assert mod.review_contract(AUDIT,HANDOFF)
    assert AUDIT["host_deploy_selected_image_source"] != AUDIT["image_build_reviewed_source"]
    with pytest.raises(ValueError,match="submission DENIED"):
        mod.refuse_submission(HANDOFF,AUDIT,proposal())

@pytest.mark.parametrize("candidate,required_blocker",[
    ({"accepted_x11":False},"x11-accepted-generation-missing"),
    ({"accepted_x11":{"generation_id":"a"*64,"accepted":True,
                      "issuer":"forged"}},"protected-native-admission-not-available"),
    ({"source_revision":"b"*40},"task-source-revision-mismatch"),
    ({"mesa_source":"c"*40},"mesa-source-pin-mismatch"),
    ({"task":"mesa-final"},"task-not-in-protected-host-deploy-allowlist"),
    ({"task":"turbovnc-final"},"task-not-in-protected-host-deploy-allowlist"),
    ({"checkpoint_protected_verified":False},"independent-checkpoint-unverified"),
    ({"checkpoint_protected_verified":{"signed":True,"epoch":2}},
     "protected-native-admission-not-available"),
])
def test_synthetic_unaccepted_predecessor_stale_source_or_unsupported_task(candidate,required_blocker):
    reasons=mod.synthetic_blockers(HANDOFF,AUDIT,proposal(**candidate))
    assert required_blocker in reasons
    with pytest.raises(ValueError,match="DENIED"):
        mod.refuse_submission(HANDOFF,AUDIT,proposal(**candidate))

def test_real_prepared_plan_always_denied_even_with_plausible_receipts():
    altered=copy.deepcopy(HANDOFF)
    for stage in altered["accepted_generation_receipts"]:
        altered["accepted_generation_receipts"][stage]={
            "generation_id":"a"*64, "receipt_sha256":"sha256:"+"b"*64,
            "issuer":"host", "signature":"c"*128, "accepted":True,
        }
    with pytest.raises(ValueError,match="forged"):
        mod.review_contract(AUDIT,altered)
    with pytest.raises(ValueError,match="DENIED"):
        mod.refuse_submission(altered,AUDIT,proposal())

def test_handoff_cannot_flip_prepared_status_or_build_submit_flag():
    for key,value in (("status","READY"),("build_submission_allowed",True),
                      ("native_accepted",True),("rights_authorized",True)):
        altered=copy.deepcopy(HANDOFF)
        altered[key]=value
        with pytest.raises(ValueError,match="prematurely admitted"):
            mod.review_contract(AUDIT,altered)

@pytest.mark.parametrize("field,replacement",[
    ("host_deploy_selected_image_source","f"*40),
    ("mesa_source","0"*40),
    ("reviewed_graphical_tasks",["graphics-fonts-image-v1","mesa-final"]),
    ("native_receipts_observed",True),
    ("authorized_submission_test_allowed",True),
    ("host_install_current_authority_observed",True),
])
def test_source_audit_cannot_repin_or_claim_protected_authority(field,replacement):
    altered=copy.deepcopy(AUDIT)
    altered[field]=replacement
    with pytest.raises(ValueError):
        mod.review_contract(altered,HANDOFF)

def test_fake_immutable_host_source_bytes_cannot_pass_the_blob_gate():
    with pytest.raises(ValueError,match="immutable source blob changed"):
        mod.verify_pinned_host_deploy_source(AUDIT,
            fetch=lambda path, revision:b"# plausible host-deploy source\n")

def test_no_remote_or_host_call_in_normal_source_gate(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("offline source inspection must never fetch or submit")
    monkeypatch.setattr(mod,"_remote_source",forbidden)
    assert mod.review_contract(AUDIT,HANDOFF)
    assert "protected-native-admission-not-available-to-source-ci" in (
        mod.synthetic_blockers(HANDOFF,AUDIT,proposal()))

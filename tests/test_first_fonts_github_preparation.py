"""Offline Fonts source/request preparation synthetic refusal tests (no AWS)."""
import copy
import importlib.util
import json
import os
import shutil
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("zog_fonts_prep",ROOT/"tools/verify_first_fonts_github_preparation.py")
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)

def check(obj=None, *, fonts_host=None, signed_reader=None, compiler_consumer=None):
    return m.verify(m.load() if obj is None else obj,
        os.environ["ZOG_HOSTDEPLOY_FONTS_PR7"] if fonts_host is None else fonts_host,
        os.environ["ZOG_HOSTDEPLOY_TASKC_PR26"],
        os.environ["ZOG_IMAGE_BUILD_SELECTED_SOURCE"],
        os.environ["ZOG_IMAGE_BUILD_SIGNED_READER"] if signed_reader is None else signed_reader,
        os.environ["ZOG_HOSTDEPLOY_COMPILER_CONSUMER_PR29"] if compiler_consumer is None else compiler_consumer)

def test_exact_source_and_request_shape_only_never_compiler_admission():
    value=check()
    assert value["source_contract"]=="EXACT_FONTS_PLAN_AND_ORIGINAL_PIN"
    assert value["submission"]=="PREPARED_NOT_SUBMITTABLE"
    assert value["gateway_protocol"]=="SYNTHETIC_SHAPE_ONLY"
    assert value["accepted_generation"] is None
    assert value["native_evidence"] is None

@pytest.mark.parametrize("part,key,value",[
 ("producer","source_revision","b0f53dbdec0e88b9b37feb5317398db3d20507dd"),
 ("reviewer","compiler_base_reader_revision","0"*40),
 ("producer","monthly_pin_sha256","sha256:"+"f"*64),
 ("reviewer","host_deploy_fonts_catalogue_revision","f"*40),
 ("reviewer","host_deploy_task_c_revision","f"*40),
 ("gateway","source_commit","b0f53dbdec0e88b9b37feb5317398db3d20507dd"),
 ("gateway","operation","toolchain.submit"),
 ("gateway","event","workflow_dispatch"),
 ("gateway","request_id","f"*32),
 ("gateway","workspace_id","f"*32),
 ("gateway","issue_number",42),
 ("gateway","actor","signed-actor"),
 ("gateway","request_sha256","sha256:"+"f"*64),
 ("gateway","queue_receipt",{"MessageId":"fake"}),
 ("gateway","dispatcher_selected_revision","f"*40),
 ("gateway","admin_operation_opt_in",True),
 ("task_catalogue","selected_base_generation","e"*64),
 ("task_catalogue","installed_catalogue_sha256","sha256:"+"f"*64),
 ("task_catalogue","selected_managed_lane","my-real-lane"),
 ("task_catalogue","only_task","graphics-xcb-core-image-v1"),
 ("task_catalogue","targets",["libpng-final","fontconfig-final","freetype-final"]),
 ("task_catalogue","arguments_mode","bootstrap"),
 ("output_evidence","output_generation_id","f"*64),
 ("output_evidence","pipeline_id","f"*32),
 ("output_evidence","acceptance_receipt_sha256","sha256:"+"f"*64),
 ("output_evidence","actual_immutable_generation_verified",True),
 ("submission","enabled",True),
 ("submission","auto_retry",True),
 ("submission","manual_direct_ssm_allowed",True),
 ("submission","github_issue_created",True),
 ("submission","submitted_sqs_message",True),
 ("submission","acceptance_claimed",True),
 ("budget","work_bytes",31*1024**3),
 ("budget","execution_limit_seconds",21601)
])
def test_fabricated_request_identity_authority_or_wider_budget_rejected(part,key,value):
    x=copy.deepcopy(m.load())
    x[part][key]=value
    with pytest.raises(m.FontsNotAdmitted,match="PREPARED_NOT_SUBMITTABLE"):
        check(x)

@pytest.mark.parametrize("gate",m.GATE_KEYS)
def test_no_claim_can_turn_source_only_native_gate_true(gate):
    x=copy.deepcopy(m.load())
    x["native_gates"][gate]={
        "signature":"looks-valid",
        "generation_id":"f"*64,
        "status":"accepted"
    }
    with pytest.raises(m.FontsNotAdmitted,match="native owner admission"):
        check(x)

def test_no_original_github_request_issue_envelope_in_repository():
    raw=m.RECORD.read_text()
    assert "<!-- zog-gateway-request:v1 -->" not in raw
    assert '"request_id": null' in raw
    assert '"workspace_id": null' in raw
    assert '"issue_number": null' in raw
    assert json.loads(raw)["submission"]["enabled"] is False

def test_real_selected_plan_and_catalogue_immutable_reviewed_sources():
    x=check()
    assert x["task"]=="graphics-fonts-image-v1"
    assert m.SOURCE=="1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
    assert m.TARGETS==("libpng-final","freetype-final","fontconfig-final")

def test_source_program_does_not_import_network_or_create_remote_tasks():
    source=(ROOT/"tools/verify_first_fonts_github_preparation.py").read_text()
    for denied in ("import boto3","import botocore","requests.post(",
                   "send_message(","send_command(","SendCommand(",
                   "create_issue(","subprocess.run("):
        assert denied not in source


def test_signed_compiler_base_kind_is_not_invented_by_offline_review():
    data=check()
    assert data["native_evidence"] is None
    assert data["accepted_generation"] is None
    assert m.load()["native_gates"]["accepted_signed_compiler_base_generation"] is None
    assert m.load()["reviewer"]["compiler_base_reader_revision"]==m.READER
    assert m.load()["reviewer"]["host_deploy_compiler_consumer_revision"]==m.HOST_CONSUMER
    assert m.load()["reviewer"]["host_deploy_fonts_catalogue_revision"]==m.HOST_FONTS
    assert m.load()["reviewer"]["host_deploy_task_c_revision"]==m.HOST_TASK_C

def test_exact_current_reader_catalogue_and_consumer_are_not_prior_versions():
    assert m.READER=="1616f192ef9d8964a8f37f32a86c69c0242a213c"
    assert m.HOST_FONTS=="c69e752033107ffe9e76d2506af446801964ea3d"
    assert m.HOST_CONSUMER=="b3ac93cd92df1b280f087fbb748263d3371750aa"
    assert m.SOURCE=="1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
    assert m.PIN=="sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36"
    assert m.load()["task_catalogue"]["selected_base_generation"] is None


@pytest.mark.parametrize("key,old_value", [
  ("host_deploy_fonts_catalogue_revision","745cb7e887fabcea06caf1d7db732b33f9dadca0"),
  ("compiler_base_reader_revision","bf0b37fea1767bf7ab02ca2d1c5d1a0d5487d4b6"),
  ("host_deploy_compiler_consumer_revision","745cb7e887fabcea06caf1d7db732b33f9dadca0"),
])
def test_previous_source_heads_do_not_reenter_frozen_preparation(key,old_value):
    record=copy.deepcopy(m.load())
    record["reviewer"][key]=old_value
    with pytest.raises(m.FontsNotAdmitted,match="source review head changed"):
        check(record)


def _partial_copy(source,destination,paths):
    for relative in paths:
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/relative,target)
    return destination


def test_legacy_signed_looking_isolation_reader_is_denied(tmp_path):
    source=Path(os.environ["ZOG_IMAGE_BUILD_SIGNED_READER"])
    path=Path("src/zog/image_build/compiler_base_isolation.py")
    candidate=_partial_copy(source,tmp_path/"old-reader",[
       Path("src/zog/image_build/compiler_base_acceptance.py"),path])
    original=(candidate/path).read_text()
    assert "selected-root-kernel-mounts-v1" in original
    (candidate/path).write_text(original.replace(
       "selected-root-kernel-mounts-v1","legacy-no-host-mounts-v1"))
    with pytest.raises(m.FontsNotAdmitted,match="actual mount/worker isolation"):
        check(signed_reader=candidate)


@pytest.mark.parametrize("substitution",["isolation_profile","witness_requirement","source_abi"])
def test_updated_pr7_consumer_requires_exact_reviewed_pr29_bytes(tmp_path,substitution):
    source=Path(os.environ["ZOG_HOSTDEPLOY_FONTS_PR7"])
    paths=[
        Path("src/zog/host_deploy/gateway/graphics_catalogue_owner.py"),
        Path("src/zog/host_deploy/gateway/graphics_base_acceptance.py"),
    ]
    candidate=_partial_copy(source,tmp_path/"drifted-catalogue",paths)
    target=candidate/paths[1]
    text=target.read_text()
    assert '"selected-root-kernel-mounts-v1"' in text
    if substitution=="isolation_profile":
        text=text.replace('"selected-root-kernel-mounts-v1"',
                          '"legacy-no-host-mounts-v1"')
    elif substitution=="witness_requirement":
        text=text.replace('not match(probe["isolation"].get("witness_sha256"),SHA)',
                          "False")
    else:
        text=text.replace('"x86_64-zog-linux-gnu"','"aarch64-linux-gnu"')
    target.write_text(text)
    with pytest.raises(m.FontsNotAdmitted,match="differs from reviewed PR29"):
        check(fonts_host=candidate)


def test_current_catalogue_owner_cannot_select_old_reader(tmp_path):
    source=Path(os.environ["ZOG_HOSTDEPLOY_FONTS_PR7"])
    paths=[
        Path("src/zog/host_deploy/gateway/graphics_catalogue_owner.py"),
        Path("src/zog/host_deploy/gateway/graphics_base_acceptance.py"),
    ]
    candidate=_partial_copy(source,tmp_path/"stale-owner",paths)
    owner=candidate/paths[0]
    owner.write_text(owner.read_text().replace(m.READER,
                                "bf0b37fea1767bf7ab02ca2d1c5d1a0d5487d4b6"))
    with pytest.raises(m.FontsNotAdmitted,match="differs from reviewed PR29"):
        check(fonts_host=candidate)


def test_unselected_consumer_or_source_missing_denied():
    with pytest.raises(m.FontsNotAdmitted,match="consumer source is absent"):
        m.verify(m.load(),os.environ["ZOG_HOSTDEPLOY_FONTS_PR7"],
                 os.environ["ZOG_HOSTDEPLOY_TASKC_PR26"],
                 os.environ["ZOG_IMAGE_BUILD_SELECTED_SOURCE"],
                 os.environ["ZOG_IMAGE_BUILD_SIGNED_READER"],None)

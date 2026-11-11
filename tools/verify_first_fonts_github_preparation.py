"""Offline, read-only FIRST Fonts GitHub-trigger source preparation.

This module deliberately NEVER writes an executable issue envelope, opens an
issue, requests AWS credentials, invokes SQS/SSM or converts source-only
review data to installed owner authority. All authentic native evidence
slots must remain absent until a separately approved Work handoff.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECORD=ROOT/"project/graphics-first-workspace/first-fonts-github-preparation-v1.json"
TASK="graphics-fonts-image-v1"
SOURCE="1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
PIN="sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36"
HOST_FONTS="ee4a3d58077fac8a578e1c4f96540e1999a9d1ba"
OWNER_GIT_BLOB="b2148a30bc1a7b074468e463cb9fab1e9abe4ce1"
HOST_CONSUMER="b3ac93cd92df1b280f087fbb748263d3371750aa"
READER="1616f192ef9d8964a8f37f32a86c69c0242a213c"
HOST_TASK_C="0fd2db17698423d4cd30b296fc9f78e83cee145c"
ENTRIES=(
    ("fontconfig-final","fontconfig","fontconfig/stages/final"),
    ("freetype-final","freetype","freetype/stages/final"),
    ("libpng-final","libpng","libpng/stages/final"),
)
TARGETS=("libpng-final","freetype-final","fontconfig-final")
GATE_KEYS=(
    "trusted_host_original_request_administrator_authorization","accepted_signed_compiler_base_generation",
    "canonical_base_generation_receipt","real_managed_lane_and_host_installation",
    "protected_one_task_catalogue_and_receipt",
    "root_backed_30_plus_2_gib_kernel_quota_admission",
    "six_hour_cpu_and_persistent_write_budget",
    "authenticated_original_snapshot_and_ssm_result",
    "installed_single_trusted_host_gateway",
    "durable_local_send_once_intent_reboot_recovery",
    "trusted_host_instance_iam_and_fifo_dispatcher",
    "authenticated_native_source_and_producer_reader",
    "selected_compiler_purpose_issuer_and_revocation",
    "one_attempt_and_uncertain_ack_reconciliation",
)
OUTPUT_NULLS=(
    "pipeline_id","original_request_id","recipe_snapshot","input_generation_id",
    "output_generation_id","generation_manifest_sha256",
    "acceptance_receipt_sha256","producer_receipt_sha256",
    "installed_verification_execution","build_record_root","trace_provenance",
)

class FontsNotAdmitted(ValueError):pass
def deny(why):
    raise FontsNotAdmitted("Fonts GitHub source PREPARED_NOT_SUBMITTABLE: "+why)
def load():
    return json.loads(RECORD.read_bytes())
def exact(obj,fields,what):
    if type(obj) is not dict or set(obj)!=set(fields):
        deny("missing or unreviewed "+what+" fields")
def literal(path):
    return ast.literal_eval(Path(path).read_text())
def source_constants(path,keys):
    tree=ast.parse(Path(path).read_text())
    found={}
    for node in tree.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target,ast.Name) and target.id in keys:
                    found[target.id]=ast.literal_eval(node.value)
    if set(found)!=set(keys):deny("source owner constants missing")
    return found
def load_host_protocol(path):
    spec=importlib.util.spec_from_file_location("reviewed_host_gateway_protocol",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def verify(record, fonts_host, taskc_host, immutable_producer, signed_reader=None,
           compiler_consumer=None):
    """Verify exact source inputs, while refusing all compiler/dispatcher admission."""
    exact(record,("schema","status","task","producer","reviewer","task_catalogue",
                  "gateway","native_gates","budget","resource_admission",
                  "submission","output_evidence"),"preparation")
    if record["schema"]!="zog-fonts-github-trigger-preparation-v1" or record["status"]!="PREPARED_NOT_SUBMITTABLE" or record["task"]!=TASK:
        deny("source preparation promoted or wrong task")
    p=record["producer"]
    if p!={"repository":"zog144/image-build","source_revision":SOURCE,
           "source_plan_path":"project/bootstrap/graphics-fonts.py",
           "monthly_pin_path":"project/pins/2026-10-01/commit-pin.py",
           "monthly_pin_sha256":PIN}:
        deny("original source or October pin substituted")
    if record["reviewer"]!={"host_deploy_fonts_catalogue_revision":HOST_FONTS,
                            "host_deploy_compiler_consumer_revision":HOST_CONSUMER,
                            "host_deploy_task_c_revision":HOST_TASK_C,
                            "compiler_base_reader_revision":READER}:
        deny("independently frozen host-deploy source review head changed")
    cat=record["task_catalogue"]
    required_catalogue={
        "schema":2,"only_task":TASK,"entries":[list(e) for e in ENTRIES],
        "targets":list(TARGETS),"arguments_mode":"image",
        "selected_base_generation":None,"selected_managed_lane":None,
        "selected_host":None,"installed_catalogue_sha256":None,
        "installed_catalogue_receipt_sha256":None,
    }
    if cat!=required_catalogue:deny("unreviewed graphical task, fabricated base, or catalogue receipt")
    if record["native_gates"]!={k:None for k in GATE_KEYS}:
        deny("native owner admission fabricated by source readiness record")
    if record["budget"]!={"work_bytes":30*1024**3,"external_bytes":2*1024**3,
                           "total_bytes":32*1024**3,"execution_limit_seconds":21600}:
        deny("native compiler resource contract widened")
    if record["resource_admission"]!={
            "schema":"zog-fonts-root-backed-resource-admission-v1",
            "backend":"existing-root-filesystem-project-quota",
            "catalogue_directory":"/var/lib/zog/fonts",
            "work_directory":"/var/lib/zog/fonts/work",
            "external_directory":"/var/lib/zog/fonts/external",
            "native_quota_observed":False,
            "native_worker_mounts_observed":False,
            "native_deadline_observed":False,
            "native_catalogue_installed":False}:
        deny("native resource admission fabricated or selected storage changed")
    if record["submission"]!={"enabled":False,"auto_retry":False,
                                "manual_direct_ssm_allowed":False,
                                "github_issue_created":False,
                                "submitted_sqs_message":False,
                                "acceptance_claimed":False}:
        deny("source preparation confused with request or approved submission")
    g=record["gateway"]
    if g!={"event":"issues.opened","origin_repository":"zog144/host-deploy",
           "operation":"build.submit","source_repository":"zog144/image-build",
           "source_commit":SOURCE,"request_schema":1,"request_id":None,
           "workspace_id":None,"issue_number":None,"actor":None,
           "request_sha256":None,"queue_receipt":None,
           "dispatcher_selected_revision":None,"admin_operation_opt_in":None}:
        deny("invented original GitHub request, actor or FIFO acknowledgement")
    o=record["output_evidence"]
    if o!={**{k:None for k in OUTPUT_NULLS},
           "schema":"image-build-verified-graphical-predecessor-v1",
           "output_kind":"image","actual_immutable_generation_verified":False}:
        deny("signed-looking generation receipt or pipeline ID fabricated")

    fonts_host=Path(fonts_host).resolve(strict=True)
    taskc_host=Path(taskc_host).resolve(strict=True)
    immutable_producer=Path(immutable_producer).resolve(strict=True)
    if signed_reader is None:
        deny("independently pinned compiler reader source is absent")
    signed_reader=Path(signed_reader).resolve(strict=True)
    if compiler_consumer is None:
        deny("independently reviewed PR29 compiler consumer source is absent")
    compiler_consumer=Path(compiler_consumer).resolve(strict=True)
    reader_source=signed_reader/"src/zog/image_build/compiler_base_acceptance.py"
    isolation_source=signed_reader/"src/zog/image_build/compiler_base_isolation.py"
    if not reader_source.is_file() or not isolation_source.is_file():
        deny("current observed-isolation compiler reader source missing")
    observed_source=reader_source.read_text()
    isolation_text=isolation_source.read_text()
    if (not all(x in observed_source for x in (
         'SCHEMA = "image-build-compiler-base-acceptance-v1"',
         'BINDING = "image-build-compiler-base-binding-v1"',
         'from .compiler_base_isolation import validate as validate_isolation',
         'validate_isolation(probe["isolation"], e, claim["installed_paths"])',
         'observed["uid"]!=configuration.get("execution_user_id")',
         'observed["gid"]!=configuration.get("execution_group_id")',
         'claim["generation_kind"] not in ("toolchain","image")',
    )) or source_constants(isolation_source,{"SCHEMA","PROFILE"})!={
         "SCHEMA":"image-build-compiler-isolation-v2",
         "PROFILE":"selected-root-kernel-mounts-v1",
    } or not all(x in isolation_text for x in (
         "'/proc': 'proc'", "'/sys': 'sysfs'",
         "elif path in PSEUDO:", "if path=='/':",
         "or not 1<=len(mounts)<=40:",
    ))):
        deny("current compiler reader lacks reviewed actual mount/worker isolation profile")
    # The shared compiler ACCEPTANCE consumer is exact PR29 source. The
    # dedicated one-task PR7 catalogue owner intentionally extends PR29's
    # original owner: it now freezes compiler_base in the real pipeline.submit,
    # and its own entire Git source is pinned independently by HOST_FONTS.
    suffix=Path("src/zog/host_deploy/gateway/graphics_base_acceptance.py")
    selected=fonts_host/suffix
    reviewed=compiler_consumer/suffix
    if (not selected.is_file() or not reviewed.is_file() or
            selected.read_bytes()!=reviewed.read_bytes()):
        deny("first-Fonts compiler acceptance consumer differs from reviewed PR29")
    owner_path=fonts_host/"src/zog/host_deploy/gateway/graphics_catalogue_owner.py"
    owner_bytes=owner_path.read_bytes()
    git_blob=hashlib.sha1(b"blob "+str(len(owner_bytes)).encode("ascii")+bytes([0])+owner_bytes).hexdigest()
    if git_blob!=OWNER_GIT_BLOB:
        deny("first-Fonts root-backed catalogue owner differs from exact reviewed PR7 source")
    resource_source=(fonts_host/"src/zog/host_deploy/gateway/fonts_resource_admission.py").read_text()
    if not all(token in resource_source for token in (
            'SCHEMA="zog-fonts-root-backed-resource-admission-v1"',
            'WORK_BYTES=30*1024**3', 'EXTERNAL_BYTES=2*1024**3',
            'TIME_SECONDS=21600', 'def inspect_native(',
            'FS_IOC_FSGETXATTR', 'Q_XGETQUOTA',
            'same_host_root_filesystem', 'quota_active',
            'if free_bytes<TOTAL_BYTES:')):
        deny("exact reviewed existing-root filesystem resource admission missing")
    owner_source=owner_bytes.decode("utf-8")
    catalogue_source=(fonts_host/"src/zog/host_deploy/gateway/task_catalogue.py").read_text()
    if (('"compiler_base": bound_base["accepted_receipt_sha256"]' not in owner_source
          or 'required.add("compiler_base")' not in catalogue_source
          or 'retained_input_evidence["evidence"].get("accepted_receipt_sha256")' not in catalogue_source)):
        deny("actual first Fonts request does not freeze independently accepted compiler receipt")
    consumer=(fonts_host/"src/zog/host_deploy/gateway/graphics_base_acceptance.py").read_text()
    if not all(x in consumer for x in (
        '"image-build-compiler-isolation-v2"',
        '"selected-root-kernel-mounts-v1"',
        'not match(probe["isolation"].get("witness_sha256"),SHA)',
        '"x86_64-zog-linux-gnu"',
        '"independent-compiler-capability-observed-not-job-authorization"',
    )):
        deny("first-Fonts catalogue retains obsolete compiler consumer/probe contract")
    owner=source_constants(fonts_host/"src/zog/host_deploy/gateway/graphics_catalogue_owner.py",
          {"SOURCE","REPOSITORY","PIN_PATH","PIN_SHA256","PIN_DATE","TASK","READER_SOURCE"})
    if owner!={"SOURCE":SOURCE,"REPOSITORY":"zog144/image-build",
              "PIN_PATH":p["monthly_pin_path"],"PIN_SHA256":PIN[7:],
              "PIN_DATE":"2026-10-01","TASK":TASK,
              "READER_SOURCE":READER}:
        deny("PR7 original first-Fonts native owner selects different source/pin/task")
    catalogue=source_constants(fonts_host/"src/zog/host_deploy/gateway/task_catalogue.py",
                               {"SCHEMA","REVIEWED_IMAGE_TASKS"})
    if catalogue["SCHEMA"]!=2:
        deny("first task catalogue schema was changed")
    entry=catalogue["REVIEWED_IMAGE_TASKS"][TASK]
    if entry!={"entries":ENTRIES,"targets":TARGETS}:
        deny("actual reviewed PR7 Fonts recipe selection changed")
    plan=literal(immutable_producer/p["source_plan_path"])
    if plan.get("schema")!=1 or plan.get("architecture")!="x86_64":
        deny("source Fonts bootstrap plan differs")
    stages=plan.get("stages")
    if type(stages) is not list or [(x.get("id"),x.get("project"),x.get("recipe"))
               for x in stages]!=[ENTRIES[2],ENTRIES[1],ENTRIES[0]]:
        deny("actual producer build-stage ordering differs")
    if plan.get("targets")!=list(TARGETS):
        deny("original immutable source target ordering differs")
    pin=immutable_producer/p["monthly_pin_path"]
    if not pin.is_file() or pin.is_symlink() or ("sha256:"+hashlib.sha256(pin.read_bytes()).hexdigest())!=PIN:
        deny("original October monthly pin bytes differ")

    protocol=load_host_protocol(taskc_host/"src/zog/host_deploy/gateway/protocol.py")
    if protocol.BUILD_TASKS!={"graphics-fonts-image-v1","graphics-xcb-core-image-v1",
           "graphics-x11-core-image-v1","xcb-support-image-v1"}:
        deny("actual task allowlist changed without independent review")
    if protocol.ORIGIN_REPOSITORY!="zog144/host-deploy" or protocol.SOURCE_REPOSITORIES!={"zog144/image-build"}:
        deny("original GitHub issue provenance or producer repository changed")
    if "build.submit" not in protocol.OPERATIONS:
        deny("typed build.submit no longer reviewed")
    # Verify only synthetic shape. This request is not returned, serialized,
    # queued, reported as accepted, or usable as an actual GitHub issue.
    synthetic={
        "schema":1,"request_id":"11"*16,"workspace_id":"22"*16,
        "operation":"build.submit","source":{"repository":"zog144/image-build","commit":SOURCE},
        "origin":{"repository":"zog144/host-deploy","issue_number":1,
                  "trigger_actor":"source-fixture"},
        "parameters":{"lane":"source-fixture","task":TASK},
    }
    protocol.validate_request(synthetic)
    for field,value in [
        ("source",{"repository":"zog144/image-build","commit":"b0f53dbdec0e88b9b37feb5317398db3d20507dd"}),
        ("parameters",{"lane":"source-fixture","task":"mesa-final"}),
    ]:
        altered=dict(synthetic)
        altered[field]=value
        if field=="source":
            # The generic protocol allows a syntactically valid *other* commit;
            # the reviewed owner and immutable catalogue selection must veto it.
            if altered["source"]["commit"]==SOURCE:
                deny("source substitution negative is broken")
        else:
            try:
                protocol.validate_request(altered)
            except protocol.RequestProtocolError:
                pass
            else:
                deny("unreviewed task unexpectedly accepted by original gateway")

    dispatch=(taskc_host/"src/zog/host_deploy/gateway/github_dispatch.py").read_text()
    workflow=(taskc_host/".github/workflows/gateway-issue-dispatch.yml").read_text()
    # Task C is now one trusted Host gateway with existing instance IAM and
    # fsynced per-operation local send-once claims. Do not reintroduce the
    # obsolete S3, separately signed Task C installation or SSM-owner IPC.
    trusted=(taskc_host/"src/zog/host_deploy/gateway/trusted_host_submission.py").read_text()
    pipeline=(taskc_host/"src/zog/host_deploy/gateway/generic_pipeline.py").read_text()
    send_once=(taskc_host/"src/zog/host_deploy/gateway/graphics_operation_send_intent.py").read_text()
    attester=(immutable_producer/"src/zog/image_build/graphical_generation_acceptance.py").read_text()
    if (not all(s in dispatch for s in (
        'ISSUE_MARKER = "<!-- zog-gateway-request:v1 -->"',
        'event.get("action") != "opened"',
        '"origin" in intent',
        'MessageDeduplicationId=request["request_id"]',
        '"total_max_attempts": 1',
    )) or not all(s in workflow for s in (
        'types: [opened]','github.run_attempt == 1',
        "vars.ZOG_GATEWAY_SUBMIT_ENABLED == 'true'",
        'id-token: write','github_configuration',
        'github_dispatch submit',
    ))):
        deny("original issue-opened OIDC/FIFO single-submission contract changed")
    if (not all(x in trusted for x in (
            'DOCUMENT = "AWS-RunShellScript"',
            'from .image_build_dispatch import verify_current_target',
            'def selected_command(', 'def submit_once(',
            'return host.submit_command(script, seconds=seconds)',
        )) or not all(x in pipeline for x in (
            'def advance(', '_protected_original_identifiers(',
            'from . import trusted_host_submission as trusted',
            'send_intent.claim(', 'trusted.submit_once(',
            'send_intent.record_command(',
        )) or not all(x in send_once for x in (
            'host-deploy-generic-operation-send-once-v1',
            'def claim(', 'def refuse_if_claimed(', 'def require_command(',
            'os.fsync(',
        ))):
        deny("November 11 trusted-Host single-attempt Task C source selection changed")
    for content in (pipeline, trusted):
        # Do not reject historical unselected modules; reject use by the
        # actual selected gateway stage execution route.
        imports=ast.walk(ast.parse(content))
        for node in imports:
            if isinstance(node,ast.ImportFrom) and node.module and any(
                stale in node.module for stale in (
                    'graphics_owner_ipc','graphics_owner_trust_history',
                    'graphics_broker','graphics_s3','owner_checkpoint')):
                deny("retired S3/broker owner imported into active Task C path")
    if not all(s in attester for s in (
         'EVIDENCE = "image-build-verified-graphical-predecessor-v1"',
         '"output_kind": "image"','"pipeline_id": context["pipeline_id"]',
         '"acceptance_receipt_sha256": pointer["record"]',
         '"producer_receipt_sha256": producer_receipt',
         '"generation_manifest_sha256": _sha256(manifest_raw)',
         '"uncertainty": False','"missing_evidence_count": 0',
         'def attest_native(', 'os.geteuid() != 0',
    )):
        deny("original source cannot attest accepted distinct Fonts output")
    return {
        "source_contract":"EXACT_FONTS_PLAN_AND_ORIGINAL_PIN",
        "gateway_protocol":"SYNTHETIC_SHAPE_ONLY",
        "gateway_installation":"NATIVE_NOT_INSTALLED",
        "native_evidence":None,
        "task":"graphics-fonts-image-v1",
        "submission":"PREPARED_NOT_SUBMITTABLE",
        "accepted_generation":None
    }


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--fonts-host",required=True)
    parser.add_argument("--taskc-host",required=True)
    parser.add_argument("--image-build-source",required=True)
    parser.add_argument("--signed-reader",required=True)
    parser.add_argument("--compiler-consumer",required=True)
    args=parser.parse_args()
    print(json.dumps(verify(load(),args.fonts_host,args.taskc_host,args.image_build_source,args.signed_reader,
                           args.compiler_consumer),
                     sort_keys=True))

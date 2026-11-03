#!/usr/bin/env python3
"""Cross-repository SOURCE review only. NEVER returns compiler authorization.

The immutable host-deploy Git blobs are fetched only by an explicit source-CI
flag. Offline synthetic requests remain bounded and cannot mint native grants.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "project/graphics-first-workspace/host-deploy-submission-audit.json"
HANDOFF = ROOT / "project/graphics-first-workspace/source-to-native-handoff.json"
SCHEMA = "zog-first-workspace-host-deploy-submission-audit-v1"
SELECTED_SOURCE = "1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
MESA = "9cbd652226b863a7b4bb2d6d9539722e1a262508"
HD11 = "7d052b340a026497fd32afb82d0a290d1d6bc60e"
TASKS = ("graphics-fonts-image-v1", "graphics-xcb-core-image-v1", "graphics-x11-core-image-v1")
SLOTS = frozenset(("fonts", "XCB", "X11", "zlib_native_environment",
                    "ncurses_temporary", "LLVM", "Mesa"))
HOLD = "PREPARED_NOT_SUBMITTABLE"
PREFIX = "src/zog/host_deploy/gateway/"

def _require(condition, reason):
    if not condition:
        raise ValueError(reason)

def review_contract(audit, handoff):
    _require(type(audit) is dict and audit.get("schema") == SCHEMA, "wrong submission audit schema")
    _require(audit.get("status") == "SOURCE_REVIEW_NO_COMPILER_SUBMISSION", "source review escalated")
    _require(audit.get("host_deploy_pr11_source") == HD11, "host-deploy exact reviewed revision changed")
    _require(audit.get("host_deploy_pr8_source") == "a4ac7cdb4646e0fcd9a9cf49df9d367f2a108006",
             "base graphical chain revision changed")
    _require(audit.get("host_deploy_selected_image_source") == SELECTED_SOURCE,
             "root-selected compiler source revision changed")
    _require(audit.get("mesa_source") == MESA and handoff.get("source_revisions",{}).get("mesa_pr8") == MESA,
             "outdated or changed Mesa review source")
    _require(tuple(audit.get("reviewed_graphical_tasks",[])) == TASKS,
             "unreviewed graphical task entered finite chain")
    _require(frozenset(audit.get("inherited_receipt_slots",[])) == SLOTS,
             "missing inherited protected generation slot")
    _require(all(audit.get(key) is False for key in (
        "source_handoff_admits_compiler", "native_receipts_observed",
        "host_install_current_authority_observed", "authorized_submission_test_allowed")),
        "source review illegally claims protected authority")
    _require(type(handoff) is dict and handoff.get("status") == HOLD
             and handoff.get("native_accepted") is False
             and handoff.get("build_submission_allowed") is False
             and handoff.get("rights_authorized") is False,
             "source-only handoff prematurely admitted for compilation")
    receipts = handoff.get("accepted_generation_receipts", {})
    _require(type(receipts) is dict and set(receipts) == SLOTS
             and all(value is None for value in receipts.values()),
             "unverified or forged inherited generation receipts")
    _require(len(audit.get("protected_gate_obligations", [])) == 7,
             "protected source/authority/worker prerequisite omitted")
    blobs = audit.get("host_deploy_source_blobs")
    _require(type(blobs) is dict and len(blobs) == 9 and
             all(path.startswith(PREFIX) and len(digest) == 40
                 and set(digest) <= set("0123456789abcdef")
                 for path,digest in blobs.items()),
             "missing exact reviewed host-deploy source blobs")
    return True

def synthetic_blockers(handoff, audit, candidate):
    """Independent source model: report why *any* purported request is NO-GO.

    This does not call host-deploy, and never consumes a signed receipt.
    A real native gate must revalidate source/issuer/checkpoint/stage-once.
    """
    reasons = []
    if handoff.get("status") == HOLD or handoff.get("build_submission_allowed") is not True:
        reasons.append("prepared-plan-not-authorized")
    if candidate.get("task") not in TASKS:
        reasons.append("task-not-in-protected-host-deploy-allowlist")
    if candidate.get("source_revision") != audit.get("host_deploy_selected_image_source"):
        reasons.append("task-source-revision-mismatch")
    if candidate.get("mesa_source") != MESA or handoff.get("source_revisions",{}).get("mesa_pr8") != MESA:
        reasons.append("mesa-source-pin-mismatch")
    if not candidate.get("accepted_x11") or handoff.get("accepted_generation_receipts",{}).get("X11") is None:
        reasons.append("x11-accepted-generation-missing")
    if candidate.get("checkpoint_protected_verified") is not True:
        reasons.append("independent-checkpoint-unverified")
    # A syntactically plausible source-supplied SHA or "verified" boolean is
    # NEVER accepted as an issuer/manifest/installation-bound native receipt.
    reasons.append("protected-native-admission-not-available-to-source-ci")
    return tuple(reasons)

def refuse_submission(handoff, audit, candidate):
    reasons = synthetic_blockers(handoff, audit, candidate)
    raise ValueError("graphical compiler submission DENIED: " + ", ".join(reasons))

def _literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id==name
                                                for t in node.targets):
            if (isinstance(node.value,ast.Call)
                    and isinstance(node.value.func,ast.Name)
                    and node.value.func.id=="frozenset" and len(node.value.args)==1):
                return frozenset(ast.literal_eval(node.value.args[0]))
            return ast.literal_eval(node.value)
    raise ValueError("expected constant absent: " + name)

def _function(tree, name):
    value = next((node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
                  and node.name==name), None)
    _require(value is not None, "required protected host-deploy entry point missing: "+name)
    return value

def verify_pinned_host_deploy_source(audit, *, fetch=None):
    """Review actual source bytes, not only a copied task list."""
    review_contract(audit, json.loads(HANDOFF.read_text()))
    fetch = fetch or _remote_source
    trees={}
    source={}
    for path, expected_blob in sorted(audit["host_deploy_source_blobs"].items()):
        data=fetch(path,HD11)
        _require(type(data) is bytes and 0<len(data)<=512*1024,
                 "source blob missing or oversized: "+path)
        digest=hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()
        _require(digest==expected_blob, "host-deploy immutable source blob changed: "+path)
        source[path]=data.decode("utf-8")
        trees[path]=ast.parse(source[path])
    owner=trees[PREFIX+"graphics_catalogue_owner.py"]
    chain=trees[PREFIX+"graphics_generation_chain.py"]
    tasks=trees[PREFIX+"task_catalogue.py"]
    protocol=trees[PREFIX+"protocol.py"]
    pipeline=trees[PREFIX+"generic_pipeline.py"]
    checkpoint=trees[PREFIX+"graphics_external_checkpoint.py"]
    export=trees[PREFIX+"graphics_chain_export.py"]
    history=trees[PREFIX+"graphics_gateway_history.py"]
    stage_once=trees[PREFIX+"graphics_stage_once.py"]
    _require(_literal(owner, "SOURCE") == SELECTED_SOURCE, "host-deploy native owner source changed")
    _require(tuple(_literal(chain,"TASKS"))==TASKS, "host-deploy chain stages expanded/reordered")
    reviewed=_literal(tasks,"REVIEWED_IMAGE_TASKS")
    _require(all(name in reviewed for name in TASKS), "host-deploy catalogue missing chain tasks")
    _require(not any("mesa" in name or "xvnc" in name or "xterm" in name
                     for name in reviewed), "unreviewed Workspace task added")
    _require(set(TASKS).issubset(_literal(protocol,"BUILD_TASKS")),
             "typed gateway protocol lacks reviewed stages")
    _require(_literal(tasks,"SCHEMA")==2, "task catalogue typed schema changed")
    _function(pipeline,"_base")
    _require("require_record(root, request_id, binding)" in source[PREFIX+"generic_pipeline.py"],
             "durable protected stage-once record missing from pipeline")
    _function(stage_once,"require_record")
    _function(checkpoint,"require_current")
    _function(history,"verify_history")
    _function(export,"load_selected_step")
    _require(source[PREFIX+"graphics_chain_export.py"].count("external.require_current(pin)") >= 2,
             "checkpoint not checked around live graphical export")
    _require("'compiler_authorized': False" in source[PREFIX+"graphics_generation_chain.py"] or
             '"compiler_authorized": False' in source[PREFIX+"graphics_generation_chain.py"],
             "protected chain no longer holds compiler authority")
    return True

def _remote_source(path, revision):
    url = "https://raw.githubusercontent.com/zog144/host-deploy/"+revision+"/"+path
    req = Request(url, headers={"User-Agent":"zog-source-readonly-interop/1"})
    with urlopen(req, timeout=25) as stream:
        raw=stream.read(512*1024+1)
    return raw

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify-pinned-host-deploy",action="store_true")
    args=parser.parse_args()
    handoff=json.loads(HANDOFF.read_text())
    audit=json.loads(AUDIT.read_text())
    review_contract(audit,handoff)
    if args.verify_pinned_host_deploy:
        verify_pinned_host_deploy_source(audit)
    try:
        refuse_submission(handoff,audit,{"task":TASKS[2],"source_revision":SELECTED_SOURCE,
            "mesa_source":MESA,"accepted_x11":True,"checkpoint_protected_verified":True})
    except ValueError as exc:
        _require(str(exc).startswith("graphical compiler submission DENIED:"),
                 "unexpected source gate result")
        print("Pinned host-deploy source contract PASS; "+str(exc))
    else:
        raise AssertionError("source-only review unexpectedly authorized a compiler")

if __name__=="__main__":
    main()

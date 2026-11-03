#!/usr/bin/env python3
"""Read-only integrated Resident B PR14/PR15 source review. Never runs a controller."""
import ast
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"project/package"
RECORD=ROOT/"project/host/resident-b-pr14-pr15-combined-source-review.json"
STAGES=("resident312-flit-core","resident312-installer","resident312-packaging",
        "resident312-wheel","resident312-setuptools","resident312-dbus-next",
        "resident312-image-build")

def load_verifier(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

dep=load_verifier("combined_transitive","tools/verify_resident312_transitive_sources.py")
install=load_verifier("combined_install","tools/verify_resident_b_controller_install_security.py")

def refuse(message):
    raise ValueError("Resident B combined source NOT READY: "+message)

def literal(path):
    return ast.literal_eval(path.read_text())

def verify(*, record=None, controller_overrides=None, tool_overrides=None):
    data=record if record is not None else json.loads(RECORD.read_text())
    if (type(data) is not dict or set(data)!={
            "schema","status","pr14_source_head","pr15_original_source_head",
            "reconciliation_strategy","py312_candidate","source_tool_stages",
            "controllers","expected_installed_outputs","required_native_holds",
            "trusted_native_witness","accepted_generation","compiler_submission_allowed",
            "service_activation_allowed","redistribution_authorized"
        } or
        data["schema"]!="zog-resident-b-combined-source-review-v1" or
        data["status"]!="SOURCE_ONLY_NATIVE_NOT_READY" or
        data["pr14_source_head"]!="e64e682f2fb2df8f590737683b99188c16fc51c0" or
        data["pr15_original_source_head"]!="bc5a93b18fd8ce39f3e72cd67d05dc0534f98b88" or
        data["reconciliation_strategy"]!="non-destructive-two-parent-merge" or
        data["py312_candidate"]!="python-resident312-final" or
        data["source_tool_stages"]!=[x+"-final" for x in STAGES] or
        data["controllers"]!=["box-control-final","root-control-final"]):
        refuse("stale/different source input or unauthorized review record")
    if (data["trusted_native_witness"] is not None or
        data["accepted_generation"] is not None or
        any(data[x] is not False for x in
            ("compiler_submission_allowed","service_activation_allowed","redistribution_authorized"))):
        refuse("source record fabricated native admission")
    holds=data["required_native_holds"]
    if not isinstance(holds,list) or len(holds)!=5 or not all(
        isinstance(x,str) and len(x)>=25 for x in holds):
        refuse("native or rights obligations omitted")
    deps=dep.verify(overrides=tool_overrides)
    inst=install.verify(overrides=controller_overrides)
    if (deps["source_chain"]!="SEVEN_PINNED_CP312_CANDIDATES" or
        deps["native_generation"] is not None or
        deps["compiler_authorization"] is not False or
        inst["native_install"]!="NO_GO" or
        inst["root_service"]!="DISABLED_ROOT_ONLY" or
        inst["box_control"]!="ONE_SHOT_NONROOT_UNSELECTED"):
        refuse("source or privileged installation already promoted")
    named=data["expected_installed_outputs"]
    if set(named)!={"box-control","root-control"}:
        refuse("missing/extra installed controller output mapping")
    for name in named:
        source=literal(PKG/name/"stages/final/produce-manifest.py")
        outputs=named[name]
        if (type(outputs) is not list or len(outputs)!=len(set(outputs)) or
            set(source["required"])!=set(outputs)):
            refuse("stale output manifest, console script, original notice or RECORD: "+name)
        if (not any(x.endswith(".dist-info/RECORD") for x in outputs) or
            not any(x.endswith(".dist-info/METADATA") for x in outputs) or
            "usr/bin/"+name not in outputs or
            not any(x.endswith("/__init__.py") for x in outputs)):
            refuse("wheel RECORD, metadata or console script absent: "+name)
        build=literal(PKG/name/"stages/final/build.py")
        command=build["install"][0][-1]
        for output in outputs:
            if output.startswith("usr/lib/python3.12/site-packages/") and (
                "/"+output not in command and
                "dist/*.whl" not in command):
                refuse("source install does not target declared output: "+output)
        if "/usr/bin/python3.12 -I -m installer" not in command:
            refuse("controller installer unpinned from selected interpreter: "+name)
        edge=literal(PKG/name/"stages/final/dependencies.py")
        if edge!=dep.CONTROLLERS[name]:
            refuse("stale/missing controller runtime or tool predecessor: "+name)
    if "usr/lib/systemd/system/zog-root-control.service" not in named["root-control"] or (
        any("/systemd/system/" in p for p in named["box-control"])):
        refuse("controller daemon and one-shot ownership confused")
    return {"review":"SOURCE_GRAPH_AND_INSTALLATION_CONSISTENT",
            "actual_native_compilation":"NOT_EXECUTED",
            "selected_native_generation":None,
            "authority":"NO_GO"}

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))

#!/usr/bin/env python3
"""Offline source handoff gate, NOT a native authority or generator of accepted IDs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("fonts", "XCB", "X11", "LLVM", "Mesa", "Xvnc-i3-xterm", "mesa-demos-smoke")
EDGES = (("fonts","Xvnc-i3-xterm"), ("XCB","X11"), ("X11","Mesa"),
         ("X11","Xvnc-i3-xterm"), ("LLVM","Mesa"), ("Mesa","Xvnc-i3-xterm"),
         ("Xvnc-i3-xterm","mesa-demos-smoke"))
RECEIPTS = ("fonts","XCB","X11","zlib_native_environment","ncurses_temporary","LLVM","Mesa")
SOURCES = {"workspace_pr9_reviewed_input":"db13d73a45f8a3be579226656442c331a9f701ea",
           "mesa_pr8":"9cbd652226b863a7b4bb2d6d9539722e1a262508"}
MUST_OUTPUT = ("usr/bin/Xvnc","usr/bin/i3","usr/bin/xterm","usr/lib/dri/swrast_dri.so",
               "usr/bin/glxgears","usr/bin/xkbcomp","usr/share/fonts/X11/misc/6x13.pcf.gz",
               "usr/share/terminfo/x/xterm", "usr/share/licenses/turbovnc/libsha1-COPYING")
REQUIRED_TOOLS = ("C-C++-linker-ar-objcopy-readelf", "meson-ninja-cmake-pkgconf",
                  "python-generators","XKB-and-font-tools","build-utilities")

def verify(record):
    if record.get("schema") != "zog-first-workspace-source-to-native-handoff-v1":
        raise ValueError("unknown Workspace handoff schema")
    if record.get("status") != "PREPARED_NOT_SUBMITTABLE":
        raise ValueError("source handoff cannot claim native readiness")
    order=record.get("producer_order")
    if tuple(order or ()) != STAGES or len(set(order))!=len(order):
        raise ValueError("missing or reordered native predecessor")
    if {tuple(x) for x in record.get("producer_edges", [])} != set(EDGES):
        raise ValueError("missing/changed dependency edge")
    indices={name:i for i,name in enumerate(order)}
    for predecessor,consumer in EDGES:
        if indices[predecessor]>=indices[consumer]:
            raise ValueError("Mesa/Xvnc or fonts/X11 producer ordering violated")
    receipts=record.get("accepted_generation_receipts")
    if not isinstance(receipts,dict) or set(receipts)!=set(RECEIPTS):
        raise ValueError("missing inherited or graphical predecessor receipt slot")
    if any(value is not None for value in receipts.values()):
        raise ValueError("fabricated or unauthenticated generation receipt")
    if record.get("source_revisions")!=SOURCES:
        raise ValueError("source revision changed; independently re-freeze exact sources")
    if "re-frozen" not in record.get("source_revision_policy",""):
        raise ValueError("moving PR head cannot count as immutable source")
    for key in ("native_accepted","rights_authorized","build_submission_allowed","canonical_promotion_allowed"):
        if record.get(key) is not False:
            raise ValueError("source-only handoff escalated: "+key)
    if record.get("native_readiness")!="REFUSE_MISSING_AUTHENTIC_RECEIPTS_AND_INDEPENDENT_ADMISSION":
        raise ValueError("source-only negative-readiness policy removed")
    for key in ("inherited_stages","required_resources","required_tools","expected_outputs","protected_evidence"):
        if not isinstance(record.get(key),list) or not record[key]:
            raise ValueError("missing handoff evidence: "+key)
    for token in ("zlib-native-environment","ncurses-temporary"):
        if token not in record["inherited_stages"]:
            raise ValueError("missing inherited selected Zog stage: "+token)
    for output in MUST_OUTPUT:
        if output not in record["expected_outputs"]:
            raise ValueError("missing native output: "+output)
    tools=record.get("required_tool_provenance")
    if not isinstance(tools,dict) or set(tools)!=set(REQUIRED_TOOLS) or any(not v for v in tools.values()):
        raise ValueError("missing selected build-tool origins or no-Host-leakage evidence")
    if not record.get("rights_gate","").startswith("HOLD:"):
        raise ValueError("component rights cannot be source-approved")
    if not isinstance(record.get("source_packages"),dict) or not record["source_packages"].get("mesa_draft"):
        raise ValueError("Mesa source packages absent from handoff")
    return True

def refuse_native_readiness(record):
    """Never infer an authorized generation from a source JSON file.
    
    Authenticity requires a separate protected verifier; this check cannot
    create, import or trust any receipt it is asked to read.
    """
    receipts=record.get("accepted_generation_receipts",{})
    missing=[name for name in RECEIPTS if not isinstance(receipts,dict) or receipts.get(name) is None]
    if missing:
        raise ValueError("native-readiness DENIED: authentic protected generation receipts missing: "+
                         ", ".join(missing))
    raise ValueError("native-readiness DENIED: source CI cannot authenticate or authorize generation receipts")

if __name__ == "__main__":
    record=json.loads((ROOT/"project/graphics-first-workspace/source-to-native-handoff.json").read_text())
    verify(record)
    try:
        refuse_native_readiness(record)
    except ValueError as err:
        if not str(err).startswith("native-readiness DENIED:"):
            raise
        print("Workspace handoff source checks PASS; "+str(err))
    else:
        raise AssertionError("source-only gate wrongly admitted native build")

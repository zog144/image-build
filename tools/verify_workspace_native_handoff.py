#!/usr/bin/env python3
"""Refuse a fabricated source-to-native handoff: source CI is never a native witness."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STAGES = ("fonts", "XCB", "X11", "Xvnc-i3-xterm", "Mesa")
RECEIPTS = ("fonts", "XCB", "X11", "zlib_native_environment", "ncurses_temporary", "Mesa")

def verify(record):
    if record.get("schema") != "zog-first-workspace-source-to-native-handoff-v1":
        raise ValueError("unknown Workspace handoff schema")
    if record.get("status") != "PREPARED_NOT_SUBMITTABLE":
        raise ValueError("source handoff cannot claim native readiness")
    if tuple(record.get("producer_order", [])) != STAGES:
        raise ValueError("missing or reordered native predecessor")
    receipts = record.get("accepted_generation_receipts")
    if not isinstance(receipts, dict) or set(receipts) != set(RECEIPTS):
        raise ValueError("missing inherited or graphical predecessor receipt slot")
    if any(value is not None for value in receipts.values()):
        raise ValueError("fabricated or unauthenticated generation receipt")
    revisions = record.get("source_revisions", {})
    if revisions != {
        "workspace_pr9":"17c4fbceabf9cc2ac2a650583bd7b0caf8972974",
        "mesa_pr8":"9cbd652226b863a7b4bb2d6d9539722e1a262508",
    }:
        raise ValueError("source revision changed; independently reconcile exact PR heads")
    for key in ("native_accepted","rights_authorized","build_submission_allowed","canonical_promotion_allowed"):
        if record.get(key) is not False:
            raise ValueError("source-only handoff escalated: " + key)
    for key in ("inherited_stages","required_resources","required_tools","expected_outputs","protected_evidence"):
        if not isinstance(record.get(key), list) or not record[key]:
            raise ValueError("missing handoff predecessors or evidence: " + key)
    for token in ("zlib-native-environment","ncurses-temporary"):
        if token not in record["inherited_stages"]:
            raise ValueError("missing inherited selected Zog stage: "+token)
    for output in ("usr/bin/Xvnc","usr/bin/i3","usr/bin/xterm","usr/lib/dri/swrast_dri.so","usr/bin/glxgears"):
        if output not in record["expected_outputs"]:
            raise ValueError("missing native expected output: "+output)
    return True

if __name__ == "__main__":
    record=json.loads((ROOT/"project/graphics-first-workspace/source-to-native-handoff.json").read_text())
    verify(record)
    print("Workspace handoff source checks PASS; native receipts absent; build submission DENIED")

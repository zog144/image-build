"""GLib/Cairo/Pango upstream-pin ledger deliberately cannot grant compiler admission."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"project/graphics-first-workspace"

def test_text_stack_pins_and_compositional_dependency_holds():
    plan=json.loads((ROOT/"text-stack-candidates.json").read_text())
    assert plan["schema"]=="zog-first-workspace-text-source-preparation-v1"
    assert plan["status"]=="source-pinned-no-compiled-graph"
    for key in ("native_accepted","canonical_admitted","redistribution_authorized"):
        assert plan[key] is False
    for name,item in plan["versions"].items():
        assert len(item["sha256"])==64 and item["url"].startswith("https://")
        assert item["unresolved"] and item["predecessors"] and item["provides"]
    pango=set(plan["versions"]["pango"]["predecessors"])
    assert {"glib","cairo","harfbuzz","fribidi"}<=pango
    assert {"pixman","libXrender"}<=set(plan["versions"]["cairo"]["predecessors"])
    assert {"libXrender","harfbuzz","fribidi"}<=set(plan["remaining_new_catalogue_inputs"])

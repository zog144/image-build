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
        assert item["original_notice_members"]
        assert all(len(digest)==64 and len(path)>0 for path,digest in item["original_notice_members"].items())
    assert len(plan["versions"]["glib"]["original_notice_members"]) >= 9
    pango=set(plan["versions"]["pango"]["predecessors"])
    assert {"glib","cairo","harfbuzz","fribidi"}<=pango
    assert {"pixman","libXrender"}<=set(plan["versions"]["cairo"]["predecessors"])
    assert {"libXrender","harfbuzz","fribidi"}<=set(plan["remaining_new_catalogue_inputs"])

"""Read-only truthful incompleteness gate for the first interactive Workspace."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "project/graphics-first-workspace/closure.json"


def test_first_workspace_source_graph_is_explicitly_not_ready():
    plan = json.loads(GRAPH.read_text())
    assert plan["schema"] == "zog-first-workspace-source-closure-v1"
    assert plan["status"] == "source-incomplete"
    assert plan["native_accepted"] is False
    assert plan["rights_authorized"] is False
    assert not plan["build_submission_allowed"]
    assert not plan["canonical_promotion_allowed"]
    assert plan["frozen_accepted_generations_required"] == ["fonts", "XCB", "X11"]
    for name in plan["reviewed_source_present"]:
        assert (ROOT / "project/package" / name / "package.py").exists()


def test_turbovnc_server_profile_disables_unselected_surfaces():
    profile = json.loads(GRAPH.read_text())["consumers"]["turbovnc"]
    values = profile["cmake_profile"]
    for name in ("TVNC_BUILDVIEWER", "TVNC_BUILDWEBSERVER",
                 "TVNC_NVCONTROL", "TVNC_BUILDSYSTEMD", "TVNC_DLOPENSSL",
                 "TVNC_ZLIBNG"):
        assert values[name] == "OFF"
    assert values["TVNC_BUILDSERVER"] == values["TVNC_STATIC_XORG_PATHS"] == "ON"
    assert len(profile["must_supply_native_paths"]) == 7
    assert "pixman" in profile["required_capabilities"]
    assert "libjpeg-turbo" in profile["required_capabilities"]
    assert "xkeyboard-config" in profile["required_capabilities"]
    assert "Mesa-GLX" in profile["required_capabilities"]


def test_i3_direct_xcb_and_pango_consumer_edges_are_not_hidden():
    plan = json.loads(GRAPH.read_text())
    deps = set(plan["consumers"]["i3"]["required_pkgconfig"])
    for wanted in ("xcb-cursor", "xcb-icccm", "xcb-xrm",
                   "xcb-xkb", "xcb-xinerama", "xcb-randr",
                   "pangocairo", "cairo", "glib-2.0", "gobject-2.0",
                   "xkbcommon-x11", "yajl", "libpcre2-8"):
        assert wanted in deps
    assert set(("pixman", "pango", "xterm")).issubset(
        set(plan["remaining_source_packages"]))
    assert set(("libev","yajl","startup-notification","libxkbcommon","xkeyboard-config")).issubset(
        set(plan["source_authored_native_held"]))
    assert not set(plan["source_authored_native_held"]).intersection(
        set(plan["remaining_source_packages"]))
    for name in ("i3", "turbovnc"):
        metadata = ast.literal_eval(
            (ROOT / "project/package" / name / "package.py").read_text())
        assert metadata["status"] == "catalogue-only"

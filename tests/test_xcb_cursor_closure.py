"""Source-only XCB renderutil/cursor closure: exact archive and metadata checks."""
import ast
from pathlib import Path

from zog.image_build.metadata import load_packages, order
from zog.image_build.stages import stage_recipes

ROOT = Path(__file__).resolve().parents[1] / "project"
NOTICE = {
    "xcb-util-renderutil": ("0.3.10", "3e15d4f0e22d8ddbfbb9f5d77db43eacd7a304029bf25a6166cc63caa96d04ba",
                           "271169dd66674e9c396697af0b4822d1c59ccd2342b7740864d667a02963068b"),
    "xcb-util-cursor": ("0.1.6", "fdeb8bd127873519be5cc70dcd0d3b5d33b667877200f9925a59fdcad8f7a933",
                        "0dde91ae1d443105dc9e13cbaed6674c36683b7095836ad9ddfce26be270aad5"),
}


def lit(path):
    return ast.literal_eval(path.read_text())


def test_consumer_order_stage_recipes_are_real(tmp_path):
    plan = stage_recipes(ROOT / "bootstrap/graphics-xcb-i3-support.py",
                         ROOT / "package", tmp_path / "recipes")
    all_packages = load_packages(tmp_path / "recipes")
    names = order(all_packages, plan["targets"])
    for predecessor in ("xcb-util-final", "xcb-util-image-final",
                        "xcb-util-renderutil-final"):
        assert names.index(predecessor) < names.index("xcb-util-cursor-final")
    assert all_packages["xcb-util-cursor-final"].build_dependencies == (
        "xcb-util-final", "xcb-util-image-final", "xcb-util-renderutil-final")
    assert all_packages["xcb-util-cursor-final"].runtime_dependencies == (
        "xcb-util-final", "xcb-util-image-final", "xcb-util-renderutil-final")


def test_two_archive_source_identities_and_notice_hashes_exact():
    for name, (version, pinned_sha, copying_sha) in NOTICE.items():
        base = ROOT / "package" / name
        upstream = lit(base / "upstream.py")
        sources = lit(base / "stages/final/sources.py")
        license_record = lit(base / "license.py")
        assert upstream["version"] == version
        assert upstream["sha256"] == pinned_sha
        assert sources[0]["sha256"] == pinned_sha
        assert sources[0]["archive"] is True
        assert license_record["source"]["sha256"] == pinned_sha
        assert license_record["evidence"][0]["path"] == f"{name}-{version}/COPYING"
        assert license_record["evidence"][0]["sha256"] == copying_sha
        assert all(x["source_sha256"] == pinned_sha for x in license_record["evidence"])
        assert license_record["components"][0]["status"] == "unresolved"
        assert lit(base / "package.py")["status"] == "catalogue-only"


def test_native_generation_not_spoofed_by_source_recipe():
    for name, (_, _, notice_sha) in NOTICE.items():
        base = ROOT / "package" / name
        build = lit(base / "stages/final/build.py")
        manifest = lit(base / "stages/final/produce-manifest.py")
        assert manifest["trees"] == ["usr"]
        assert len(manifest["required"]) == 1
        assert "COPYING" in build["install"][0][-1]
        assert "test -n \"$DESTDIR\"" in build["install"][0][-1]
        assert "--disable-static" in build["configure"][0][-1]
        assert build["build"][0][-1].endswith("make -j8")
        integration = lit(base / "stages/final/integration.py")
        assert "No Host fallbacks" in integration["base_contract"]
        assert "No native compiler" in integration["dependency_review"]["selected_build"]

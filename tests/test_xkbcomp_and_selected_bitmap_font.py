"""Verify original xkbcomp and 6x13 font source, never installed Host bytes."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load
ROOT=Path(__file__).resolve().parents[1]/"project/package"
def lit(p):return ast.literal_eval(p.read_text())
def test_xkbcomp_source_notice_and_inherited_dependencies():
    root=ROOT/"xkbcomp"
    source=lit(root/"stages/final/sources.py")[0]
    rights=load(root/"license.py",[source])
    assert source["sha256"]=="2ac31f26600776db6d9cd79b3fcd272263faebac7eb85fb2f33c7141b8486060"
    assert rights["evidence"][0]["sha256"]=="6b833fdc05906ce57f016dc791db86830d49ee4da2861ce45806c50b3f4dda9e"
    assert rights["components"][0]["status"]=="unresolved"
    assert lit(root/"package.py")["status"]=="catalogue-only"
    assert "usr/bin/xkbcomp" in load_package(root/"stages/final").outputs
    assert "libxkbfile-final" in lit(root/"stages/final/dependencies.py")["build"]
def test_font_member_source_sha_independently_observed():
    x=lit(ROOT/"basic-font/stages/final/integration.py")["original_selected_font_member"]
    assert x["path"]=="font-misc-misc-1.1.3/6x13.bdf"
    assert x["sha256"]=="c68c55ca8effcdc2714fffa9c8e07df290411867b00b547eeae952f7473efc9b"

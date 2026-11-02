"""Source-only first Workspace package DAG from actual package stage declarations.

The test rejects internal cycles, unsupported source package references and
silently promoted leaves. Missing XKB compiler and Mesa remain deliberate holds.
"""
import ast
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]/"project"
PACKAGE=ROOT/"package"
DRAFT=ROOT/"graphics-first-workspace/turbovnc-draft"
TARGETS=("i3","xterm","turbovnc")
EXTERNAL_GATED={"mesa"}  # Exact immutable candidate remains in PR #8 only.
SOURCE_NOT_YET_AUTHORED=set()
SELECTED={
    "i3","xterm","turbovnc",
    "libev","yajl","startup-notification","libxkbcommon",
    "xkeyboard-config","glib","cairo","pango","harfbuzz",
    "fribidi","libXrender","libXaw","libXmu","libXpm",
    "libXft","luit","basic-font","bdftopcf","mkfontscale",
    "pixman","libjpeg-turbo","xkbcomp",
}
def literal(path):
    return ast.literal_eval(path.read_text())
def stage_dir(package):
    return DRAFT/"stages/final" if package=="turbovnc" else PACKAGE/package/"stages/final"

def source_order():
    ordered=[]
    visiting=set()
    visited=set()
    missing=set()
    def visit(name):
        if name in EXTERNAL_GATED:
            missing.add(name)
            return
        if name in SOURCE_NOT_YET_AUTHORED:
            missing.add(name)
            return
        directory=stage_dir(name)
        if not directory.is_dir():
            raise AssertionError("undeclared graphics dependency: "+name)
        if name in visiting:
            raise AssertionError("graphics source cycle: "+name)
        if name in visited:
            return
        visiting.add(name)
        dependency=literal(directory/"dependencies.py")
        for ref in dependency["build"]:
            assert ref.endswith("-final"),(name,ref)
            child=ref[:-6]
            if child in SELECTED:
                visit(child)
            elif child in EXTERNAL_GATED or child in SOURCE_NOT_YET_AUTHORED:
                missing.add(child)
            else:
                assert (PACKAGE/child/"stages/final").is_dir(), (
                    name, "unknown or Host-only dependency", ref)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)
    for target in TARGETS:
        visit(target)
    return ordered,missing

def test_exact_graph_source_stages_are_acyclic_and_hold_unadmitted_external_inputs():
    order,missing=source_order()
    assert missing=={"mesa"}
    for target in TARGETS:
        assert order.index(target)>0
    for leaf,root in (("harfbuzz","pango"),("fribidi","pango"),
                      ("pango","i3"),("cairo","i3"),("glib","i3"),
                      ("libXrender","cairo"),("libXaw","xterm"),
                      ("luit","xterm"),("basic-font","xterm"),
                      ("pixman","turbovnc"),("libjpeg-turbo","turbovnc")):
        assert order.index(leaf)<order.index(root)
    for name in SELECTED:
        assert literal((DRAFT if name=="turbovnc" else PACKAGE/name)/"package.py")["status"]=="catalogue-only"

def test_core_graphical_meson_and_cmake_source_profiles_deny_automatic_fallback():
    for name in ("glib","cairo","pango","i3"):
        build=literal(stage_dir(name)/"build.py")["configure"][0][-1]
        assert "PKG_CONFIG_LIBDIR" in build
        assert "--wrap-mode=nodownload" in build
        assert "-Dauto_features=disabled" in build
    xvnc=literal(stage_dir("turbovnc")/"build.py")["configure"][0][-1]
    assert "PKG_CONFIG_LIBDIR" in xvnc
    assert "-DTVNC_DRI3=OFF" in xvnc
    assert "-DTVNC_BUILDVIEWER=OFF" in xvnc

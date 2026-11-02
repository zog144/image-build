"""Source-only first Workspace package DAG from actual package stage declarations.

The test rejects internal cycles, unsupported source package references and
silently promoted leaves. Mesa remains a separate immutable candidate; inherited nonfinal stages are explicitly bound.
"""
import ast
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]/"project"
PACKAGE=ROOT/"package"
DRAFT=ROOT/"graphics-first-workspace/turbovnc-draft"
TARGETS=("i3","xterm","turbovnc")
EXTERNAL_GATED={"mesa"}  # Exact immutable candidate remains in PR #8 only.
INHERITED_NONFINAL={"zlib":"native-environment","ncurses":"temporary"}
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

def source_order(*, overrides=None):
    """Walk real selected package source stages and their runtime-only edges.

    Overrides are for adversarial unit fixtures, never the production graph.
    """
    overrides = overrides or {}
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
        dependency=overrides.get(name, literal(directory/"dependencies.py"))
        for ref in dict.fromkeys(dependency["build"] + dependency["runtime"]):
            if ref in {"zlib-native-environment", "ncurses-temporary"}:
                child,stage=(("zlib","native-environment") if ref=="zlib-native-environment"
                             else ("ncurses","temporary"))
                assert INHERITED_NONFINAL[child]==stage
                assert (PACKAGE/child/"stages"/stage/"sources.py").is_file(), (
                    name, "missing inherited Zog source provenance", ref)
                missing.add(child + ":" + stage + ":inherited-accepted-generation")
                continue
            assert ref.endswith("-final"),(name,ref)
            child=ref[:-6]
            if child in SELECTED:
                visit(child)
            elif child in EXTERNAL_GATED:
                missing.add(child)
            else:
                assert (PACKAGE/child/"stages/final").is_dir(), (
                    name, "unknown or Host-only dependency", ref)
                # An unselected package may be a valid pre-existing stage,
                # but its exact input must exist; no host library substitution.
                assert (PACKAGE/child/"stages/final/sources.py").is_file(), (
                    name, "missing predecessor original sources", ref)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)
    for target in TARGETS:
        visit(target)
    return ordered,missing

def test_exact_graph_source_stages_are_acyclic_and_hold_unadmitted_external_inputs():
    order,missing=source_order()
    assert missing=={"mesa", "zlib:native-environment:inherited-accepted-generation", "ncurses:temporary:inherited-accepted-generation"}
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


def test_negative_missing_inherited_stage_refusal():
    original=literal(stage_dir("xterm")/"dependencies.py")
    broken={**original,"build":[r.replace("ncurses-temporary","ncurses-final") for r in original["build"]]}
    with pytest.raises(AssertionError,match="unknown or Host-only dependency"):
        source_order(overrides={"xterm":broken})


def test_negative_missing_selected_predecessor_and_cycle():
    original=literal(stage_dir("i3")/"dependencies.py")
    missing={**original,"build":original["build"]+["unreviewed-host-headers-final"]}
    with pytest.raises(AssertionError,match="unknown or Host-only dependency"):
        source_order(overrides={"i3":missing})
    cyclic={**original,"build":original["build"]+["i3-final"]}
    with pytest.raises(AssertionError,match="graphics source cycle"):
        source_order(overrides={"i3":cyclic})


def test_negative_generated_headers_and_installed_resources_are_not_omitted():
    expected={
      "i3": {"usr/bin/i3","usr/bin/i3bar","usr/share/licenses/i3/LICENSE"},
      "xterm": {"usr/bin/xterm","usr/share/X11/app-defaults/XTerm",
                "usr/share/terminfo/x/xterm"},
      "basic-font": {"usr/share/fonts/X11/misc/6x13.pcf.gz",
                     "usr/share/fonts/X11/misc/fonts.dir"},
      "turbovnc": {"usr/bin/Xvnc","usr/bin/vncserver",
                   "usr/share/licenses/turbovnc/Xserver-COPYING"},
    }
    for name,paths in expected.items():
        manifest=literal(stage_dir(name)/"produce-manifest.py")
        assert paths.issubset(set(manifest["required"])), name
    i3=literal(stage_dir("i3")/"build.py")
    assert "build-i3/config.h" in i3["test"][0][-1]
    xvnc=literal(stage_dir("turbovnc")/"build.py")
    assert "-DXKB_BIN_DIRECTORY=/usr/bin" in xvnc["configure"][0][-1]
    assert "xkbcomp-final" in literal(stage_dir("turbovnc")/"dependencies.py")["build"]


def test_no_host_binary_or_pkgconfig_fallback_can_be_approved_from_source():
    for name in ("i3","cairo","glib","pango","turbovnc"):
        script=literal(stage_dir(name)/"build.py")["configure"][0][-1]
        assert "PKG_CONFIG_LIBDIR" in script
        assert name=="turbovnc" or "--wrap-mode=nodownload" in script
    graph=__import__("json").loads((ROOT/"graphics-first-workspace/closure.json").read_text())
    assert graph["native_accepted"] is False
    assert graph["rights_authorized"] is False
    assert graph["build_submission_allowed"] is False
    assert graph["canonical_promotion_allowed"] is False
    for required in ("zlib","ncurses"):
        assert any(required in x for x in graph["source_only_dag_hold"])


def verify_order(order, *, overrides=None):
    """Verify reported ordering independently of DFS traversal."""
    overrides=overrides or {}
    if len(order)!=len(set(order)):
        raise AssertionError("duplicate stage in proposed package order")
    positions={name:i for i,name in enumerate(order)}
    for name in order:
        deps=overrides.get(name,literal(stage_dir(name)/"dependencies.py"))
        for ref in dict.fromkeys(deps["build"]+deps["runtime"]):
            if ref.endswith("-final"):
                child=ref[:-6]
                if child in SELECTED and (child not in positions or positions[child]>=positions[name]):
                    raise AssertionError("incorrect package ordering or missing predecessor: "+ref)
            elif ref in ("zlib-native-environment","ncurses-temporary"):
                continue
            else:
                raise AssertionError("unexpected unreviewed stage identity: "+ref)
    return True

def test_adversarial_package_order_and_missing_runtime_predecessor_denied():
    order,_=source_order()
    assert verify_order(order)
    with pytest.raises(AssertionError,match="incorrect package ordering"):
        verify_order(order[::-1])
    with pytest.raises(AssertionError,match="missing predecessor"):
        verify_order([x for x in order if x!="xkbcomp"])
    with pytest.raises(AssertionError,match="duplicate stage"):
        verify_order(order+["i3"])

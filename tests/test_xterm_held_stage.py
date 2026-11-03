"""Exact source-only xterm stage and deliberate missing-library hold."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load

ROOT = Path(__file__).resolve().parents[1]/"project/package/xterm"
def lit(p):
    return ast.literal_eval((ROOT/p).read_text())

def test_xterm_configure_install_and_resources_use_original_release():
    source=lit("stages/final/sources.py")[0]
    assert source["sha256"]=="b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6"
    assert source["archive"] is True
    record=load(ROOT/"license.py",[source])
    assert record["components"][0]["status"]=="unresolved"
    stage=load_package(ROOT/"stages/final")
    assert stage.sources == (source,)
    outputs=set(lit("stages/final/produce-manifest.py")["required"])
    assert {"usr/bin/xterm","usr/share/X11/app-defaults/XTerm","usr/share/terminfo/x/xterm"}<=outputs
    commands=lit("stages/final/build.py")
    configure=commands["configure"][0][-1]
    assert "--disable-setuid" in configure and "--disable-setgid" in configure
    assert "--with-app-defaults=/usr/share/X11/app-defaults" in configure
    install=commands["install"][0][-1]
    assert "test -n" in install and "DESTDIR" in install
    assert 'make DESTDIR="$DESTDIR" install-ti' in install
    assert 'usr/share/licenses/xterm/COPYING' in install

def test_xterm_source_authored_but_selected_dependencies_still_missing():
    deps=lit("stages/final/dependencies.py")
    assert set(("libXaw-final","libXmu-final","libXpm-final","libXft-final")).issubset(deps["build"])
    assert {"luit-final","basic-font-final"}.issubset(deps["runtime"])
    assert "HOLD:" in lit("stages/final/integration.py")["native_admission"]
    assert lit("package.py")["status"]=="catalogue-only"

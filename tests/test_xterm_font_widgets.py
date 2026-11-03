"""Source-pinned xterm widget libraries and exact minimal bitmap font pipeline."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load as load_license
ROOT=Path(__file__).resolve().parents[1]/"project/package"
NAMES=("libXaw","libXmu","libXpm","libXft","mkfontscale","basic-font")
def lit(x):return ast.literal_eval(x.read_text())
def test_all_xterm_predecessor_stage_contracts_stay_source_only():
    for name in NAMES:
        r=ROOT/name
        source=lit(r/"stages/final/sources.py")[0]
        record=load_license(r/"license.py",[source])
        assert record["source"]["sha256"]==source["sha256"]
        assert all(x["source_sha256"]==source["sha256"] for x in record["evidence"])
        assert record["components"][0]["status"]=="unresolved"
        assert lit(r/"package.py")["status"]=="catalogue-only"
        assert load_package(r/"stages/final").outputs
        assert 'test -n "' in lit(r/"stages/final/build.py")["install"][0][-1]
        assert "HOLD" in lit(r/"stages/final/integration.py")["native_admission"]
def test_widget_library_and_font_tools_order():
    assert "libXmu-final" in lit(ROOT/"libXaw/stages/final/dependencies.py")["build"]
    assert "libXpm-final" in lit(ROOT/"libXaw/stages/final/dependencies.py")["build"]
    assert "libXrender-final" in lit(ROOT/"libXft/stages/final/dependencies.py")["build"]
    font=lit(ROOT/"basic-font/stages/final/build.py")
    assert "bdftopcf" in font["build"][0][-1]
    assert "mkfontscale" in font["build"][0][-1]
    assert "gzip -n" in font["build"][0][-1]
    assert "bdftopcf-final" in lit(ROOT/"basic-font/stages/final/dependencies.py")["build"]
    assert "mkfontscale-final" in lit(ROOT/"basic-font/stages/final/dependencies.py")["build"]

"""Read-only original luit and bdftopcf releases; no Host fallback."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load
ROOT=Path(__file__).resolve().parents[1]/"project/package"
PINS={"luit":("30b0e787cb07a0f504b70f1d6123930522111ce9d4276f6683a69b322b49c636","20b6a1481d9dafeaa471e2ac497ecc651428e8369cc935b5bd9d0e5b77d78081"),"bdftopcf":("bc60be5904330faaa3ddd2aed7874bee2f29e4387c245d6787552f067eb0523a","a437fb5272ba507c2977b2ef623bb391270f521b2a20271ed044785f4eaa5dbc")}
def lit(p):return ast.literal_eval(p.read_text())
def test_luit_and_bitmap_compiler_exact_source():
    for name,(src,rights_sha) in PINS.items():
        folder=ROOT/name
        source=lit(folder/"stages/final/sources.py")[0]
        record=load(folder/"license.py",[source])
        assert source["sha256"]==src
        assert record["evidence"][0]["sha256"]==rights_sha
        assert record["components"][0]["status"]=="unresolved"
        assert lit(folder/"package.py")["status"]=="catalogue-only"
        stage=load_package(folder/"stages/final")
        assert stage.sources==(source,)
        assert "usr/bin/"+name in stage.outputs
        assert 'test -n "' in lit(folder/"stages/final/build.py")["install"][0][-1]

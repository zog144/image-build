"""Reviewed font shaping/bidi/Xrender source-stage ordering and boundaries."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load as load_license
ROOT=Path(__file__).resolve().parents[1]/"project/package"
SOURCE={
"harfbuzz":("11.5.0","2d30ba45c4c8ec4de661a1002b4f88d0841ff1a3087f34629275f5436d722109","ba8f810f2455c2f08e2d56bb49b72f37fcf68f1f4fade38977cfd7372050ad64"),
"fribidi":("1.0.16","1b1cde5b235d40479e91be2f0e88a309e3214c8ab470ec8a2744d82a5a9ea05c","32434afcc8666ba060e111d715bfdb6c2d5dd8a35fa4d3ab8ad67d8f850d2f2b"),
"libXrender":("0.9.12","b832128da48b39c8d608224481743403ad1691bf4e554e4be9c174df171d1b97","bbe1db89c48816c48248796adac91defd8fbde1141b145f01511781ab87f29a1")}
def lit(p):return ast.literal_eval(p.read_text())
def test_exact_original_archive_license_bound_and_native_unaccepted():
    for name,(version,sha,rights_sha) in SOURCE.items():
        root=ROOT/name
        source=lit(root/"stages/final/sources.py")[0]
        license_record=load_license(root/"license.py",[source])
        assert source["sha256"]==sha
        assert lit(root/"upstream.py")["version"]==version
        assert license_record["evidence"][0]["sha256"]==rights_sha
        assert license_record["components"][0]["status"]=="unresolved"
        assert lit(root/"package.py")["status"]=="catalogue-only"
        item=load_package(root/"stages/final")
        assert item.sources==(source,)
        assert item.outputs and item.output_trees==("usr",)
        build=lit(root/"stages/final/build.py")
        assert 'test -n "$DESTDIR"' in build["install"][0][-1]
        assert "licenses/"+name+"/COPYING" in build["install"][0][-1]
        assert "HOLD" in lit(root/"stages/final/integration.py")["native_admission"]
def test_font_deps_avoid_glib_cairo_cycles_and_no_host_subprojects():
    text=lit(ROOT/"harfbuzz/stages/final/build.py")["configure"][0][-1]
    for flag in ("-Dglib=disabled","-Dcairo=disabled","-Dfreetype=disabled","-Dutilities=disabled","--wrap-mode=nodownload"):
        assert flag in text
    assert lit(ROOT/"harfbuzz/stages/final/dependencies.py")["build"]==[]
    assert lit(ROOT/"fribidi/stages/final/dependencies.py")["build"]==[]
    assert lit(ROOT/"libXrender/stages/final/dependencies.py")["build"]==["libX11-final","xorgproto-final"]

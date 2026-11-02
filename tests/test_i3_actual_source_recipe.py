"""Actual i3 4.25.1 source-only Meson profile, dependency closure and license binding."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load as rights
ROOT=Path(__file__).resolve().parents[1]/"project/package/i3"
def lit(n):return ast.literal_eval((ROOT/n).read_text())

def test_i3_stage_is_metadata_loadable_and_native_held():
    source=lit("stages/final/sources.py")[0]
    assert source["sha256"]=="4a742bbe81b9e5ee6057f42a8e3c691d88894e93f1a5d81fe239128512ac05c0"
    stage=load_package(ROOT/"stages/final")
    assert stage.sources==(source,)
    license_record=rights(ROOT/"license.py",[source])
    assert license_record["status"]=="declared"
    assert license_record["evidence"][0]["sha256"]=="cefa5e57afbfcdc39cdf3434d6d9381216ba015d4a0768ad87e358f78ea3733e"
    assert license_record["components"][0]["status"]=="unresolved"
    assert lit("package.py")["status"]=="catalogue-only"
    assert stage.output_trees==("usr",)
    assert "usr/bin/i3" in stage.outputs and "usr/bin/i3bar" in stage.outputs
    assert lit("stages/final/integration.py")["native_admission"].startswith("HOLD")
def test_meson_pkgconf_sources_and_generated_header_requirements():
    integration=lit("stages/final/integration.py")
    deps=lit("stages/final/dependencies.py")
    build=lit("stages/final/build.py")
    command=build["configure"][0][-1]
    assert "pkgconf --exists " + " ".join(integration["required_pkgconfig"]) in command
    for pkg in ("pangocairo","glib-2.0","gobject-2.0","xkbcommon-x11","libstartup-notification-1.0"):
        assert pkg in integration["required_pkgconfig"]
    for source in ("pango-final","cairo-final","glib-final","fribidi-final"):
        if source=="fribidi-final":
            assert source in __import__("ast").literal_eval((ROOT.parent/"pango/stages/final/dependencies.py").read_text())["build"]
        else:
            assert source in deps["build"]
    assert "-Ddocs=false" in command and "-Dmans=false" in command
    assert "--wrap-mode=nodownload" in command
    assert "-Dauto_features=disabled" in command
    assert "PKG_CONFIG_LIBDIR" in command and "ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION" in command
    assert "build-i3/config.h" in build["test"][0][-1]

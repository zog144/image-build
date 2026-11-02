"""Never admit a TurboVNC Xvnc source draft as an installed server."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
ROOT=Path(__file__).resolve().parents[1]/"project/graphics-first-workspace/turbovnc-draft"
def lit(p):return ast.literal_eval((ROOT/p).read_text())

def test_server_only_build_profile_exact_flags():
    source=lit("stages/final/sources.py")[0]
    assert source["sha256"]=="9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"
    stage=load_package(ROOT/"stages/final")
    assert stage.sources==(source,)
    build=lit("stages/final/build.py")
    flags=build["configure"][0][-1]
    for wanted in ("-DTVNC_BUILDSERVER=ON","-DTVNC_BUILDVIEWER=OFF",
                   "-DTVNC_BUILDWEBSERVER=OFF","-DTVNC_NVCONTROL=OFF",
                   "-DTVNC_BUILDSYSTEMD=OFF","-DTVNC_STATIC_XORG_PATHS=ON",
                   "-DTVNC_ZLIBNG=OFF","-DTJPEG_LIBRARY=/usr/lib/libturbojpeg.so"):
        assert wanted in flags
    assert 'test -n "$ZOG_GRAPHICAL_TOOLCHAIN_ATTESTATION"' in flags
    assert 'test -n "$DESTDIR"' in build["install"][0][-1]
    assert set(("usr/bin/Xvnc","usr/bin/vncserver","usr/bin/vncpasswd"))<=set(lit("stages/final/produce-manifest.py")["required"])

def test_bundled_license_bytes_and_native_go_decision_are_held():
    rights=lit("license.py")
    assert rights["status"]=="unresolved"
    assert len(rights["evidence"])==4
    assert all(x["source_sha256"]==rights["source"]["sha256"] for x in rights["evidence"])
    assert all(x["status"]=="unresolved" for x in rights["components"])
    assert lit("package.py")["status"]=="catalogue-only"
    assert lit("stages/final/integration.py")["native_admission"].startswith("HOLD:")
    deps=lit("stages/final/dependencies.py")
    assert "libjpeg-turbo-final" in deps["build"]
    assert "pixman-final" in deps["build"]
    assert "mesa-final" in deps["runtime"]

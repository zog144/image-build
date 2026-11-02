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


def test_xvnc_selected_xserver_linker_profile_excludes_hardware_dri3():
    flags=lit("stages/final/build.py")["configure"][0][-1]
    assert "-DTVNC_DRI3=OFF" in flags
    assert "-DTVNC_ZLIBNG=OFF" in flags
    assert 'pkgconf --exists xfont2 pixman-1 x11 xau xdmcp xkbfile gl zlib' in flags
    assert "PKG_CONFIG_LIBDIR" in flags and "CMAKE_PREFIX_PATH" in flags
    deps=lit("stages/final/dependencies.py")
    for target in ("libXfont2-final","xkbcomp-final","mesa-final","zlib-native-environment","openssl-final"):
        assert target in deps["build"]
    integration=lit("stages/final/integration.py")
    assert "bundled Xorg" in integration["native_admission"]
    assert "xkbcomp" in integration["missing_native_predecessor"]
    assert integration["selected_bundled_originals"]["Xserver/COPYING"] == (
        "4cc0447a22635c7b2f1a93fec4aa94f1970fadeb72a063de006b51cf4963a06f")


def test_cmake_auth_and_feature_scope_reject_default_pam_and_ambiguous_tls():
    configure=lit("stages/final/build.py")["configure"][0][-1]
    assert "-DTVNC_USETLS=OpenSSL" in configure
    assert "-DTVNC_USETLS=1" not in configure
    assert "-DTVNC_USEPAM=OFF" in configure
    assert "-DTVNC_DRI3=OFF" in configure
    assert "-DTVNC_ZLIBNG=OFF" in configure
    assert "-DTVNC_NVCONTROL=OFF" in configure
    assert "-DTVNC_BUILDVIEWER=OFF" in configure
    assert "-DTVNC_BUILDWEBSERVER=OFF" in configure
    assert "-DTVNC_BUILDSYSTEMD=OFF" in configure
    assert "-DTVNC_DLOPENSSL=OFF" in configure
    assert "pkgconf --exists" in configure
    integ=lit("stages/final/integration.py")
    assert integ["selected_cmake_sources_sha256"]["unix/Xvnc/programs/Xserver/CMakeLists.txt"] == (
        "4e52b66d996039bb1450690cc694691670c8f5c4cad387d8f057eeaa28feede4")
    assert integ["source_exclusion_observations"]["device_access"].startswith("GLX swrast")

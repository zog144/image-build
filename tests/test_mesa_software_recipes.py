"""Source-only contracts: LLVM X86, Mesa llvmpipe/GLX, mesa-demos smoke.

Never claims native configure/compilation or complete redistribution rights.
"""
import ast
from pathlib import Path

import pytest


PROJECT = Path(__file__).resolve().parents[1] / "project"
NAMES = ("llvm", "mesa", "mesa-demos")
HASHES = {
    "llvm": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad",
    "mesa": "0fd54fea7dbbddb154df05ac752b18621f26d97e27863db3be951417c6abe8ae",
    "mesa-demos": "3046a3d26a7b051af7ebdd257a5f23bfeb160cad6ed952329cdff1e9f1ed496b",
}


def lit(path):
    return ast.literal_eval(path.read_text())


def stage(name, part):
    return lit(PROJECT / "graphics-drafts" / name / "stages" / "final" / part)


@pytest.mark.parametrize("name", NAMES)
def test_exact_archive_and_supplementary_pin_agree_without_boot_input_mutation(name):
    package = PROJECT / "graphics-drafts" / name
    status = lit(package / "package.py")
    upstream = lit(package / "upstream.py")
    inputs = stage(name, "sources.py")
    notice = lit(package / "license.py")
    source_pin = lit(PROJECT / "pins/2026-11-01/graphics-source-pin.py")
    assert source_pin["scope"] == "first-workspace-graphics-only"
    assert source_pin["status"].startswith("supplementary-source-review-only")
    assert status["status"] == "catalogue-only"
    assert status["recipe_status"] == "drafted-final-stage-native-held"
    assert upstream["sha256"] == HASHES[name]
    assert len(inputs) == 1
    assert inputs[0] == source_pin["packages"][name]["recipes"][f"{name}/stages/final"][0]
    assert inputs[0]["sha256"] == upstream["sha256"] == HASHES[name]
    assert inputs[0]["url"] == upstream["release_url"]
    assert upstream["version"] == notice["version"] == source_pin["packages"][name]["version"]
    assert notice["status"] == "unresolved"
    assert "component rights" in notice["scope"]
    assert notice["source"] == {"url": upstream["release_url"], "sha256": HASHES[name]}
    assert notice["evidence"] and all(len(item["sha256"]) == 64 for item in notice["evidence"])
    assert all(item["source_sha256"] == HASHES[name] for item in notice["evidence"])
    assert "Selected upstream rights members:" in notice["notes"][-1]
    assert notice["components"][0]["status"] == "unresolved"
    # A source draft is not discoverable as a compiled/admitted package.
    assert not (PROJECT / "package" / name).exists()


def test_gallium_dependency_graph_is_exact_and_non_host_fallback():
    llvm = stage("llvm", "dependencies.py")
    mesa = stage("mesa", "dependencies.py")
    demo = stage("mesa-demos", "dependencies.py")
    assert "llvm-final" in mesa["build"] and "llvm-final" in mesa["runtime"]
    assert "libdrm-final" in mesa["build"]
    assert "libxshmfence-final" in mesa["build"]
    assert "libXxf86vm-final" in mesa["build"]
    for name in ("libX11-final", "libXext-final", "libxcb-final"):
        assert name in mesa["build"]
    assert "mesa-final" in demo["build"] and "mesa-final" in demo["runtime"]
    assert llvm["build"] == ["zlib-native-environment"]
    for name in NAMES:
        integration = stage(name, "integration.py")
        assert integration["native_admission"].startswith("HOLD")
        assert integration["unresolved"]
        assert "zero unpinned host libraries" in integration["base_contract"]


def test_llvm_jit_and_mesa_software_glx_feature_contract():
    llvm = stage("llvm", "build.py")
    mesa = stage("mesa", "build.py")
    lc = llvm["configure"][0][-1]
    mc = mesa["configure"][0][-1]
    assert "-DLLVM_TARGETS_TO_BUILD=X86" in lc
    assert "-DLLVM_BUILD_LLVM_DYLIB=ON" in lc
    assert "-DLLVM_ENABLE_RTTI=ON" in lc
    assert "-DLLVM_ENABLE_PROJECTS=" in lc
    assert "--parallel 2" in llvm["build"][0][-1]
    assert "llvm-config --version" in mc
    assert "llvm-config --shared-mode" in mc
    assert "llvm-config --has-rtti" in mc
    for option in (
        "-Dplatforms=x11", "-Dgallium-drivers=swrast", "-Dglx=dri",
        "-Dllvm=enabled", "-Dshared-llvm=enabled",
        "-Dvulkan-drivers=", "-Dgbm=disabled", "-Degl=disabled",
        "-Dglvnd=disabled", "-Dauto_features=disabled",
    ):
        assert option in mc
    assert "-Ddri3=" not in mc  # removed from Mesa 25.3.0 Meson options
    assert "-Dgallium-drivers=auto" not in mc
    assert "radeonsi" not in mc and "iris" not in mc
    assert "/dev/dri" not in mc
    assert "libdrm" in mc
    assert "pkg-config --exists x11 xext x11-xcb xcb xcb-randr xcb-glx xcb-shm xcb-dri3 xcb-present xcb-sync xcb-xfixes xshmfence xxf86vm libdrm expat zlib" in mc


def test_demo_does_not_depend_on_host_binaries_or_broad_gpu_suite():
    commands = stage("mesa-demos", "build.py")
    assert "glxgears glxinfo" in commands["build"][0][-1]
    assert "pkg-config --exists gl glx x11 xext" in commands["configure"][0][-1]
    assert "DESTDIR" in commands["install"][0][-1]
    assert "install -Dm755" in commands["install"][0][-1]
    text = str(commands)
    assert "apt " not in text and "dnf " not in text
    assert "-Dvulkan=disabled" in commands["configure"][0][-1]
    assert "glxgears" in commands["build"][0][-1]
    for name in NAMES:
        script = str(stage(name, "build.py"))
        assert "curl " not in script and "wget " not in script
        assert "sudo " not in script
        assert "glxgears -benchmark" not in script


def test_only_glxgears_runtime_smoke_remains_native():
    doc = (PROJECT.parent / "docs/image-build/mesa-llvmpipe-source-contract.md").read_text()
    assert "Xvnc" in doc and "glxgears" in doc
    assert "No FPS minimum" in doc
    assert "No /dev/dri" not in doc  # documentation explains separately that no device is granted
    assert "Basic/console-first" in doc


def test_exact_source_pins_for_direct_glx_dependencies():
    pin = lit(PROJECT / "pins/2026-11-01/graphics-source-pin.py")
    for name, ver, sha in (
        ("libxshmfence", "1.3.3", "d4a4df096aba96fea02c029ee3a44e11a47eb7f7213c1a729be83e85ec3fde10"),
        ("libXxf86vm", "1.1.7", "ae50c0f669e0af5a67cc4cd0f54f21d64a64d2660af883e80e95d3fe51b945d8"),
    ):
        item = pin["packages"][name]
        assert item["version"] == ver
        assert item["source"]["sha256"] == sha
        assert stage(name, "sources.py")[0]["sha256"] == sha
        assert not (PROJECT / "package" / name).exists()


def test_original_xxf86vm_pkgconfig_install_and_complete_llvm_target_graph():
    xxf = stage("libXxf86vm", "produce-manifest.py")
    assert xxf["required"][:2] == ["usr/lib/libXxf86vm.so", "usr/lib/pkgconfig/xxf86vm.pc"]
    assert "usr/share/licenses/libXxf86vm/COPYING" in xxf["required"]
    assert "xf86vmode.h" not in str(xxf)
    llvm = stage("llvm", "build.py")
    assert llvm["build"][0][-1].splitlines() == [
        "cmake --build build-llvm --target llvm-tblgen --parallel 2",
        "cmake --build build-llvm --parallel 2",
    ]
    assert "test -x build-llvm/bin/llvm-tblgen" in llvm["test"][0][-1]
    assert 'install -Dm755 build-llvm/bin/llvm-tblgen' in llvm["install"][0][-1]
    assert "usr/bin/llvm-tblgen" in stage("llvm", "produce-manifest.py")["required"]
    assert "test -x /usr/bin/llvm-tblgen" in stage("mesa", "build.py")["configure"][0][-1]
    assert "llvm-config --has-rtti" in stage("mesa", "build.py")["configure"][0][-1]


def test_canonical_admission_is_explicitly_held_pending_real_closure():
    import json
    plan = json.loads((PROJECT / "graphics-drafts/admission-plan.json").read_text())
    assert plan["schema"] == "image-build-first-workspace-graphics-canonical-admission-v1"
    assert plan["status"] == "source-prepared-native-and-rights-NO-GO"
    assert plan["source_pin_contract"] == "supplementary-review-only-not-canonical"
    assert plan["immutable_publication"] == "applications-v1"
    assert plan["intended_stage_order"] == [
        "llvm-final", "libdrm-final", "libxshmfence-final",
        "libXxf86vm-final", "mesa-final", "mesa-demos-final",
    ]
    assert {p["name"] for p in plan["blocked_python_build_inputs"]} == {
        "mako-final", "pyyaml-final",
    }
    assert len(plan["required_acceptance"]) == 6
    assert any("glxgears" in item for item in plan["required_acceptance"])
    assert all(not (PROJECT / "package" / name).exists()
               for name in ("llvm", "libdrm", "libxshmfence",
                            "libXxf86vm", "mesa", "mesa-demos"))
    assert (PROJECT / "package/libX11/stages/final/produce-manifest.py").exists()
    x11 = lit(PROJECT / "package/libX11/stages/final/produce-manifest.py")
    assert "usr/lib/libX11-xcb.so" in x11["required"]
    assert (PROJECT / "package/libxcb/stages/final/produce-manifest.py").exists()


def test_real_inherited_zlib_source_stage_remains_frozen_input_not_host_fallback():
    inherited = PROJECT/"package/zlib/stages/native-environment"
    assert (inherited/"sources.py").is_file()
    assert not (PROJECT/"package/zlib/stages/final").is_dir()
    for name in ("llvm","mesa"):
        record=stage(name,"dependencies.py")
        assert "zlib-native-environment" in record["build"]
        assert "zlib-final" not in record["build"]

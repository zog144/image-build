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
    assert notice["status"] == "archive-member-hashes-verified-rights-review-pending"
    assert notice["source"] == {"url": upstream["release_url"], "sha256": HASHES[name]}
    assert notice["evidence"] and all(len(item["sha256"]) == 64 for item in notice["evidence"])
    assert notice["required_original_notice_paths"]
    assert notice["components"][0]["status"] == "unresolved"
    # A source draft is not discoverable as a compiled/admitted package.
    assert not (PROJECT / "package" / name).exists()


def test_gallium_dependency_graph_is_exact_and_non_host_fallback():
    llvm = stage("llvm", "dependencies.py")
    mesa = stage("mesa", "dependencies.py")
    demo = stage("mesa-demos", "dependencies.py")
    assert "llvm-final" in mesa["build"] and "llvm-final" in mesa["runtime"]
    assert "libdrm-final" in mesa["build"]
    for name in ("libX11-final", "libXext-final", "libxcb-final"):
        assert name in mesa["build"]
    assert "mesa-final" in demo["build"] and "mesa-final" in demo["runtime"]
    assert llvm["build"] == ["zlib-final"]
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


def test_demo_does_not_depend_on_host_binaries_or_broad_gpu_suite():
    commands = stage("mesa-demos", "build.py")
    assert "glxgears glxinfo" in commands["build"][0][-1]
    assert "pkg-config --exists gl x11 xext" in commands["configure"][0][-1]
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

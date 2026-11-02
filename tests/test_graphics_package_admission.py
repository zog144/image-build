"""Exact-source Mesa graphical draft admission checks.

The canonical loader and licensing schema must accept draft *metadata*.
Actual producer admission remains blocked, including when source CI passes.
"""
import ast
import json
from pathlib import Path
import pytest
from zog.image_build.metadata import load_package, literal
from zog.image_build.licensing import validate as validate_license

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "project/graphics-drafts"
CANONICAL = ROOT / "project/package"
SIX = ("llvm", "libdrm", "libxshmfence", "libXxf86vm", "mesa", "mesa-demos")


@pytest.mark.parametrize("name", SIX)
def test_draft_stage_passes_actual_package_and_licensing_parsers(name):
    folder = DRAFT / name / "stages/final"
    package = load_package(folder)
    license_record = literal(DRAFT / name / "license.py")
    pin = literal(ROOT / "project/pins/2026-11-01/graphics-source-pin.py")
    assert package.sources == (pin["packages"][name]["recipes"][name + "/stages/final"][0],)
    assert validate_license(license_record, package.sources) == package.licensing
    assert license_record["status"] == "unresolved"
    assert any(c["status"] == "unresolved" for c in license_record["components"])
    assert license_record["scope"] and license_record["notes"]
    assert license_record["evidence"]
    assert all(entry["source_sha256"] == package.sources[0]["sha256"]
               for entry in license_record["evidence"])
    assert package.output_trees == ("usr",)
    assert package.outputs
    assert all(path.startswith("usr/") for path in package.outputs)
    assert not (CANONICAL / name).exists()


def test_held_six_stage_closure_exposes_unadmitted_python_inputs():
    plan = json.loads((DRAFT / "admission-plan.json").read_text())
    assert plan["status"] == "source-prepared-native-and-rights-NO-GO"
    expected = tuple(t.removesuffix("-final") for t in plan["intended_stage_order"])
    assert expected == SIX
    direct = {n: load_package(DRAFT / n / "stages/final") for n in SIX}
    predecessors = {
        "libX11", "libXext", "libxcb", "xorgproto", "expat", "zlib",
        "meson", "ninja",
    }
    for name, package in direct.items():
        for dep in package.build_dependencies + package.runtime_dependencies:
            if dep=="zlib-native-environment":
                assert (CANONICAL/"zlib/stages/native-environment/sources.py").is_file()
                assert not (CANONICAL/"zlib/stages/final").exists()
                continue
            assert dep.endswith("-final"), (name, dep)
            resolved = dep[:-len("-final")]
            assert resolved in SIX or resolved in predecessors or resolved in (
                "mako", "pyyaml",
            ), (name, dep)
    mesa = direct["mesa"]
    assert "mako-final" in mesa.build_dependencies
    assert "pyyaml-final" in mesa.build_dependencies
    assert not (CANONICAL / "mako").exists()
    assert not (CANONICAL / "pyyaml").exists()
    assert "mako-final" in {v["name"] for v in plan["blocked_python_build_inputs"]}
    assert "pyyaml-final" in {v["name"] for v in plan["blocked_python_build_inputs"]}


@pytest.mark.parametrize("name", SIX)
def test_no_synthetic_source_or_immutable_publication_authority(name):
    stage = DRAFT / name / "stages/final"
    pin = literal(ROOT / "project/pins/2026-11-01/graphics-source-pin.py")
    record = literal(DRAFT / name / "license.py")
    manifest = literal(stage / "produce-manifest.py")
    integration = literal(stage / "integration.py")
    assert set(manifest) == {"trees", "required"}
    assert record["status"] != "reviewed"
    assert pin["status"].startswith("supplementary-source-review-only")
    assert integration["native_admission"].startswith("HOLD")
    assert not (CANONICAL / name).exists()


def test_source_archive_inspector_verifies_actual_bytes_not_git_tag_assumptions():
    source = (ROOT / "tools/inspect_graphics_archives.py").read_text()
    assert 'digest != source["sha256"]' in source
    assert 'archive-internal rights hash differs' in source
    assert 'unrecognized exact-release Meson option' in source
    assert 'missing or duplicated build source member' in source
    assert 'source_tree_layout' in source
    assert 'source_review_candidates' in source
    assert 'missing scoped source candidate' in source
    assert 'scoped source hash differs from original archive' in source
    assert 'original_pep517' in source
    assert 'PEP 517 backend requirements changed' in source


def test_exact_glx_pkgconfig_contract_includes_xcb_extensions_and_xshmfence():
    mesa = literal(DRAFT / "mesa/stages/final/integration.py")
    required = set(mesa["inherited_glx_pkgconfig"])
    assert {"x11-xcb","xcb-glx","xcb-dri3","xcb-present",
            "xcb-shm","xcb-sync","xcb-xfixes","xshmfence","xxf86vm",
            "libdrm"} <= required
    assert "DT_NEEDED/SONAME/RPATH/RUNPATH" in mesa["immutable_elf_check"]
    builder = literal(DRAFT / "mesa/stages/final/build.py")
    command = builder["configure"][0][-1]
    assert "pkg-config --exists " + " ".join(mesa["inherited_glx_pkgconfig"]) in command
    x11 = literal(CANONICAL / "libX11/stages/final/produce-manifest.py")
    assert "usr/lib/libX11-xcb.so" in x11["required"]
    xshmfence = literal(DRAFT / "libxshmfence/stages/final/produce-manifest.py")
    assert "usr/lib/pkgconfig/xshmfence.pc" in xshmfence["required"]
    xshmfence_install = literal(DRAFT / "libxshmfence/stages/final/build.py")["install"][0][-1]
    assert "usr/lib/pkgconfig/xshmfence.pc" in xshmfence_install
    demos = literal(DRAFT / "mesa-demos/stages/final/build.py")["configure"][0][-1]
    assert "pkg-config --exists gl glx x11 xext" in demos

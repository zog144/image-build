"""Hold Mesa admission until isolated source-built Python/tool closure is evidenced.

These checks protect the boundary; they do not falsely claim to have built the
Python tools, resolved component licensing, or executed a native graphics build.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "project/graphics-drafts"
PIN = ROOT / "project/pins/2026-11-01/graphics-source-pin.py"
SIX = ("llvm", "libdrm", "libxshmfence", "libXxf86vm", "mesa", "mesa-demos")


def literal(path):
    return ast.literal_eval(path.read_text())


def test_python_sources_do_not_masquerade_as_isolated_builds():
    sources = literal(DRAFT / "python-build-inputs.py")
    assert sources["status"] == "build-only-source-evidence; not install-admitted"
    for name in ("mako", "pyyaml"):
        assert sources["packages"][name]["source_sha256"] == literal(PIN)["packages"][name]["source"]["sha256"]
        assert sources["packages"][name]["unresolved"]
        assert not (ROOT / "project/package" / name).exists()
    plan = json.loads((DRAFT / "admission-plan.json").read_text())
    assert {item["name"] for item in plan["blocked_python_build_inputs"]} == {"mako-final", "pyyaml-final"}
    assert "MarkupSafe" in plan["blocked_python_build_inputs"][0]["issue"]
    # MarkupSafe and backend resolution must not be silently inferred from a runner.
    assert "markupsafe" not in literal(PIN)["packages"]
    assert "setuptools" not in literal(PIN)["packages"]


def test_graphics_configure_is_not_proof_of_path_isolation():
    build = literal(DRAFT / "mesa/stages/final/build.py")
    command = build["configure"][0][-1]
    assert "command -v meson" in command
    assert "pkg-config --exists" in command
    # Prevent this source-only step from being confused with an isolation pass:
    # neither executable ownership nor pkgconf lookup roots are attested here.
    assert "PKG_CONFIG_LIBDIR=" not in command
    assert "CMAKE_PREFIX_PATH=" not in command
    assert "PYTHONNOUSERSITE=" not in command
    plan = json.loads((DRAFT / "admission-plan.json").read_text())
    assert any("without fallback" in gate for gate in plan["required_acceptance"])


def test_all_six_components_remain_unreviewed_and_noncanonical():
    for name in SIX:
        record = literal(DRAFT / name / "license.py")
        assert record["status"] == "unresolved"
        assert record["components"] and all(
            component["status"] == "unresolved" for component in record["components"]
        )
        assert record["evidence"]
        assert not (ROOT / "project/package" / name).exists()
    assert (ROOT / "docs/image-build/mesa-toolchain-and-rights-review-2026-11-01.md").exists()

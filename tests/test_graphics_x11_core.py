from pathlib import Path
import ast

from zog.image_build.metadata import load_packages, order
from zog.image_build.stages import stage_recipes

ROOT = Path(__file__).resolve().parents[1] / "project"


def literal(path):
    return ast.literal_eval(path.read_text())


def test_x11_core_is_consumer_driven_and_ordered(tmp_path):
    plan = stage_recipes(
        ROOT / "bootstrap/graphics-x11-core.py",
        ROOT / "package",
        tmp_path / "recipes",
    )
    packages = load_packages(tmp_path / "recipes")
    ordered = order(packages, plan["targets"])
    assert ordered.index("xtrans-final") < ordered.index("libX11-final")
    assert ordered.index("libX11-final") < ordered.index("libXext-final")
    assert ordered.index("libXfixes-final") < ordered.index("libXi-final")
    assert ordered.index("libXi-final") < ordered.index("libXtst-final")
    assert ordered.index("libfontenc-final") < ordered.index("libXfont2-final")
    assert packages["libX11-final"].runtime_dependencies == ()
    assert packages["libX11-final"].build_dependencies == ("xtrans-final",)


def test_libx11_security_patch_chain_is_typed_and_zero_fuzz():
    package = literal(ROOT / "package/libX11/stages/final/integration.py")
    patches = package["patches"]
    assert [p["cve"] for p in patches] == [
        "CVE-2026-88806",
        "CVE-2026-94283",
        "CVE-2026-94284",
        "CVE-2026-94285",
    ]
    assert [p["order"] for p in patches] == [1, 2, 3, 4]
    assert all(p["fuzz"] == 0 and p["strip"] == 1 for p in patches)
    assert sum(len(p["files"]) for p in patches) == 6
    build = literal(ROOT / "package/libX11/stages/final/build.py")
    script = build["prepare"][0][-1]
    assert script.count("--fuzz=0") == 8
    for patch in patches:
        assert patch["source"]["sha256"] in script
        for file in patch["files"]:
            assert file["before_sha256"] in script
            assert file["after_sha256"] in script


def test_x11_core_does_not_claim_compiler_host_acceptance():
    for name in ["xtrans","libX11","libXext","libXfixes","libXi","libXtst","libXv","libxkbfile","libfontenc","libXfont2"]:
        package = literal(ROOT / "package" / name / "package.py")
        assert package["status"] == "catalogue-only"
        integration = literal(ROOT / "package" / name / "stages/final/integration.py")
        assert "runtime acceptance remains separate" in integration["test_scope"]

def test_x11_session_support_is_consumer_driven_and_ordered(tmp_path):
    plan = stage_recipes(
        ROOT / "bootstrap/graphics-x11-session.py",
        ROOT / "package",
        tmp_path / "recipes",
    )
    packages = load_packages(tmp_path / "recipes")
    ordered = order(packages, plan["targets"])
    assert ordered.index("libICE-final") < ordered.index("libSM-final")
    assert ordered.index("libSM-final") < ordered.index("libXt-final")
    assert packages["libSM-final"].runtime_dependencies == ("libICE-final",)
    assert packages["libXt-final"].runtime_dependencies == (
        "libICE-final",
        "libSM-final",
    )
    sm = literal(ROOT / "package/libSM/stages/final/integration.py")
    assert "util-linux native-environment" in sm["base_contract"]
    for name in ("libICE", "libSM", "libXt"):
        package = literal(ROOT / "package" / name / "package.py")
        assert package["status"] == "catalogue-only"

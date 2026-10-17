from pathlib import Path
import ast

from zog.image_build.metadata import load_packages, order
from zog.image_build.stages import stage_recipes

ROOT = Path(__file__).resolve().parents[1] / "project"


def literal(path):
    return ast.literal_eval(path.read_text())


def test_graphics_xcb_closes_libevdev_keysym_dependency(tmp_path):
    plan = stage_recipes(
        ROOT / "bootstrap/graphics-xcb.py",
        ROOT / "package",
        tmp_path / "recipes",
    )
    packages = load_packages(tmp_path / "recipes")
    ordered = order(packages, plan["targets"])
    assert ordered.index("check-final") < ordered.index("libevdev-final")
    assert ordered.index("libevdev-final") < ordered.index("python-libevdev-final")
    assert ordered.index("python-libevdev-final") < ordered.index("xorgproto-final")
    assert packages["python-libevdev-final"].runtime_dependencies == (
        "libevdev-final",
    )
    assert packages["xorgproto-final"].test_dependencies == (
        "python-libevdev-final",
    )


def test_libevdev_keeps_device_suite_explicitly_outside_package_build():
    build = literal(
        ROOT / "package/libevdev/stages/final/build.py"
    )
    command = build["test"][0]
    assert "--no-suite" in command
    assert "needs-uinput" in command
    integration = literal(
        ROOT / "package/libevdev/stages/final/integration.py"
    )
    assert "/dev/uinput" in integration["test_scope"]
    assert "separate" in integration["external_test_prerequisite"]


def test_python_libevdev_exact_xorgproto_api_is_tested():
    build = literal(
        ROOT / "package/python-libevdev/stages/final/build.py"
    )
    script = build["test"][0][-1]
    assert "EV_KEY.KEY_MAX" in script
    assert "EV_ABS.ABS_MAX" in script
    integration = literal(
        ROOT / "package/python-libevdev/stages/final/integration.py"
    )
    assert "root-only" in integration["test_scope"]


def test_graphics_common_check_is_not_modified_by_dependency_batch():
    path = ROOT / "bootstrap/graphics-common-check.sh"
    data = path.read_text()
    assert "GRAPHICS_COMMON_PASS" in data
    assert "libevdev" not in data
    assert "xcb" not in data.lower()

def test_xcb_i3_support_phase1_is_consumer_driven_and_ordered(tmp_path):
    plan = stage_recipes(
        ROOT / "bootstrap/graphics-xcb-i3-support.py",
        ROOT / "package",
        tmp_path / "recipes",
    )
    packages = load_packages(tmp_path / "recipes")
    ordered = order(packages, plan["targets"])
    assert ordered.index("xcb-util-final") < ordered.index("xcb-util-image-final")
    assert ordered.index("xcb-util-final") < ordered.index("xcb-util-xrm-final")
    assert packages["xcb-util-image-final"].runtime_dependencies == (
        "xcb-util-final",
    )
    assert packages["xcb-util-xrm-final"].runtime_dependencies == (
        "xcb-util-final",
    )
    for name in (
        "xcb-util",
        "xcb-util-image",
        "xcb-util-keysyms",
        "xcb-util-wm",
        "xcb-util-xrm",
    ):
        package = literal(ROOT / "package" / name / "package.py")
        assert package["status"] == "catalogue-only"


def test_desktop_gl_research_covers_xcb_cursor_dependency_closure():
    workflow = (
        ROOT.parent / ".github/workflows/graphics-recipe-research.yml"
    ).read_text()
    desktop = workflow.split("  desktop-and-gl:", 1)[1]
    for name in (
        "xcb-util-image",
        "xcb-util-renderutil",
        "xcb-util-cursor",
        "xcb-util-xrm",
    ):
        assert name in desktop
    assert desktop.index("xcb-util-image") < desktop.index("xcb-util-cursor")
    assert desktop.index("xcb-util-renderutil") < desktop.index("xcb-util-cursor")

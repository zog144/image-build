import ast
import json
from pathlib import Path
from types import SimpleNamespace

from zog.image_build.filesystem import inventory
from zog.image_build.metadata import load_packages
from zog.image_build.stages import stage_recipes
import zog.image_build.resident_boot_targeted as boot


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"


def test_targeted_plan_materializes_shadow_from_unchanged_catalogue_pin(tmp_path):
    plan = stage_recipes(
        PROJECT / "bootstrap/boot-a-targeted.py",
        PROJECT / "package",
        tmp_path / "recipes",
    )
    packages = load_packages(tmp_path / "recipes")
    assert plan["overlay_targets"] == ["systemd-final", "shadow-login"]
    assert {"systemd-final", "shadow-login"} <= set(packages)
    selected = ast.literal_eval((tmp_path / "recipes/commit-pin.py").read_text())
    shadow = selected["packages"]["shadow-login"]
    monthly = ast.literal_eval(
        (PROJECT / "pins/2026-10-01/commit-pin.py").read_text()
    )
    assert shadow["pin_policy"] == "catalogue-source"
    assert {k:shadow["sources"][0][k] for k in ("url","sha256")} == (
        monthly["packages"]["shadow"]["source"]
    )
    login = packages["shadow-login"]
    commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in login.steps[phase]
    )
    assert "--without-libpam" in commands
    assert "! readelf -d src/login | grep -q 'libpam'" in commands


def _overlay_record(root, name):
    outputs = inventory(root)
    inputs = {"fixture": name}
    from zog.image_build.metadata import identity
    return {
        "identity": identity({"inputs": inputs, "outputs": outputs}),
        "inputs": inputs,
        "outputs": outputs,
        "integration": {"fixture": name},
        "provenance": {"output": "sha256:" + name[0] * 64, "result": None},
        "root": str(root),
    }


def test_overlay_plan_preserves_parent_and_records_exact_collisions(tmp_path, monkeypatch):
    parent_root = tmp_path / "parent"
    (parent_root / "usr/bin").mkdir(parents=True)
    (parent_root / "usr/bin/keep").write_text("keep\n")
    (parent_root / "applications").mkdir(mode=0o755)
    parent = SimpleNamespace(
        generation="p" * 64,
        root=parent_root,
        manifest={"outputs": inventory(parent_root)},
    )
    monkeypatch.setattr(
        boot,
        "_parent_binding",
        lambda _parent: {
            "generation": "p" * 64,
            "manifest_sha256": "m" * 64,
            "output_count": len(parent.manifest["outputs"]),
            "outputs_identity": "sha256:" + "i" * 64,
        },
    )

    systemd = tmp_path / "systemd"
    (systemd / "usr/lib/systemd/boot/efi").mkdir(parents=True)
    (systemd / "usr/lib/systemd/boot/efi/systemd-bootx64.efi").write_bytes(b"efi")
    (systemd / "applications").mkdir(mode=0o700)
    (systemd / "applications").chmod(0o000)
    (systemd / "state").mkdir(mode=0o700)
    (systemd / "state").chmod(0o000)

    shadow = tmp_path / "shadow"
    (shadow / "usr/bin").mkdir(parents=True)
    (shadow / "usr/bin/login").write_bytes(b"login")
    (shadow / "usr/bin/login").chmod(0o755)

    overlays = {
        "systemd-final": _overlay_record(systemd, "systemd-final"),
        "shadow-login": _overlay_record(shadow, "shadow-login"),
    }
    plan = boot.overlay_plan(parent, overlays)
    assert plan["removals"] == []
    app = next(item for item in plan["collisions"] if item["path"] == "applications")
    assert app["old"]["mode"] == 0o755 and app["new"]["mode"] == 0
    assert any(item["path"] == "state" for item in plan["additions"])
    assert any(item["path"] == "usr/bin/login" for item in plan["additions"])

    derived = tmp_path / "derived"
    boot.compose(parent, overlays, plan, derived)
    assert (derived / "usr/bin/keep").read_text() == "keep\n"
    assert (derived / "usr/bin/login").read_bytes() == b"login"
    assert (derived / "applications").stat().st_mode & 0o7777 == 0
    assert (derived / "state").stat().st_mode & 0o7777 == 0
    assert inventory(derived) == plan["expected_outputs"]


def test_overlay_plan_rejects_unreviewed_directory_mode_change(tmp_path, monkeypatch):
    parent_root = tmp_path / "parent"
    (parent_root / "usr/bin").mkdir(parents=True)
    (parent_root / "applications").mkdir(mode=0o755)
    parent = SimpleNamespace(
        generation="p" * 64,
        root=parent_root,
        manifest={"outputs": inventory(parent_root)},
    )
    monkeypatch.setattr(boot, "_parent_binding", lambda _parent: {"fixture": True})

    systemd = tmp_path / "systemd"
    (systemd / "usr").mkdir(mode=0o700)
    (systemd / "applications").mkdir(mode=0o700)
    (systemd / "applications").chmod(0o000)
    (systemd / "state").mkdir(mode=0o700)
    (systemd / "state").chmod(0o000)
    shadow = tmp_path / "shadow"
    (shadow / "usr/bin").mkdir(parents=True)
    (shadow / "usr/bin/login").write_bytes(b"login")

    overlays = {
        "systemd-final": _overlay_record(systemd, "systemd-final"),
        "shadow-login": _overlay_record(shadow, "shadow-login"),
    }
    import pytest
    with pytest.raises(Exception, match="unreviewed directory mode replacement"):
        boot.overlay_plan(parent, overlays)

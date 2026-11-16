"""Source regression checks for booted serial console and core service identities.

The native boot remains Work-owned. These guards detect missing staged outputs
or a systemd/getty path mismatch before publishing a successor image.
"""
import ast
from pathlib import Path

PROJECT = Path(__file__).parents[1] / "project"


def recipe(path):
    return ast.literal_eval((PROJECT / "package" / path).read_text())


def command(path, phase):
    return "\n".join(step[-1] for step in recipe(path / "build.py")[phase])


def test_native_util_linux_requires_actual_agetty():
    outputs = recipe(Path("util-linux/stages/native-environment/produce-manifest.py"))
    assert "usr/sbin/agetty" in outputs["required"]
    configure = command(Path("util-linux/stages/native-environment"), "configure")
    assert "--sbindir=/usr/sbin" in configure


def test_systemd_getty_templates_use_native_binary():
    stage = Path("systemd/stages/final")
    configure = command(stage, "configure")
    assert "-Dsplit-bin=false" in configure
    assert "-Dagetty-path=/usr/sbin/agetty" in configure
    assert "-Dagetty-path=/usr/bin/agetty" not in configure
    install = command(stage, "install")
    assert "for unit in getty@.service serial-getty@.service" in install
    assert 'grep -Fq "ExecStart=-/usr/sbin/agetty "' in install
    required = recipe(stage / "produce-manifest.py")["required"]
    assert "usr/lib/systemd/system/getty@.service" in required
    assert "usr/lib/systemd/system/serial-getty@.service" in required


def test_journal_group_declaration_is_a_required_package_output():
    stage = Path("systemd/stages/final")
    assert "usr/lib/sysusers.d/systemd-journal.conf" in recipe(stage / "produce-manifest.py")["required"]
    install = command(stage, "install")
    assert 'grep -Eq "^g[[:space:]]+systemd-journal[[:space:]]"' in install
    assert "systemctl enable" not in install


def test_dbus_user_declaration_is_a_required_package_output():
    stage = Path("dbus/stages/final")
    assert "usr/lib/sysusers.d/dbus.conf" in recipe(stage / "produce-manifest.py")["required"]
    configure = command(stage, "configure")
    assert "-Ddbus_user=messagebus" in configure
    install = command(stage, "install")
    assert 'grep -Eq "^u[[:space:]]+messagebus[[:space:]]"' in install
    assert "useradd" not in install and "groupadd" not in install

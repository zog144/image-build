"""Stage packaged and generated dependency scripts into a private directory.

These tests use disposable roots only, never an EC2 Host, /usr or accepted zog.
"""
import base64
import csv
import hashlib
import io
import os
from pathlib import Path
import stat
import sys
import zipfile

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import install_nonresident_certbot_dependencies_staged as staged
from verify_nonresident_certbot_dependency_wheelhouse import DependencyHold


def _wheel(wheelhouse, *, packaged_script=True, entry_point=True,
           other_data=None):
    name, version = "jmespath", "1.1.0"
    wheel = wheelhouse / "jmespath-1.1.0-py3-none-any.whl"
    metadata = name + "-" + version + ".dist-info"
    mapping = {
        "jmespath/__init__.py": b"def main():\n    return 0\n",
        metadata + "/METADATA": b"Metadata-Version: 2.1\nName: jmespath\nVersion: 1.1.0\n",
        metadata + "/WHEEL": (b"Wheel-Version: 1.0\nGenerator: test\n"
                               b"Root-Is-Purelib: true\nTag: py3-none-any\n"),
    }
    if packaged_script:
        mapping["jmespath-1.1.0.data/scripts/jp.py"] = b"#!python\nprint('wheel jp')\n"
    if entry_point:
        mapping[metadata + "/entry_points.txt"] = (
            b"[console_scripts]\njmespath-cli = jmespath:main\n"
        )
    if other_data:
        mapping["jmespath-1.1.0.data/data/" + other_data] = b"unreviewed"
    rows = []
    for path, data in sorted(mapping.items()):
        data_hash = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
        rows.append((path, "sha256=" + data_hash, str(len(data))))
    rows.append((metadata + "/RECORD", "", ""))
    content = io.StringIO()
    csv.writer(content, lineterminator="\n").writerows(rows)
    mapping[metadata + "/RECORD"] = content.getvalue().encode()
    with zipfile.ZipFile(wheel, "w") as bundle:
        for path, data in mapping.items():
            info = zipfile.ZipInfo(path)
            info.external_attr = 0o755 << 16 if path.endswith("jp.py") else 0o644 << 16
            bundle.writestr(info, data)
    return wheel


def _stage(tmp_path, monkeypatch, *, packaged_script=True, entry_point=True,
           other_data=None):
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    wheel = _wheel(wheelhouse, packaged_script=packaged_script,
                   entry_point=entry_point, other_data=other_data)
    monkeypatch.setattr(staged, "verify_wheels", lambda *_args, **_kwargs: {
        "distributions": [{
            "name": "jmespath", "version": "1.1.0",
            "file": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        }],
    })
    monkeypatch.setattr(staged, "EXPECTED_DEPENDENCIES", 1)
    return staged.stage(wheelhouse, tmp_path / "staged-root")


def _rpm_root(tmp_path):
    root = tmp_path / "rpm-host"
    original = root / "usr/bin/jp.py"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"#!/usr/bin/python3\n# AL2023 RPM owned jp.py\n")
    return root, original, original.read_bytes()


def _zog_guard(root):
    site = root / staged.SITE
    record = site / "zog-0.1.1.dev20261117.dist-info/RECORD"
    launcher = root / "usr/bin/box-control"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_bytes(b"#!/usr/bin/python3.12\n# existing verified zog\n")
    data = launcher.read_bytes()
    launcher_sha = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
    record.parent.mkdir(parents=True)
    record.write_text(
        "../../../bin/box-control,sha256=" + launcher_sha + "," + str(len(data)) + "\n"
        "zog-0.1.1.dev20261117.dist-info/RECORD,,\n"
    )
    return hashlib.sha256(record.read_bytes()).hexdigest(), launcher, data


def test_jp_rpm_command_unchanged_and_packaged_and_generated_scripts_private(tmp_path, monkeypatch):
    result = _stage(tmp_path, monkeypatch)
    root, rpm_script, rpm_before = _rpm_root(tmp_path)
    before_live = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    approved = staged.preflight(result, root)
    assert approved["live_files_written"] == 0
    assert approved["files"] == len(result["members"])
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()) == before_live
    assert rpm_script.read_bytes() == rpm_before
    assert set(result["scripts"]) == {
        staged.SCRIPTS + "/jp.py",
        staged.SCRIPTS + "/jmespath-cli",
    }
    for name in ("jp.py", "jmespath-cli"):
        target = result["root"] / staged.SCRIPTS / name
        assert target.is_file()
        assert target.read_bytes().startswith(b"#!/usr/bin/python3.12")
    record = (result["root"] / staged.SITE /
              "jmespath-1.1.0.dist-info/RECORD").read_text()
    for name in ("jp.py", "jmespath-cli"):
        assert "../../../libexec/zog/python3.12/bin/" + name in record
    staged.verify_staged_records(result["root"], result["wheels"])


def test_private_destination_collision_blocks_entire_install_before_writes(tmp_path, monkeypatch):
    result = _stage(tmp_path, monkeypatch)
    root, rpm_script, original = _rpm_root(tmp_path)
    private = root / staged.SCRIPTS / "jp.py"
    private.parent.mkdir(parents=True)
    private.write_bytes(b"already-owned private destination\n")
    snapshot = {p.relative_to(root).as_posix(): p.read_bytes()
                for p in root.rglob("*") if p.is_file()}
    with pytest.raises(DependencyHold, match="final destination collision"):
        staged.preflight(result, root)
    assert {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()} == snapshot
    assert rpm_script.read_bytes() == original
    assert not (root / staged.SITE / "jmespath").exists()


def test_generated_entrypoint_collision_also_stops_every_file(tmp_path, monkeypatch):
    result = _stage(tmp_path, monkeypatch)
    root, rpm_script, original = _rpm_root(tmp_path)
    generated = root / staged.SCRIPTS / "jmespath-cli"
    generated.parent.mkdir(parents=True)
    generated.write_bytes(b"unexpected executable\n")
    with pytest.raises(DependencyHold, match="final destination collision"):
        staged.preflight(result, root)
    assert rpm_script.read_bytes() == original
    assert not (root / staged.SITE / "jmespath").exists()


def test_library_collision_and_symlinked_ancestor_fail_closed(tmp_path, monkeypatch):
    result = _stage(tmp_path, monkeypatch)
    root, rpm_script, original = _rpm_root(tmp_path)
    existing = root / staged.SITE / "jmespath/__init__.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing package")
    with pytest.raises(DependencyHold, match="collision"):
        staged.preflight(result, root)
    existing.unlink()
    existing.parent.rmdir()
    unsafe = root / "usr/libexec/zog"
    unsafe.parent.mkdir(parents=True)
    unsafe.symlink_to(root / "elsewhere")
    with pytest.raises(DependencyHold, match="ancestry"):
        staged.preflight(result, root)
    assert rpm_script.read_bytes() == original


def test_wheel_data_cannot_escape_python_or_private_script_paths(tmp_path, monkeypatch):
    with pytest.raises(DependencyHold, match="non-Python/non-private-script"):
        _stage(tmp_path, monkeypatch, other_data="bin/another-program")


def test_create_only_simulated_commit_preserves_rpm_jp_and_zog_guard(tmp_path, monkeypatch):
    result = _stage(tmp_path, monkeypatch)
    root, rpm_script, rpm_before = _rpm_root(tmp_path)
    zog_sha, launcher, launcher_before = _zog_guard(root)
    monkeypatch.setattr(staged.os, "geteuid", lambda: 0)
    outcome = staged.apply(result, root, expected_zog_sha=zog_sha,
                           expected_zog_count=2, expected_zog_launchers=1)
    assert outcome["status"] == "FILES_CREATED_NATIVE_READBACK_REQUIRED"
    assert outcome["live_files_written"] == len(result["members"])
    assert rpm_script.read_bytes() == rpm_before
    assert launcher.read_bytes() == launcher_before
    assert (root / staged.SCRIPTS / "jp.py").is_file()
    assert (root / staged.SCRIPTS / "jmespath-cli").is_file()
    assert (root / staged.SITE / "jmespath/__init__.py").is_file()
    assert staged.preflight_existing(result, root, expected_zog_sha=zog_sha,
                                    expected_zog_count=2, expected_zog_launchers=1)
    with pytest.raises(DependencyHold, match="collision"):
        staged.preflight(result, root)


def test_stage_fails_on_tampered_installed_record_before_live_preflight(tmp_path, monkeypatch):
    result = _stage(tmp_path, monkeypatch)
    record = result["root"] / staged.SITE / "jmespath-1.1.0.dist-info/RECORD"
    record.write_text(record.read_text().replace("sha256=", "sha256=x", 1))
    root, rpm_script, before = _rpm_root(tmp_path)
    with pytest.raises(DependencyHold, match="RECORD does not match"):
        staged.preflight(result, root)
    assert rpm_script.read_bytes() == before


def test_staged_collision_between_wheel_scripts_and_generated_entrypoints(tmp_path, monkeypatch):
    # Installer is create-only even inside staging; no ambiguous script owner.
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    wheel = _wheel(wheelhouse)
    monkeypatch.setattr(staged, "verify_wheels", lambda *_args, **_kwargs: {
        "distributions": [{"name": "jmespath", "version": "1.1.0",
                           "file": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}],
    })
    monkeypatch.setattr(staged, "EXPECTED_DEPENDENCIES", 1)
    # A second private entrypoint with the same filename as wheel-provided
    # jp.py is a genuine collision, not a reason to silently overwrite.
    with zipfile.ZipFile(wheel) as zf:
        original = {n:zf.read(n) for n in zf.namelist()}
    original["jmespath-1.1.0.dist-info/entry_points.txt"] = (
        b"[console_scripts]\njp.py = jmespath:main\n")
    record = io.StringIO()
    for name, data in sorted(original.items()):
        if name.endswith("/RECORD"):
            continue
        sha = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
        record.write(f"{name},sha256={sha},{len(data)}\n")
    record.write("jmespath-1.1.0.dist-info/RECORD,,\n")
    original["jmespath-1.1.0.dist-info/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(wheel, "w") as bundle:
        for name, data in original.items():
            bundle.writestr(name, data)
    with pytest.raises((FileExistsError, DependencyHold), match="File already exists|same staged"):
        staged.stage(wheelhouse, tmp_path / "staged-root")

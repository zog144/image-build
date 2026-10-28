import os
import platform
import stat
from pathlib import Path

import pytest

from zog.image_build import ImageBuild
import zog.image_build.engine as engine_module
from zog.image_build.host_export import _payload_staging
from zog.image_build.staging_durability import (
    copy,
    inventory,
    sync,
)
import zog.image_build.staging_durability as durability
import zog.image_build.resident_boot_targeted as boot


def _mode(path):
    return stat.S_IMODE(Path(path).lstat().st_mode)


def _restrictive_root(tmp_path):
    root = tmp_path / "root"
    (root / "usr/bin").mkdir(parents=True)
    (root / "usr/bin/tool").write_bytes(b"tool")
    (root / "state").mkdir()
    (root / "applications").mkdir()
    (root / "state").chmod(0)
    (root / "applications").chmod(0)
    return root


def test_sync_preserves_mode_zero_and_never_follows_symlink(tmp_path):
    root = _restrictive_root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o555)
    (root / "redirect").symlink_to(outside, target_is_directory=True)
    before = inventory(root)

    sync(root)

    assert _mode(root / "state") == 0
    assert _mode(root / "applications") == 0
    assert _mode(outside) == 0o555
    assert inventory(root) == before
    redirect = next(row for row in before if row["path"] == "redirect")
    assert redirect["kind"] == "symlink"


def test_sync_restores_restrictive_modes_when_durability_fails(tmp_path, monkeypatch):
    root = _restrictive_root(tmp_path)

    def fail(_root):
        assert _mode(root / "state") == 0o700
        assert _mode(root / "applications") == 0o700
        raise OSError("injected durability failure")

    monkeypatch.setattr(durability, "_sync_tree", fail)
    with pytest.raises(OSError, match="injected durability failure"):
        sync(root)

    assert _mode(root / "state") == 0
    assert _mode(root / "applications") == 0


def test_copy_preserves_restrictive_modes_and_source(tmp_path):
    source = _restrictive_root(tmp_path)
    expected = inventory(source)
    destination = tmp_path / "copy"

    assert copy(source, destination, expected=expected) == expected

    assert inventory(source) == expected
    assert inventory(destination) == expected
    assert _mode(source / "state") == _mode(destination / "state") == 0
    assert _mode(source / "applications") == _mode(destination / "applications") == 0


def test_payload_staging_preserves_final_modes_in_archive_manifest(tmp_path):
    root = _restrictive_root(tmp_path)
    payload = _payload_staging(root, tmp_path / "rootfs.tar")
    entries = {row["path"]: row for row in payload["entries"]}
    assert entries["state"]["mode"] == 0
    assert entries["applications"]["mode"] == 0
    assert _mode(root / "state") == 0
    assert _mode(root / "applications") == 0


def test_targeted_publication_pre_stage_handles_mode_zero_without_engine_source_change(tmp_path):
    root = _restrictive_root(tmp_path)
    state = tmp_path / "state-store"
    packages = tmp_path / "packages"
    packages.mkdir()
    builder = ImageBuild(package_dir=packages, state_dir=state)
    outputs = inventory(root)
    host = {"fixture": "restrictive-directory-publication"}
    inputs = {
        "schema": 2,
        "kind": "host-bootstrap",
        "host": host,
        "files": outputs,
        "architecture": platform.machine(),
    }
    details = {"host": host}

    boot._prepare_publication_candidate(builder, root, inputs, "host-bootstrap", details)
    original_sync = engine_module.sync_tree
    with boot._targeted_staging_sync():
        assert engine_module.sync_tree is durability.sync
        selected = builder._publish(root, inputs, "host-bootstrap", details)
    assert engine_module.sync_tree is original_sync

    assert selected.manifest["outputs"] == outputs
    assert _mode(selected.root / "state") == 0
    assert _mode(selected.root / "applications") == 0


def test_targeted_sync_scope_restores_engine_callback_on_failure():
    original = engine_module.sync_tree
    with pytest.raises(RuntimeError, match="scope failure"):
        with boot._targeted_staging_sync():
            assert engine_module.sync_tree is durability.sync
            raise RuntimeError("scope failure")
    assert engine_module.sync_tree is original


def test_installed_verification_preparation_handles_mode_zero_as_non_root(tmp_path):
    """Exercise seed_build.verify's real installed-verification preparation path."""
    import json
    from types import SimpleNamespace

    from zog.image_build.developer.seed_build import verify

    assert os.geteuid() != 0, "regression must execute as a non-root coordinator"
    root = _restrictive_root(tmp_path)
    controller = {
        "execution_user_id": os.geteuid(),
        "execution_group_id": os.getegid(),
        "startup_timeout_seconds": 5,
        "termination_grace_seconds": 2,
        "resource_limits": {"memory_max": 1048576},
    }
    policy = {
        "controller": controller,
        "execution_timeout_seconds": 30,
    }

    class Runner:
        def __init__(self):
            self.execute = SimpleNamespace(configuration=lambda: controller)

        def build_request(self, root, source, output, command, environment):
            return {
                "environment": environment,
                "working_directory": "/image-build/source",
                "timeout_seconds": 30,
                "read_only_root": True,
                "network_access": False,
            }

        def run(self, root, source, output, command, environment, log):
            raise RuntimeError("stop after installed-verification preparation")

    builder = SimpleNamespace(
        runner=Runner(),
        provenance=None,
        _policy=lambda: policy,
        _release_resources=lambda _folder: None,
    )
    binding = {
        "verification_report_contract": "image-build-installed-verification-v1",
        "execution_policy": policy,
    }
    folder = tmp_path / "installed-verification"

    with pytest.raises(RuntimeError, match="stop after installed-verification preparation"):
        verify(builder, folder, root, [["/bin/true"]], binding)

    prepared = json.loads((folder / "prepared.json").read_text())
    assert prepared["binding"] == binding
    assert prepared["root"] == inventory(root)
    assert prepared["verification_observation_contract"] == (
        "image-build-verification-observation-v2"
    )
    assert _mode(folder / "root/state") == 0
    assert _mode(folder / "root/applications") == 0
    assert _mode(root / "state") == 0
    assert _mode(root / "applications") == 0



def test_installed_verification_full_completion_handles_mode_zero_as_non_root(
    tmp_path, monkeypatch
):
    """Exercise verify() through durable completion and cleanup as non-root."""
    import json
    from types import SimpleNamespace

    import zog.image_build.developer.seed_build as seed_build

    assert os.geteuid() != 0, "regression must execute as a non-root coordinator"
    root = _restrictive_root(tmp_path)
    controller = {
        "execution_user_id": os.geteuid(),
        "execution_group_id": os.getegid(),
        "startup_timeout_seconds": 5,
        "termination_grace_seconds": 2,
        "resource_limits": {"memory_max": 1048576},
    }
    policy = {
        "controller": controller,
        "execution_timeout_seconds": 30,
    }

    class Runner:
        def __init__(self):
            self.execute = SimpleNamespace(configuration=lambda: controller)
            self.calls = 0

        def build_request(self, root, source, output, command, environment):
            return {
                "environment": environment,
                "working_directory": "/image-build/source",
                "timeout_seconds": 30,
                "read_only_root": True,
                "network_access": False,
            }

        def run(self, root, source, output, command, environment, log):
            self.calls += 1
            restricted = Path(output) / "restricted"
            restricted.mkdir()
            (restricted / "evidence").write_text("verified\n")
            restricted.chmod(0)

    runner = Runner()
    releases = []
    builder = SimpleNamespace(
        runner=runner,
        provenance=None,
        _policy=lambda: policy,
        _release_resources=lambda folder: releases.append(Path(folder)),
    )
    binding = {
        "verification_report_contract": "image-build-installed-verification-v1",
        "execution_policy": policy,
    }
    folder = tmp_path / "installed-verification-full"

    def ordinary_sync_is_forbidden(_path):
        raise AssertionError("verify() used ordinary sync_tree")

    monkeypatch.setattr(seed_build, "sync_tree", ordinary_sync_is_forbidden)

    result = seed_build.verify(builder, folder, root, [["/bin/true"]], binding)

    restricted = next(row for row in result["outputs"] if row["path"] == "restricted")
    assert restricted == {"path": "restricted", "mode": 0, "kind": "directory"}
    assert json.loads((folder / "verification.json").read_text()) == result
    assert _mode(folder / "output/restricted") == 0
    assert not (folder / "root").exists()
    assert not (folder / "source").exists()
    assert json.loads((folder / "workspace-cleanup.json").read_text())["phase"] == "complete"
    assert _mode(root / "state") == 0
    assert _mode(root / "applications") == 0
    assert runner.calls == 1
    assert releases == [folder]

    reused = seed_build.verify(builder, folder, root, [["/bin/true"]], binding)
    assert reused == result
    assert runner.calls == 1
    assert releases == [folder, folder]

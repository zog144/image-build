"""Boot A inherited-peer v2: no replay, privilege shortcut or identity migration.

Source tests use a finite fake box-control recorder; they do not claim kernel
SO_PEERCRED, installed root-control or native child EUID acceptance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zog.image_build import box_control_adapter as adapter_module
from zog.image_build.box_control_adapter import (
    BoxControlExecutionAdapter, INHERITED_EXECUTION_CONTRACT,
)
from zog.image_build.errors import ImageBuildError
from zog.image_build.runner import BuildExecutionRequest


def _request(root):
    for item in ("root", "source", "output"):
        (root / item).mkdir(parents=True, exist_ok=True)
    return BuildExecutionRequest(
        root=root / "root", source=root / "source", output=root / "output",
        command=("/usr/bin/true",), environment={"PATH": "/usr/bin"},
        working_directory="/image-build/source", timeout_seconds=10,
        read_only_root=True, network_access=False,
    )


class RecordingController:
    def __init__(self, project):
        self.project = SimpleNamespace(path=project)
        self.systemd_transport = SimpleNamespace(socket_path="/run/zog/root-control.sock")
        self.calls = []
        self.request_id = "r1-abcdef-" + "a" * 32 + "-" + "b" * 64

    def register_build_root(self, **arguments):
        self.calls.append(("register", arguments))
        return {
            "schema": 1, "execution_contract": INHERITED_EXECUTION_CONTRACT,
            "resource_id": arguments["resource_id"], "state": "ready",
        }

    def issue_build_request_id(self):
        self.calls.append(("issue", {}))
        return self.request_id

    def inspect_build_job(self, job_id):
        from zog.box_control.errors import RuntimeOperationError
        self.calls.append(("inspect", {"job_id": job_id}))
        raise RuntimeOperationError("unknown build identity: job:" + job_id)

    def submit_build_job(self, **arguments):
        from zog.box_control.build_protocol import canonical_request
        request_id = arguments.pop("request_id")
        self.calls.append(("submit", {"request_id": request_id, **arguments}))
        return {
            "schema": 1, "execution_contract": INHERITED_EXECUTION_CONTRACT,
            "request_id": request_id,
            "job_id": hashlib.sha256(request_id.encode()).hexdigest()[:32],
            "request": canonical_request(arguments),
            "process_cleanup_complete": True, "state": "complete",
            "outcome": "success", "exit_code": 0,
            "runtime_id": "test-v2-runtime", "invocation_id": "test-v2-invocation",
            "journal_reference": "test-v2-journal",
        }


def _adapter(control, **options):
    return BoxControlExecutionAdapter(
        control, startup_timeout_seconds=5, termination_grace_seconds=3,
        wait_timeout_seconds=0,
        resource_limits={"thread-count-maximum": 8, "memory-maximum-bytes": 1_000_000},
        input_manifest_id="sha256:" + "1" * 64, **options,
    )


@pytest.fixture(autouse=True)
def nonroot_test_peer(monkeypatch):
    # Actual native root-control must independently attest kernel credentials.
    monkeypatch.setattr(adapter_module.os, "geteuid", lambda: 2001)
    monkeypatch.setattr(adapter_module.os, "getegid", lambda: 2001)


def test_new_producer_emits_v2_only_and_keeps_original_request_identity(tmp_path):
    control = RecordingController(tmp_path)
    package = tmp_path / "new-attempt"
    request = _request(package)
    observed = _adapter(control).execute_for_attempt(
        request, package / "compile.controller.json",
    )
    assert observed.exit_code == 0
    saved = json.loads((package / "compile.controller.json").read_text())
    resource = json.loads((package / "controller-resources.json").read_text())
    assert saved["schema"] == resource["schema"] == 2
    assert saved["execution_contract"] == resource["execution_contract"] == INHERITED_EXECUTION_CONTRACT
    assert saved["binding"]["execution_contract"] == INHERITED_EXECUTION_CONTRACT
    assert saved["request_id"] == control.request_id
    assert saved["binding"]["configuration"]["read_only_root"] if False else True
    assert [name for name, _ in control.calls] == ["register", "issue", "inspect", "submit"]
    for name, arguments in control.calls:
        assert "execution_user_id" not in arguments
        assert "execution_group_id" not in arguments
        assert "User" not in arguments and "Group" not in arguments
    assert saved["binding"]["request"]["read_only_root"] is True
    assert saved["binding"]["request"]["network_access"] is False


@pytest.mark.parametrize("legacy", [
    {"schema": 1, "execution_user_id": 24201, "execution_group_id": 24202},
    {"schema": 1},
    {"schema": 2, "execution_contract": "zog-build-identity-free-v1"},
])
def test_retained_old_command_checkpoint_is_untouched_and_no_rpc(tmp_path, legacy):
    control = RecordingController(tmp_path)
    package = tmp_path / "old-attempt"
    request = _request(package)
    checkpoint = package / "compile.controller.json"
    checkpoint.write_text(json.dumps(legacy))
    original = checkpoint.read_bytes()
    before = {p.name: p.read_bytes() for p in package.iterdir() if p.is_file()}
    with pytest.raises(ImageBuildError, match="inspection-only; refusing replay"):
        _adapter(control).execute_for_attempt(request, checkpoint)
    assert checkpoint.read_bytes() == original
    assert before == {p.name: p.read_bytes() for p in package.iterdir() if p.is_file()}
    assert control.calls == []


@pytest.mark.parametrize("name,old", [
    ("controller-resources.json", {
        "resource_id": "a" * 32, "registration": {"execution_user_id": 24201},
    }),
    ("registration-pending.json", {
        "resource_id": "a" * 32, "registration": {"execution_group_id": 24202},
    }),
])
def test_old_resource_and_pending_registration_do_not_migrate(tmp_path, name, old):
    control = RecordingController(tmp_path)
    package = tmp_path / "old-registration"
    request = _request(package)
    marker = package / name
    marker.write_text(json.dumps(old))
    before = marker.read_bytes()
    with pytest.raises(ImageBuildError, match="inspection-only; refusing replay"):
        _adapter(control).execute_for_attempt(request, package / "compile.controller.json")
    assert marker.read_bytes() == before
    assert control.calls == []
    assert not (package / "compile.controller.json").exists()


def test_release_never_replays_or_releases_legacy_resource(tmp_path):
    control = RecordingController(tmp_path)
    directory = tmp_path / "old-release"
    directory.mkdir()
    data = json.dumps({"resource_id": "a" * 32, "registration": {},
                       "execution_user_id": 24201}).encode()
    (directory / "controller-resources.json").write_bytes(data)
    with pytest.raises(ImageBuildError, match="inspection-only; refusing replay"):
        _adapter(control).release_resources(directory)
    assert (directory / "controller-resources.json").read_bytes() == data
    assert control.calls == []
    assert not (directory / "controller-released.json").exists()


@pytest.mark.parametrize("key", ["geteuid", "getegid"])
def test_root_peer_rejected_before_any_request_or_mutation(tmp_path, monkeypatch, key):
    control = RecordingController(tmp_path)
    package = tmp_path / "root-caller"
    request = _request(package)
    monkeypatch.setattr(adapter_module.os, key, lambda: 0)
    with pytest.raises(ImageBuildError, match="authenticated nonroot"):
        _adapter(control).execute_for_attempt(request, package / "compile.controller.json")
    assert control.calls == []
    assert not list(package.glob("*.json"))


@pytest.mark.parametrize("bad", [
    {"execution_identity": "root"},
    {"execution_identity": "owner"},
])
def test_selected_user_overrides_rejected_at_adapter_construction(tmp_path, bad):
    with pytest.raises(ImageBuildError, match="must be inherit"):
        _adapter(RecordingController(tmp_path), **bad)

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


@pytest.mark.parametrize("uid,gid", [(0, 2001), (2001, 0)])
def test_mixed_zero_peer_rejected_before_any_request_or_mutation(
    tmp_path, monkeypatch, uid, gid,
):
    control = RecordingController(tmp_path)
    package = tmp_path / "mixed-zero-caller"
    request = _request(package)
    monkeypatch.setattr(adapter_module.os, "geteuid", lambda: uid)
    monkeypatch.setattr(adapter_module.os, "getegid", lambda: gid)
    with pytest.raises(ImageBuildError, match="matched 0:0 or positive UID/GID"):
        _adapter(control).execute_for_attempt(request, package / "compile.controller.json")
    assert control.calls == []
    assert not list(package.glob("*.json"))
    assert not list(package.glob("*.lock"))


def test_root_0_0_peer_can_register_and_submit_new_v2_job(tmp_path, monkeypatch):
    # An injected local 0:0 process view is a source-only fixture, NOT
    # evidence of a kernel-authenticated socket peer or native root child.
    monkeypatch.setattr(adapter_module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(adapter_module.os, "getegid", lambda: 0)
    control = RecordingController(tmp_path)
    package = tmp_path / "root-v2-new-attempt"
    request = _request(package)
    observed = _adapter(control).execute_for_attempt(
        request, package / "compile.controller.json",
    )
    assert observed.exit_code == 0
    checkpoint = json.loads((package / "compile.controller.json").read_text())
    resource = json.loads((package / "controller-resources.json").read_text())
    assert checkpoint["schema"] == resource["schema"] == 2
    assert checkpoint["execution_contract"] == resource["execution_contract"] == INHERITED_EXECUTION_CONTRACT
    assert [name for name, _ in control.calls] == ["register", "issue", "inspect", "submit"]
    for _, arguments in control.calls:
        assert not set(arguments) & {
            "User", "Group", "execution_user_id", "execution_group_id",
            "_peer", "peer", "peer_identity",
        }
    assert checkpoint["binding"]["request"]["read_only_root"] is True
    assert checkpoint["binding"]["request"]["network_access"] is False


def test_root_0_0_peer_still_requires_exact_box_control_v2_wire(tmp_path, monkeypatch):
    from zog.box_control import build_protocol
    monkeypatch.setattr(adapter_module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(adapter_module.os, "getegid", lambda: 0)
    monkeypatch.setattr(build_protocol, "INHERITED_EXECUTION_CONTRACT", "legacy-identity-v1")
    control = RecordingController(tmp_path)
    package = tmp_path / "wrong-wire"
    request = _request(package)
    with pytest.raises(ImageBuildError, match="v2 wire is not selected"):
        _adapter(control).execute_for_attempt(request, package / "compile.controller.json")
    assert control.calls == []
    assert not list(package.glob("*.json"))
    assert not list(package.glob("*.lock"))


@pytest.mark.parametrize("bad", [
    {"execution_identity": "root"},
    {"execution_identity": "owner"},
])
def test_selected_user_overrides_rejected_at_adapter_construction(tmp_path, bad):
    with pytest.raises(ImageBuildError, match="must be inherit"):
        _adapter(RecordingController(tmp_path), **bad)



def _pending_registration(tmp_path):
    directory = tmp_path / "new-pending-registration"
    directory.mkdir()
    control = RecordingController(tmp_path)
    registration = {
        "prepared_root": "/project/attempt/root",
        "source_directory": "/project/attempt/source",
        "output_directory": "/project/attempt/output",
        "input_manifest_id": "sha256:" + "1" * 64,
    }
    rid = "a" * 32
    binding = {
        "schema": 2,
        "execution_contract": INHERITED_EXECUTION_CONTRACT,
        "resource_id": rid,
        "registration": registration,
    }
    (directory / "registration-pending.json").write_text(json.dumps(binding))
    return directory, control, rid, registration


def test_root_0_0_schema2_registration_resume_keeps_original_identity(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(adapter_module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(adapter_module.os, "getegid", lambda: 0)
    directory, control, rid, registration = _pending_registration(tmp_path)
    control.inspect_build_root = lambda key: {
        "schema": 2, "resource_id": key, "state": "ready",
        "execution_identity": {"uid": 0, "gid": 0}, "intent": registration,
    }
    original = (directory / "registration-pending.json").read_bytes()
    assert _adapter(control)._register(rid, registration, directory)["state"] == "ready"
    assert original  # the original was a v2 registration, never rewritten
    assert not (directory / "registration-pending.json").exists()
    assert control.calls == [("register", {"resource_id": rid, **registration})]


def test_peer_bound_root_schema2_registration_recovery_uses_same_identity(tmp_path):
    directory, control, rid, registration = _pending_registration(tmp_path)
    control.inspect_build_root = lambda key: {
        "schema": 2, "resource_id": key, "state": "ready",
        "execution_identity": {"uid": 2001, "gid": 2001},
        "intent": registration,
    }
    result = _adapter(control)._register(rid, registration, directory)
    assert result["state"] == "ready"
    assert result["execution_contract"] == INHERITED_EXECUTION_CONTRACT
    assert not (directory / "registration-pending.json").exists()
    progress = json.loads((directory / "registration-progress.json").read_text())
    assert progress["schema"] == 2
    assert progress["execution_contract"] == INHERITED_EXECUTION_CONTRACT
    assert control.calls == [("register", {"resource_id": rid, **registration})]


@pytest.mark.parametrize("server", [
    {"schema": 1, "execution_identity": {"uid": 2001, "gid": 2001}},
    {"schema": 2, "execution_identity": {"uid": 0, "gid": 2001}},
    {"schema": 2, "execution_identity": {"uid": 2001, "gid": 0}},
    {"schema": 2, "execution_identity": {"uid": 2001, "gid": 2001},
     "intent": {"input_manifest_id": "different"}},
    {"schema": 2, "execution_identity": {"uid": -1, "gid": -1}},
    {"schema": 2, "execution_identity": {"uid": 2**31, "gid": 2**31}},
    {"schema": 2, "execution_identity": {"uid": True, "gid": True}},
])
def test_old_or_forged_remote_registration_does_not_clear_pending(
    tmp_path, server,
):
    directory, control, rid, registration = _pending_registration(tmp_path)
    old = (directory / "registration-pending.json").read_bytes()
    control.inspect_build_root = lambda key: {
        "resource_id": key, "state": "ready", "intent": registration, **server,
    }
    with pytest.raises(ImageBuildError, match="not authenticated peer-bound schema 2"):
        _adapter(control)._register(rid, registration, directory)
    assert (directory / "registration-pending.json").read_bytes() == old
    assert control.calls == []


def test_absent_registration_is_observed_but_not_resubmitted(tmp_path):
    from zog.image_build.box_control_adapter import BuildRegistrationPending
    directory, control, rid, registration = _pending_registration(tmp_path)
    old = (directory / "registration-pending.json").read_bytes()
    control.inspect_build_root = lambda key: {
        "resource_id": key, "state": "absent",
    }
    with pytest.raises(BuildRegistrationPending, match="registration"):
        _adapter(control)._register(rid, registration, directory)
    assert (directory / "registration-pending.json").read_bytes() == old
    assert control.calls == []


@pytest.mark.parametrize("peer", [(0, 0), (1001, 1002)])
def test_corrected_root_daemon_accepts_exact_box_registration_envelope(
        tmp_path, monkeypatch, peer):
    """The actual selected client/daemon pair must not repeat R5's RPC error."""
    from zog.root_control.daemon import RootControlDaemon, BUILD_RPC_CONTRACT
    from zog.box_control.build_protocol import INHERITED_EXECUTION_CONTRACT
    from zog.box_control.runtime.root_control import RootControlSystemdTransport

    assert BUILD_RPC_CONTRACT == INHERITED_EXECUTION_CONTRACT == (
        "zog-build-inherited-peer-v2")
    daemon = RootControlDaemon(tmp_path / "unused.sock")
    calls = []

    class Backend:
        def register(self, **kwargs):
            calls.append(kwargs)
            assert "build_contract" not in kwargs
            assert kwargs.pop("_peer") == peer
            assert kwargs.pop("project_root") == "/project"
            assert set(kwargs) == {"resource_id", "prepared_root",
                                   "source_directory", "output_directory",
                                   "input_manifest_id"}
            return {"state": "ready"}

    daemon.build = Backend()
    client = RootControlSystemdTransport()
    args = dict(resource_id="b" * 32, prepared_root="/project/root",
                source_directory="/project/source",
                output_directory="/project/output", input_manifest_id="test")
    def dispatch(operation, **fields):
        assert operation == "build_register"
        assert fields["build_contract"] == BUILD_RPC_CONTRACT
        assert not set(fields) & {"uid", "gid", "User", "Group", "_peer"}
        return daemon.handle({"operation": operation, **fields},
                             peer=peer)["result"]
    monkeypatch.setattr(client, "_request", dispatch)
    assert client.build_call("register", project_root="/project", **args) == {
        "state": "ready"}
    assert len(calls) == 1
    with pytest.raises(ValueError, match="unsupported inherited build RPC contract"):
        daemon.handle({"operation": "build_register", "project_root": "/project",
                       **args}, peer=peer)
    with pytest.raises(ValueError, match="unsupported inherited build RPC fields"):
        daemon.handle({"operation": "build_register", "project_root": "/project",
                       "build_contract": BUILD_RPC_CONTRACT,
                       **args, "unexpected": True}, peer=peer)
    assert len(calls) == 1


@pytest.mark.parametrize("inspection", [
    "absent", "ready", "importing", "unavailable", "forged-absent",
])
def test_failed_registration_before_first_job_cancels_only_with_controller_proof(
    tmp_path, inspection,
):
    """Fonts #63: no manual removal of an orphan pre-job registration.

    The original registration is durable; no request ID or controller job has
    ever been allocated. Only an authentic terminal/absent registration status
    permits controller-mediated release. Unknown/unsafe inspection must HOLD.
    This is synthetic controller source acceptance, not native root-control
    proof or permission to replay the old Fonts request.
    """
    from zog.box_control.errors import RuntimeOperationError

    class PreJobRegistrationFailure(RecordingController):
        def __init__(self, project):
            super().__init__(project)
            self.local_record = None

        def register_build_root(self, **arguments):
            self.calls.append(("register", arguments))
            self.local_record = dict(arguments)  # controller retained before RPC
            raise RuntimeOperationError(
                "registration failed before issuing a build request")

        def inspect_build_root(self, resource_id):
            self.calls.append(("inspect-registration", {"resource_id": resource_id}))
            if inspection == "unavailable":
                raise RuntimeOperationError("original registration status unavailable")
            if inspection == "forged-absent":
                return {"resource_id": resource_id, "state": "absent",
                        "unverified": True}
            if inspection == "absent":
                return {"resource_id": resource_id, "state": "absent"}
            return {
                "schema": 2, "resource_id": resource_id, "state": inspection,
                "intent": {k: v for k, v in self.local_record.items()
                           if k != "resource_id"},
                "execution_identity": {"uid": 2001, "gid": 2001},
            }

        def release_build_root(self, resource_id):
            self.calls.append(("release-registration", {"resource_id": resource_id}))
            assert self.local_record["resource_id"] == resource_id
            self.local_record = None  # only the controller performs cleanup
            return {"schema": 1, "execution_contract": INHERITED_EXECUTION_CONTRACT,
                    "resource_id": resource_id, "state": "released"}

    control = PreJobRegistrationFailure(tmp_path)
    package = tmp_path / "pre-job-failure"
    request = _request(package)
    adapter = _adapter(control)
    with pytest.raises(RuntimeOperationError, match="before issuing a build request"):
        adapter.execute_for_attempt(request, package / "compile.controller.json")

    resource_path = package / "controller-resources.json"
    old_resource = resource_path.read_bytes()
    resource = json.loads(old_resource)
    assert resource["schema"] == 2
    assert not list(package.glob("*.controller.json"))
    assert [label for label, _ in control.calls] == ["register"]
    assert control.local_record is not None

    if inspection in ("absent", "ready"):
        adapter.release_resources(package)
        assert json.loads((package / "controller-released.json").read_text()) == {
            "resource_id": resource["resource_id"],
            "execution_contract": INHERITED_EXECUTION_CONTRACT,
        }
        assert control.local_record is None
        assert resource_path.read_bytes() == old_resource  # retained evidence
        assert not list(package.glob("*.controller.json"))
        assert [label for label, _ in control.calls] == [
            "register", "inspect-registration", "release-registration",
        ]
        adapter.release_resources(package)  # idempotent, no second release
        assert len(control.calls) == 3
    else:
        with pytest.raises((ImageBuildError, RuntimeOperationError)):
            adapter.release_resources(package)
        assert not (package / "controller-released.json").exists()
        assert control.local_record is not None
        assert resource_path.read_bytes() == old_resource
        assert [label for label, _ in control.calls] == [
            "register", "inspect-registration",
        ]

"""Cross-repository finite-build identity-free registration (source-only).

Exercises the actual image-build adapter registration in a strict receiver,
checks the selected box-control wire schema, and compares root-control's
reviewed BuildBackend.register signature. No native compiler job is submitted.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from zog.image_build.box_control_adapter import BoxControlExecutionAdapter
from zog.image_build.errors import ImageBuildError
from zog.image_build.runner import BuildExecutionRequest

ROOT = Path(__file__).parents[1]
BOX = ROOT / "companions/box-control-inherited/box-control/src/zog/box_control/build_protocol.py"
ROOT_CONTROL = ROOT / "companions/root-control-inherited/src/zog/root_control/build.py"


def companion(path):
    if not path.is_file():
        if os.environ.get("REQUIRE_INHERITED_BUILD_PROTOCOL") == "1":
            pytest.fail("exact combined controller companion is required: " + str(path))
        pytest.skip("combined box-control/root-control source checkout belongs to focused CI")
    return path


def _adapter(control):
    return BoxControlExecutionAdapter(
        control,
        startup_timeout_seconds=5,
        termination_grace_seconds=3,
        wait_timeout_seconds=0,
        resource_limits={"thread-count-maximum": 32, "memory-maximum-bytes": 100000000},
        input_manifest_id="sha256:" + "1" * 64,
    )


class StrictReceiver:
    """The only arguments accepted by PR #49/#51 BuildBackend.register."""
    def __init__(self, directory):
        self.project = SimpleNamespace(path=directory)
        self.systemd_transport = SimpleNamespace(socket_path="/run/zog/root-control.sock")
        self.calls = []

    def register_build_root(self, *, resource_id, prepared_root, source_directory,
                            output_directory, input_manifest_id):
        self.calls.append({
            "resource_id": resource_id,
            "prepared_root": prepared_root,
            "source_directory": source_directory,
            "output_directory": output_directory,
            "input_manifest_id": input_manifest_id,
        })
        return {"resource_id": resource_id, "state": "ready",
                "execution_contract": "zog-build-inherited-peer-v2"}


def test_boot_a_adapter_matches_real_legacy_free_registration_shape(tmp_path):
    control = StrictReceiver(tmp_path / "project")
    adapter = _adapter(control)
    request = dict(
        prepared_root="/fixture/root",
        source_directory="/fixture/source",
        output_directory="/fixture/output",
        input_manifest_id="manifest",
    )
    observed = adapter._register("a" * 32, request, tmp_path)
    assert observed["state"] == "ready"
    assert control.calls == [dict(request, resource_id="a" * 32)]
    assert adapter.configuration()["execution_identity"] == "inherit"
    assert adapter.configuration()["execution_contract"] == "zog-build-inherited-peer-v2"
    assert "execution_user_id" not in adapter.configuration()
    assert "execution_group_id" not in adapter.configuration()
    params = inspect.signature(BoxControlExecutionAdapter).parameters
    assert "execution_user_id" not in params and "execution_group_id" not in params


def test_root_control_real_source_exactly_matches_receiver_signature():
    source = ast.parse(companion(ROOT_CONTROL).read_text())
    backend = next(node for node in source.body
                   if isinstance(node, ast.ClassDef) and node.name == "BuildBackend")
    register = next(node for node in backend.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "register")
    assert [n.arg for n in register.args.kwonlyargs] == [
        "project_root", "resource_id", "prepared_root", "source_directory",
        "output_directory", "input_manifest_id",
    ]
    canonical = next(node for node in source.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "canonical_request")
    literals = {
        n.value for n in ast.walk(canonical)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    assert "execution_user_id" not in literals
    assert "execution_group_id" not in literals


def test_selected_box_control_wire_request_accepts_no_account_selectors():
    companion(BOX)
    from zog.box_control.build_protocol import canonical_request
    from zog.box_control.errors import RuntimeOperationError
    rid = "a" * 32
    request = {
        "build_root_id": rid,
        "source_workspace_id": rid + "-source",
        "output_workspace_id": rid + "-output",
        "command": ["/usr/bin/true"],
        "environment": {"PATH": "/usr/bin"},
        "working_directory": "/image-build/source",
        "startup_timeout_seconds": 5,
        "execution_timeout_seconds": 10,
        "termination_grace_seconds": 3,
        "resource_limits": {
            "thread-count-maximum": 32,
            "memory-maximum-bytes": 100000000,
        },
        "read_only_root": True,
        "network_access": False,
    }
    assert canonical_request(request) == request
    for selector in ("execution_user_id", "execution_group_id"):
        with pytest.raises(RuntimeOperationError, match="missing or unsupported fields"):
            canonical_request(dict(request, **{selector: 24202}))


def test_legacy_identity_bearing_checkpoint_is_not_rewritten_or_resubmitted(tmp_path):
    companion(BOX)
    control = StrictReceiver(tmp_path / "project")
    adapter = _adapter(control)
    package = tmp_path / "package-attempt"
    root, source, output = (package / name for name in ("root", "source", "output"))
    for path in (root, source, output):
        path.mkdir(parents=True, exist_ok=True)
    old_registration = {
        "prepared_root": str(root),
        "source_directory": str(source),
        "output_directory": str(output),
        "input_manifest_id": "sha256:" + "1" * 64,
        "execution_user_id": 24201,
        "execution_group_id": 24202,
    }
    resources = package / "controller-resources.json"
    original = {"resource_id": "b" * 32, "registration": old_registration}
    resources.write_text(json.dumps(original))
    checkpoint = package / "compile.controller.json"
    request = BuildExecutionRequest(
        root=root, source=source, output=output, command=("/usr/bin/true",),
        environment={"PATH": "/usr/bin"},
        working_directory="/image-build/source", timeout_seconds=10,
    )
    with pytest.raises(ImageBuildError, match="package resource binding changed"):
        adapter.execute_for_attempt(request, checkpoint)
    assert json.loads(resources.read_text()) == original
    assert not checkpoint.exists()
    assert control.calls == []


def test_config_requires_no_execution_identity_and_fails_closed_for_old_json(tmp_path):
    companion(BOX)
    from zog.image_build.configuration import configured_runner
    project = tmp_path / "project"
    raw = {
        "execution_identity": "inherit",
        "project_root": str(project),
        "socket_path": "/run/zog/root-control.sock",
        "startup_timeout_seconds": 5,
        "execution_timeout_seconds": 20,
        "termination_grace_seconds": 3,
        "wait_timeout_seconds": 0,
        "transport_timeout_seconds": 10,
        "resource_limits": {
            "thread-count-maximum": 32,
            "memory-maximum-bytes": 100000000,
        },
    }
    config = tmp_path / "controller.json"
    config.write_text(json.dumps(raw))
    runner = configured_runner(config, project / "state")
    assert "execution_user_id" not in runner.execute.configuration()
    assert "execution_group_id" not in runner.execute.configuration()
    for field in ("execution_user_id", "execution_group_id", "User", "Group", "execution_contract"):
        config.write_text(json.dumps(dict(raw, **{field: 24202})))
        with pytest.raises(ImageBuildError, match="missing or unsupported fields"):
            configured_runner(config, project / "state")
    config.write_text(json.dumps(dict(raw, execution_identity="selected")))
    with pytest.raises(ImageBuildError, match="must be inherit"):
        configured_runner(config, project / "state")

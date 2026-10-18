import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from zog.image_build import verification_observations as vo
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory, write_json
from zog.image_build.metadata import identity
from zog.image_build.runner import (
    BoxControlRunner,
    BuildExecutionRequest,
)


def controller(tmp_path):
    return {
        "project_root": str(tmp_path / "project"),
        "socket_path": str(tmp_path / "root-control.sock"),
        "execution_user_id": 1000,
        "execution_group_id": 1001,
        "startup_timeout_seconds": 30,
        "termination_grace_seconds": 5,
        "resource_limits": {
            "thread-count-maximum": 128,
            "memory-maximum-bytes": 1024 * 1024 * 1024,
            "cpu-weight": 100,
        },
    }


def request(tmp_path, *, command=("/bin/check",), timeout=60,
            network=False, read_only=True, environment=None,
            root_name="root-a"):
    return BuildExecutionRequest(
        root=tmp_path / root_name,
        source=tmp_path / "source",
        output=tmp_path / "output",
        command=tuple(command),
        environment=environment or {
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "LC_ALL": "C",
            "HOME": "/tmp",
        },
        working_directory="/image-build/source",
        timeout_seconds=timeout,
        read_only_root=read_only,
        network_access=network,
    )


def env(tmp_path, **kwargs):
    return vo.execution_environment(
        request(tmp_path, **kwargs), controller(tmp_path)
    )


def test_identical_execution_environment_is_stable(tmp_path):
    first = env(tmp_path)
    second = env(tmp_path)
    assert first == second
    assert first["contract"] == vo.ENVIRONMENT_SCHEMA
    assert first["digest"] == (
        "sha256:" + identity(first["descriptor"])
    )


@pytest.mark.parametrize(
    ("change", "kwargs"),
    [
        ("timeout", {"timeout": 61}),
        ("network", {"network": True}),
        ("read-only-root", {"read_only": False}),
    ],
)
def test_execution_relevant_changes_change_environment(
    tmp_path, change, kwargs
):
    assert env(tmp_path)["digest"] != env(
        tmp_path, **kwargs
    )["digest"], change


def test_controller_isolation_and_resource_changes_change_environment(
    tmp_path,
):
    req = request(tmp_path)
    base = controller(tmp_path)
    first = vo.execution_environment(req, base)

    changed_user = dict(base, execution_user_id=2000)
    assert (
        vo.execution_environment(req, changed_user)["digest"]
        != first["digest"]
    )

    changed_limits = dict(
        base,
        resource_limits=dict(
            base["resource_limits"],
            **{"memory-maximum-bytes": 2 * 1024**3},
        ),
    )
    assert (
        vo.execution_environment(req, changed_limits)["digest"]
        != first["digest"]
    )


def test_broad_producer_policy_is_separate_from_execution_environment(
    tmp_path,
):
    environment = env(tmp_path)
    policy_a = {
        "controller": controller(tmp_path),
        "execution_timeout_seconds": 60,
        "provenance": {"scope": "one"},
        "source_mirror": {"endpoint": "mirror-one"},
    }
    policy_b = {
        **policy_a,
        "provenance": {"scope": "two"},
        "source_mirror": {"endpoint": "mirror-two"},
        "dependency_replacements": {"fixture": {"identity": "changed"}},
    }
    assert env(tmp_path) == environment
    assert (
        vo.producer_policy_digest(policy_a)
        != vo.producer_policy_digest(policy_b)
    )


def test_command_and_generation_locator_are_not_environment_identity(
    tmp_path,
):
    first = env(
        tmp_path,
        command=("/bin/check", "one"),
        root_name="generation-a",
    )
    second = env(
        tmp_path,
        command=("/bin/other-check", "two"),
        root_name="generation-b",
    )
    assert first == second
    assert (
        "sha256:" + identity(["/bin/check", "one"])
        != "sha256:" + identity(["/bin/other-check", "two"])
    )


def test_v2_pass_and_fail_bind_same_environment_contract(tmp_path):
    environment = env(tmp_path)
    common = dict(
        check_id="image-build/fixture/command/0",
        definition_digest="sha256:" + identity(["/bin/check"]),
        subject={
            "kind": "generation-candidate",
            "generation_id": "candidate",
            "root_inventory_digest": "sha256:" + "1" * 64,
        },
        attempt_id="attempt",
        sequence=0,
        execution_environment=environment,
        producer_policy_digest="sha256:" + "2" * 64,
        evidence=[{"kind": "fixture"}],
    )
    passed = vo.observation_v2(
        **common,
        outcome="PASS",
        execution={"exit_code": 0},
    )
    failed = vo.observation_v2(
        **common,
        outcome="FAIL",
        execution={"exit_code": 2},
    )
    assert passed["execution_environment"] == failed[
        "execution_environment"
    ]
    assert (
        passed["execution_environment"]["digest"]
        == failed["execution_environment"]["digest"]
        == environment["digest"]
    )
    assert "environment_digest" not in passed
    assert "environment_digest" not in failed


class FakeProvenance:
    host_id = "host"
    project_id = "project"

    def __init__(self, root):
        self.root = Path(root)
        (self.root / "artifacts").mkdir(parents=True)

    def _bytes(self, name, value):
        raw = (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode()
        digest = hashlib.sha256(raw).hexdigest()
        (self.root / "artifacts" / digest).write_bytes(raw)
        return {
            "name": name,
            "digest": "sha256:" + digest,
            "size": len(raw),
        }


def capture_fixture(tmp_path, *, exit_code=0):
    folder = tmp_path / "attempt"
    for name in ("root", "source", "output"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    (folder / "root" / "payload").write_text("fixture")
    command = ["/bin/check", "--fixture"]
    config = controller(tmp_path)
    policy = {
        "controller": config,
        "execution_timeout_seconds": 60,
        "provenance": {"fixture": "audit-only"},
    }
    binding = {
        "verification_report_contract":
            "image-build-installed-verification-v1",
        "verification_check": "fixture",
        "execution_policy": policy,
    }
    runner = BoxControlRunner(timeout=60)
    req = runner.build_request(
        folder / "root",
        folder / "source",
        folder / "output",
        command,
        {},
    )
    environment = vo.execution_environment(req, config)
    prepared = {
        "root": inventory(folder / "root"),
        "binding": binding,
        "commands": [command],
        "verification_observation_contract": vo.V2_SCHEMA,
        "producer_policy_digest":
            vo.producer_policy_digest(policy),
        "execution_environments": [environment],
    }
    write_json(
        folder / "command-0.execution.json",
        {
            "request": json.loads(
                json.dumps(asdict(req), default=str)
            ),
            "policy": config,
            "runtime_id": "runtime",
            "invocation_id": "invocation",
            "journal_reference": "journal",
            "exit_code": exit_code,
            "cleanup_complete": True,
        },
    )
    p = FakeProvenance(tmp_path / "build-record")
    builder = SimpleNamespace(
        provenance=p,
        _policy=lambda: policy,
    )
    return builder, folder, prepared


def test_repeated_capture_replays_exact_v2_observation(tmp_path):
    builder, folder, prepared = capture_fixture(tmp_path)
    first = vo.capture(builder, folder, prepared, 0)
    second = vo.capture(builder, folder, prepared, 0)
    assert second == first
    value = json.loads(
        (
            builder.provenance.root
            / "artifacts"
            / first["digest"][7:]
        ).read_text()
    )
    assert value["schema"] == vo.V2_SCHEMA
    assert value["outcome"] == "PASS"
    assert value["timing"]["observed_at"] is not None


def test_capture_fails_if_actual_request_environment_differs(
    tmp_path,
):
    builder, folder, prepared = capture_fixture(tmp_path)
    checkpoint = folder / "command-0.execution.json"
    raw = json.loads(checkpoint.read_text())
    raw["request"]["network_access"] = True
    write_json(checkpoint, raw)
    with pytest.raises(
        ImageBuildError,
        match="execution environment differs",
    ):
        vo.capture(builder, folder, prepared, 0)


def test_v1_evidence_remains_legacy_and_unmodified():
    legacy_digest = "sha256:" + "3" * 64
    value = vo.observation(
        check_id="image-build/legacy/command/0",
        definition_digest="sha256:" + "4" * 64,
        subject={
            "kind": "generation-candidate",
            "generation_id": "legacy",
            "root_inventory_digest": "sha256:" + "5" * 64,
        },
        attempt_id="legacy-attempt",
        sequence=0,
        outcome="PASS",
        execution={"exit_code": 0},
        environment_digest=legacy_digest,
        evidence=[{"kind": "legacy"}],
    )
    assert value["schema"] == vo.V1_SCHEMA
    assert value["environment_digest"] == legacy_digest
    assert "execution_environment" not in value
    assert "producer_policy_digest" not in value
    assert vo.validate(value) == value


def test_secret_like_environment_is_rejected(tmp_path):
    with pytest.raises(
        ImageBuildError,
        match="must not contain credentials",
    ):
        vo.execution_environment(
            request(
                tmp_path,
                environment={
                    "PATH": "/usr/bin:/bin",
                    "API_TOKEN": "definitely-secret",
                },
            ),
            controller(tmp_path),
        )


def test_new_verification_preparation_freezes_v2_environment(tmp_path):
    from zog.image_build.developer.seed_build import verify

    root = tmp_path / "candidate"
    root.mkdir()
    (root / "payload").write_text("candidate")
    config = controller(tmp_path)
    policy = {
        "controller": config,
        "execution_timeout_seconds": 60,
        "provenance": {"fixture": "audit"},
        "source_mirror": {"fixture": "mirror"},
    }
    calls = []

    def execute(request):
        calls.append(request)
        from zog.image_build.runner import BuildExecutionResult
        return BuildExecutionResult(
            "runtime", "invocation", 0, True, "journal"
        )

    execute.configuration = lambda: config
    runner = BoxControlRunner(execute=execute, timeout=60)
    provenance = FakeProvenance(tmp_path / "build-record")
    builder = SimpleNamespace(
        runner=runner,
        provenance=provenance,
        _policy=lambda: policy,
        _release_resources=lambda directory: None,
    )
    binding = {
        "verification_report_contract":
            "image-build-installed-verification-v1",
        "verification_check": "fixture",
        "execution_policy": policy,
    }
    folder = tmp_path / "verification"
    result = verify(
        builder,
        folder,
        root,
        [["/bin/check", "--fixture"]],
        binding,
    )
    prepared = json.loads(
        (folder / "prepared.json").read_text()
    )
    assert (
        prepared["verification_observation_contract"]
        == vo.V2_SCHEMA
    )
    assert (
        prepared["producer_policy_digest"]
        == vo.producer_policy_digest(policy)
    )
    assert len(prepared["execution_environments"]) == 1
    vo.validate_execution_environment(
        prepared["execution_environments"][0]
    )
    descriptors = list(
        (folder / "verification-observations").glob("0.json")
    )
    assert len(descriptors) == 1
    descriptor = json.loads(descriptors[0].read_text())
    observed = json.loads(
        (
            provenance.root
            / "artifacts"
            / descriptor["digest"][7:]
        ).read_text()
    )
    assert observed["schema"] == vo.V2_SCHEMA
    assert observed["execution_environment"] == (
        prepared["execution_environments"][0]
    )
    assert result["policy"] == policy
    assert len(calls) == 1

import json
from pathlib import Path

import pytest

from zog.image_build import ImageBuild
from zog.image_build.remote_contract import REQUEST_SCHEMA
from zog.image_build.remote_operations import RemoteOperations


REPOSITORY = Path(__file__).resolve().parents[1]
REVISION = "a" * 40


def request(operation_id, operation, arguments, predecessor=None):
    value = {
        "schema": REQUEST_SCHEMA,
        "operation_id": operation_id,
        "operation": operation,
        "source": {
            "repository": "zog144/image-build",
            "revision": REVISION,
        },
        "arguments": arguments,
    }
    if predecessor is not None:
        value["predecessor"] = predecessor
    return value


def fixture(tmp_path):
    state = tmp_path / "project" / "state"
    catalogue = REPOSITORY / "project" / "package"
    builder = ImageBuild(package_dir=catalogue, state_dir=state)
    root = tmp_path / "seed-root"
    root.mkdir()
    (root / "seed").write_text("seed")
    seed = builder.import_bootstrap(root, {"fixture": "toolchain-remote"})
    controller = tmp_path / "controller.json"
    controller.write_text("{}")
    remote = RemoteOperations(
        builder,
        repository_root=REPOSITORY,
        source_repository="zog144/image-build",
        source_revision=REVISION,
        controller_config_path=controller,
    )
    return builder, remote, seed, controller


def test_cross_bootstrap_uses_server_owned_paths_only(tmp_path, monkeypatch):
    builder, remote, seed, controller = fixture(tmp_path)
    calls = []

    def run(project, catalogue, plan, actual_controller, seed_path, operation_name):
        calls.append(
            {
                "project": Path(project),
                "catalogue": Path(catalogue),
                "plan": Path(plan),
                "controller": Path(actual_controller),
                "seed": Path(seed_path),
                "operation_name": operation_name,
            }
        )
        work = builder.state / "image-build" / operation_name
        work.mkdir(parents=True, exist_ok=True)
        record = {
            "schema": 1,
            "phase": "complete",
            "stages_generation": "1" * 64,
            "runtime_generation": "2" * 64,
        }
        (work / "operation.json").write_text(json.dumps(record))
        return record

    import zog.image_build.stages as stages
    monkeypatch.setattr(stages, "run", run)

    result = remote.execute(
        request(
            "toolchain-cross",
            "toolchain.submit",
            {
                "phase": "cross-bootstrap",
                "seed_generation": seed.generation,
            },
        )
    )
    assert result["status"] == "completed"
    assert result["selected_generation"] == "2" * 64
    assert result["artifacts"]["toolchain_execution"]["inputs"] == {
        "seed_generation": seed.generation
    }
    assert calls == [
        {
            "project": builder.state.parent,
            "catalogue": REPOSITORY / "project/package",
            "plan": REPOSITORY / "project/bootstrap/lfs-cross.py",
            "controller": controller.resolve(),
            "seed": builder.state
            / "image-build/generations"
            / seed.generation,
            "operation_name": "toolchain-toolchain-cross-cross-bootstrap",
        }
    ]
    binding = json.loads(
        (
            builder.state
            / "image-build/remote-operations/toolchain-cross/binding.json"
        ).read_text()
    )
    encoded = json.dumps(binding)
    assert str(tmp_path) not in encoded
    assert binding["execution_contract"] == (
        "image-build-toolchain-remote-execution-v1"
    )
    assert binding["identity"].startswith("sha256:")


def test_interrupted_phase_resumes_same_bound_operation(tmp_path, monkeypatch):
    builder, remote, seed, _ = fixture(tmp_path)
    calls = []

    def run(project, catalogue, plan, controller, seed_path, operation_name):
        del project, catalogue, plan, controller, seed_path
        calls.append(operation_name)
        work = builder.state / "image-build" / operation_name
        work.mkdir(parents=True, exist_ok=True)
        if len(calls) == 1:
            (work / "operation.json").write_text(
                json.dumps({"schema": 1, "phase": "stages"})
            )
            raise KeyboardInterrupt("simulated lost caller")
        record = {
            "schema": 1,
            "phase": "complete",
            "stages_generation": "3" * 64,
            "runtime_generation": "4" * 64,
        }
        (work / "operation.json").write_text(json.dumps(record))
        return record

    import zog.image_build.stages as stages
    monkeypatch.setattr(stages, "run", run)

    submitted = remote.execute(
        request(
            "toolchain-interrupt",
            "toolchain.submit",
            {
                "phase": "cross-bootstrap",
                "seed_generation": seed.generation,
            },
        )
    )
    assert submitted["status"] == "pending"
    assert submitted["uncertainty"] is True
    resumed = remote.execute(
        request(
            "toolchain-resume",
            "toolchain.resume",
            {"operation_id": "toolchain-interrupt"},
        )
    )
    assert resumed["status"] == "completed"
    assert resumed["selected_generation"] == "4" * 64
    assert calls == [
        "toolchain-toolchain-interrupt-cross-bootstrap",
        "toolchain-toolchain-interrupt-cross-bootstrap",
    ]


def test_next_phase_is_derived_from_predecessor_not_request_paths(
    tmp_path, monkeypatch
):
    builder, remote, seed, _ = fixture(tmp_path)

    import zog.image_build.stages as stages
    def cross_run(project, catalogue, plan, controller, seed_path, operation_name):
        del project, catalogue, plan, controller, seed_path
        work = builder.state / "image-build" / operation_name
        work.mkdir(parents=True, exist_ok=True)
        record = {
            "schema": 1,
            "phase": "complete",
            "stages_generation": "5" * 64,
            "runtime_generation": "6" * 64,
        }
        (work / "operation.json").write_text(json.dumps(record))
        return record
    monkeypatch.setattr(stages, "run", cross_run)
    remote.execute(
        request(
            "cross-for-temp",
            "toolchain.submit",
            {"phase": "cross-bootstrap", "seed_generation": seed.generation},
        )
    )

    seen = {}
    import zog.image_build.temporary as temporary
    def temporary_run(
        project,
        catalogue,
        plan,
        controller,
        seed_path,
        cross_path,
        operation_name,
    ):
        del project, catalogue, plan, controller
        seen["seed"] = Path(seed_path)
        seen["cross"] = Path(cross_path)
        work = builder.state / "image-build" / operation_name
        work.mkdir(parents=True, exist_ok=True)
        record = {
            "schema": 1,
            "phase": "complete",
            "compiler_generation": "7" * 64,
            "packages_generation": "8" * 64,
            "runtime_generation": "9" * 64,
        }
        (work / "operation.json").write_text(json.dumps(record))
        return record
    monkeypatch.setattr(temporary, "run", temporary_run)

    result = remote.execute(
        request(
            "temporary-next",
            "toolchain.submit",
            {"phase": "temporary-userspace"},
            predecessor="cross-for-temp",
        )
    )
    assert result["status"] == "completed"
    assert seen == {
        "seed": builder.state / "image-build/generations" / seed.generation,
        "cross": builder.state / "image-build/generations" / ("5" * 64),
    }
    assert result["artifacts"]["toolchain_execution"]["lineage"] == {
        "cross-bootstrap": "cross-for-temp"
    }


def test_toolchain_requests_refuse_caller_paths_and_wrong_predecessors(
    tmp_path, monkeypatch
):
    builder, remote, seed, _ = fixture(tmp_path)
    result = remote.execute(
        request(
            "bad-path",
            "toolchain.submit",
            {
                "phase": "cross-bootstrap",
                "seed_generation": seed.generation,
                "controller": "/tmp/not-authorized",
            },
        )
    )
    assert result["status"] == "failed"
    assert "accepts only phase and seed_generation" in result["failure"]["reason"]

    import zog.image_build.stages as stages
    def run(project, catalogue, plan, controller, seed_path, operation_name):
        del project, catalogue, plan, controller, seed_path
        work = builder.state / "image-build" / operation_name
        work.mkdir(parents=True, exist_ok=True)
        record = {
            "schema": 1,
            "phase": "complete",
            "stages_generation": "a" * 64,
            "runtime_generation": "b" * 64,
        }
        (work / "operation.json").write_text(json.dumps(record))
        return record
    monkeypatch.setattr(stages, "run", run)
    remote.execute(
        request(
            "good-cross",
            "toolchain.submit",
            {"phase": "cross-bootstrap", "seed_generation": seed.generation},
        )
    )
    wrong = remote.execute(
        request(
            "wrong-next",
            "toolchain.submit",
            {"phase": "final-math"},
            predecessor="good-cross",
        )
    )
    assert wrong["status"] == "failed"
    assert "predecessor phase differs" in wrong["failure"]["reason"]


def test_toolchain_binding_identity_rejects_retained_input_drift(
    tmp_path, monkeypatch
):
    builder, remote, seed, _ = fixture(tmp_path)

    import zog.image_build.stages as stages
    def run(project, catalogue, plan, controller, seed_path, operation_name):
        del project, catalogue, plan, controller, seed_path
        work = builder.state / "image-build" / operation_name
        work.mkdir(parents=True, exist_ok=True)
        (work / "operation.json").write_text(
            json.dumps({"schema": 1, "phase": "stages"})
        )
        raise KeyboardInterrupt("pending")
    monkeypatch.setattr(stages, "run", run)

    remote.execute(
        request(
            "binding-drift",
            "toolchain.submit",
            {"phase": "cross-bootstrap", "seed_generation": seed.generation},
        )
    )
    binding_path = (
        builder.state
        / "image-build/remote-operations/binding-drift/binding.json"
    )
    binding = json.loads(binding_path.read_text())
    binding["inputs"]["seed_generation"] = "0" * 64
    binding_path.write_text(json.dumps(binding))

    inspected = remote.execute(
        request(
            "binding-drift-inspect",
            "toolchain.inspect",
            {"operation_id": "binding-drift"},
        )
    )
    assert inspected["status"] == "failed"
    assert "binding identity changed" in inspected["failure"]["reason"]

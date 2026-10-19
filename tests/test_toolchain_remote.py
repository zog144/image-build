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


def test_full_typed_chain_derives_final_libc_and_compiler_ownership(
    tmp_path, monkeypatch
):
    builder, remote, seed, _ = fixture(tmp_path)
    state = builder.state / "image-build"

    def pipeline(generation, pipeline_id, attempt_id, packages):
        root = state / "pipelines" / pipeline_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "pipeline.json").write_text(
            json.dumps(
                {
                    "pipeline_id": pipeline_id,
                    "generation": generation,
                    "status": "complete",
                    "attempts": {"image": attempt_id},
                }
            )
        )
        package_root = state / "attempts" / attempt_id / "packages"
        for package in packages:
            target = package_root / package
            target.mkdir(parents=True, exist_ok=True)
            (target / "result.json").write_text("{}")

    def record(operation_name, value, filename="operation.json"):
        work = state / operation_name
        work.mkdir(parents=True, exist_ok=True)
        (work / filename).write_text(json.dumps(value))
        return value

    import zog.image_build.stages as stages
    monkeypatch.setattr(
        stages,
        "run",
        lambda project, catalogue, plan, controller, seed_path, operation_name: (
            pipeline("1" * 64, "pipeline-cross", "attempt-cross", ("glibc-cross-initial",))
            or record(
                operation_name,
                {
                    "schema": 1,
                    "phase": "complete",
                    "stages_generation": "1" * 64,
                    "runtime_generation": "2" * 64,
                },
            )
        ),
    )
    cross = remote.execute(
        request(
            "chain-cross",
            "toolchain.submit",
            {"phase": "cross-bootstrap", "seed_generation": seed.generation},
        )
    )
    assert cross["status"] == "completed"

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
        assert Path(seed_path).name == seed.generation
        assert Path(cross_path).name == "1" * 64
        pipeline(
            "4" * 64,
            "pipeline-temporary",
            "attempt-temporary",
            (
                "gcc-temporary-libstdcpp",
                "ncurses-temporary",
                "bash-temporary",
            ),
        )
        return record(
            operation_name,
            {
                "schema": 1,
                "phase": "complete",
                "compiler_generation": "3" * 64,
                "packages_generation": "4" * 64,
                "runtime_generation": "5" * 64,
            },
        )
    monkeypatch.setattr(temporary, "run", temporary_run)
    temporary_result = remote.execute(
        request(
            "chain-temporary",
            "toolchain.submit",
            {"phase": "temporary-userspace"},
            predecessor="chain-cross",
        )
    )
    assert temporary_result["status"] == "completed"

    import zog.image_build.native as native
    def native_run(project, catalogue, controller, inputs, operation_name):
        del project, catalogue, controller
        assert Path(inputs["compiler"]).name == "3" * 64
        assert Path(inputs["runtime"]).name == "5" * 64
        assert Path(inputs["prior_attempt"]).name == "attempt-temporary"
        pipeline(
            "6" * 64,
            "pipeline-native",
            "attempt-native-ownership",
            ("binutils-native-temporary", "gcc-native-temporary"),
        )
        return record(
            operation_name,
            {
                "schema": 1,
                "phase": "complete",
                "packages_generation": "6" * 64,
                "native_generation": "7" * 64,
                "m4_generation": "8" * 64,
            },
        )
    monkeypatch.setattr(native, "run", native_run)
    native_result = remote.execute(
        request(
            "chain-native",
            "toolchain.submit",
            {"phase": "native-transition"},
            predecessor="chain-temporary",
        )
    )
    assert native_result["status"] == "completed"

    import zog.image_build.build_environment as build_environment
    def environment_run(
        project,
        catalogue,
        controller,
        selection,
        operation_name,
    ):
        del project, catalogue, controller
        assert Path(selection).name == "7" * 64
        return record(
            operation_name,
            {"schema": 1, "phase": "complete", "generation": "9" * 64},
        )
    monkeypatch.setattr(build_environment, "run", environment_run)
    environment_result = remote.execute(
        request(
            "chain-environment",
            "toolchain.submit",
            {"phase": "native-environment"},
            predecessor="chain-native",
        )
    )
    assert environment_result["status"] == "completed"

    import zog.image_build.native_stage as native_stage
    def libc_build_run(**kwargs):
        assert Path(kwargs["selection"]).name == "9" * 64
        assert Path(kwargs["plan"]) == REPOSITORY / "project/bootstrap/lfs-final-start.py"
        work = Path(kwargs["work"])
        pipeline(
            "a" * 64,
            "pipeline-final-libc-build",
            "attempt-final-libc",
            ("glibc-final",),
        )
        value = {"schema": 1, "phase": "complete", "generation": "a" * 64}
        work.mkdir(parents=True, exist_ok=True)
        (work / "operation.json").write_text(json.dumps(value))
        return value
    monkeypatch.setattr(native_stage, "run", libc_build_run)
    libc_build = remote.execute(
        request(
            "chain-libc-build",
            "toolchain.submit",
            {"phase": "final-libc-build"},
            predecessor="chain-environment",
        )
    )
    assert libc_build["status"] == "completed"

    import zog.image_build.glibc_final as glibc_final
    def libc_publish_run(
        project,
        attempt,
        base_generation,
        previous_package,
        work,
        recover_empty_mount_directories=False,
        base_directory=None,
    ):
        del project, recover_empty_mount_directories, base_directory
        assert Path(attempt).name == "attempt-final-libc"
        assert base_generation == "9" * 64
        assert Path(previous_package) == (
            state
            / "attempts/attempt-cross/packages/glibc-cross-initial/result.json"
        )
        value = {
            "phase": "complete",
            "generation": "b" * 64,
            "published": True,
        }
        Path(work).mkdir(parents=True, exist_ok=True)
        (Path(work) / "result.json").write_text(json.dumps(value))
        return value
    monkeypatch.setattr(glibc_final, "run", libc_publish_run)
    libc = remote.execute(
        request(
            "chain-libc",
            "toolchain.submit",
            {"phase": "final-libc-publish"},
            predecessor="chain-libc-build",
        )
    )
    assert libc["status"] == "completed"

    import zog.image_build.final_math as final_math
    def math_run(project, catalogue, controller, selection, work):
        del project, catalogue, controller
        assert Path(selection).name == "b" * 64
        value = {
            "phase": "complete",
            "generation": "c" * 64,
            "base_generation": "b" * 64,
        }
        Path(work).mkdir(parents=True, exist_ok=True)
        (Path(work) / "result.json").write_text(json.dumps(value))
        return value
    monkeypatch.setattr(final_math, "run", math_run)
    math = remote.execute(
        request(
            "chain-math",
            "toolchain.submit",
            {"phase": "final-math"},
            predecessor="chain-libc",
        )
    )
    assert math["status"] == "completed"

    import zog.image_build.final_compiler as final_compiler
    def compiler_run(
        project,
        catalogue,
        controller,
        selection,
        arithmetic,
        ownership,
        work,
    ):
        del project, catalogue, controller
        assert Path(selection).name == "b" * 64
        assert Path(arithmetic).name == "c" * 64
        assert Path(ownership) == (
            state / "attempts/attempt-native-ownership/packages"
        )
        value = {
            "phase": "complete",
            "generation": "d" * 64,
            "m4_generation": "e" * 64,
            "toolchain_artifact": {
                "contract": "image-build-toolchain-artifact-v1"
            },
        }
        Path(work).mkdir(parents=True, exist_ok=True)
        (Path(work) / "result.json").write_text(json.dumps(value))
        return value
    monkeypatch.setattr(final_compiler, "run", compiler_run)
    compiler = remote.execute(
        request(
            "chain-compiler",
            "toolchain.submit",
            {"phase": "final-compiler"},
            predecessor="chain-math",
        )
    )
    assert compiler["status"] == "completed"
    assert compiler["selected_generation"] == "d" * 64
    execution = compiler["artifacts"]["toolchain_execution"]
    assert execution["lineage"] == {
        "cross-bootstrap": "chain-cross",
        "temporary-userspace": "chain-temporary",
        "native-transition": "chain-native",
        "native-environment": "chain-environment",
        "final-libc-build": "chain-libc-build",
        "final-libc-publish": "chain-libc",
        "final-math": "chain-math",
    }

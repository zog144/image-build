import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import pytest

from zog.image_build import ImageBuild
from zog.image_build.errors import ImageBuildError
from zog.image_build.remote_operations import (
    MAX_INVENTORY_ITEMS,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    RemoteOperations,
    _validated_monthly_provenance_pin,
    _validated_observed_state_dir,
)
from zog.image_build.runner import BoxControlRunner, BuildExecutionResult


def recipe(root, name, *, build=(), runtime=(), command="compile"):
    path = root / name
    path.mkdir(parents=True)
    payload = path / "payload.txt"
    payload.write_text(name)
    sources = [{
        "url": payload.resolve().as_uri(),
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
        "destination": "payload.txt",
        "archive": False,
    }]
    (path / "sources.py").write_text(repr(sources))
    (path / "dependencies.py").write_text(repr({"build": list(build), "runtime": list(runtime)}))
    (path / "build.py").write_text(repr({
        "build": [[command, name]],
        "install": [["install", name]],
    }))
    (path / "produce-manifest.py").write_text(repr(["usr/share/" + name]))
    pin = root / "commit-pin.py"
    value = ast.literal_eval(pin.read_text()) if pin.exists() else {
        "schema": 1, "date": "2026-10-01", "packages": {}
    }
    value["packages"][name] = {"sources": sources}
    pin.write_text(repr(value))

    (path / "license.py").write_text(
        repr(
            {
                "schema": 1,
                "package": name,
                "version": "fixture",
                "source": {
                    "url": sources[0]["url"],
                    "sha256": sources[0]["sha256"],
                },
                "status": "unresolved",
                "expression": None,
                "scope": "package",
                "evidence": [],
                "components": [],
                "patches": [],
                "notes": ["fixture"],
            }
        )
    )
    monthly_path = (
        root.parent
        / "pins"
        / "2026-10-01"
        / "commit-pin.py"
    )
    monthly_path.parent.mkdir(parents=True, exist_ok=True)
    monthly = (
        ast.literal_eval(monthly_path.read_text())
        if monthly_path.exists()
        else {
            "schema": 1,
            "date": "2026-10-01",
            "packages": {},
        }
    )
    monthly["packages"][name] = {
        "recipes": {name: sources}
    }
    monthly_path.write_text(repr(monthly))
    (root.parent / "pins/current.py").write_text(
        repr({"date": "2026-10-01"})
    )


class RecipeRunner:
    def run(self, root, source, output, arguments, environment, log):
        Path(log).write_text(repr(arguments))
        if arguments[0] == "install":
            target = Path(output) / "usr/share" / arguments[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(arguments[1])


def setup_repo(tmp_path):
    repository = tmp_path / "repository"
    packages = repository / "project" / "package"
    packages.mkdir(parents=True)
    recipe(packages, "compiler-first")
    recipe(packages, "compiler-second")
    recipe(packages, "library")
    recipe(packages, "consumer", runtime=("library",))
    builder = ImageBuild(package_dir=packages, state_dir=tmp_path / "state", runner=RecipeRunner())
    host = tmp_path / "host"
    host.mkdir()
    (host / "seed").write_text("seed")
    seed = builder.import_bootstrap(host, {"fixture": True})
    toolchain = builder.bootstrap(seed, [["compiler-first"], ["compiler-second"]])
    return repository, packages, builder, toolchain


def request(operation_id, operation, arguments, revision="a" * 40, predecessor=None):
    value = {
        "schema": REQUEST_SCHEMA,
        "operation_id": operation_id,
        "operation": operation,
        "source": {"repository": "zog144/image-build", "revision": revision},
        "arguments": arguments,
    }
    if predecessor is not None:
        value["predecessor"] = predecessor
    return value


def adapter(repository, builder, revision="a" * 40):
    return RemoteOperations(
        builder,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision=revision,
    )


def recipe_entries(*package_names):
    return [
        {"id": name, "project": name, "recipe": name}
        for name in package_names
    ]


def remote_recipe_snapshot(
    remote,
    operation_id,
    *package_names,
    revision="a" * 40,
):
    result = remote.execute(
        request(
            operation_id,
            "recipes.snapshot",
            {
                "entries": recipe_entries(*package_names),
                "pin_date": "2026-10-01",
            },
            revision=revision,
        )
    )
    assert result["status"] == "completed", result
    assert result["recipe_identity"].startswith("sha256:")
    return result["recipe_identity"]


def test_recipe_inspection_and_dependency_resolution(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    remote = adapter(repository, builder)

    validated = remote.execute(request("validate", "recipe.validate", {"package": "consumer"}))
    assert validated["schema"] == RESULT_SCHEMA
    assert validated["status"] == "completed"

    inspected = remote.execute(request("inspect", "package.inspect", {"package": "consumer"}))
    assert inspected["recipe_identity"]
    assert inspected["artifacts"]["runtime_dependencies"] == ["library"]

    dependencies = remote.execute(request(
        "dependencies", "dependencies.resolve", {"targets": ["consumer"]}
    ))
    assert dependencies["artifacts"]["dependency_order"][-2:] == ["library", "consumer"]


def test_invalid_recipe_and_missing_package_are_bounded_failures(tmp_path):
    repository, packages, builder, _ = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    missing = remote.execute(request("missing", "package.inspect", {"package": "absent"}))
    assert missing["status"] == "failed"
    assert missing["terminal_outcome"] == "request-error"

    (packages / "consumer" / "build.py").write_text("{'build': [['cc']]}")
    invalid = remote.execute(request("invalid", "recipe.validate", {"package": "consumer"}))
    assert invalid["status"] == "failed"
    assert invalid["failure"]["type"] == "ImageBuildError"


def test_duplicate_operation_rejects_changed_input(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    first = request("same-id", "package.inspect", {"package": "consumer"})
    assert remote.execute(first)["status"] == "completed"
    changed = request("same-id", "package.inspect", {"package": "library"})
    with pytest.raises(ImageBuildError, match="different input"):
        remote.execute(changed)


def test_remote_submit_persists_pipeline_identity_before_pending_return(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)

    def pending(request):
        raise KeyboardInterrupt("caller disconnected")

    # Simulate a durable controller handoff that has not completed.
    builder.runner = BoxControlRunner(execute=pending)
    remote = adapter(repository, builder)
    snapshot = remote_recipe_snapshot(
        remote, "snapshot-consumer", "library", "consumer"
    )
    submit_arguments = {
        "mode": "image",
        "selection": toolchain.generation,
        "targets": ["consumer"],
        "recipe_snapshot": snapshot,
    }
    result = remote.execute(request(
        "build-consumer",
        "pipeline.submit",
        submit_arguments,
    ))
    assert result["status"] == "pending"
    binding = json.loads(
        (builder.state / "image-build/remote-operations/build-consumer/binding.json").read_text()
    )
    pipeline = builder.inspect_pipeline(binding["pipeline_id"])
    assert pipeline["owner"]["operation_id"] == "build-consumer"
    assert pipeline["owner"]["source_revision"] == "a" * 40

    # Repeating the exact client request discovers the same pipeline.
    again = remote.execute(request(
        "build-consumer",
        "pipeline.submit",
        submit_arguments,
    ))
    assert again["pipeline_id"] == result["pipeline_id"]


def test_terminal_failed_build_requires_explicit_new_retry_and_can_use_new_revision(tmp_path):
    repository, packages, builder, toolchain = setup_repo(tmp_path)

    def fail_compile(build_request):
        return BuildExecutionResult(
            "runtime", "invocation", 7 if build_request.command[0] == "compile" else 0,
            True, "journal:fixture",
        )

    builder.runner = BoxControlRunner(execute=fail_compile)
    first_remote = adapter(repository, builder, "a" * 40)
    first_snapshot = remote_recipe_snapshot(
        first_remote,
        "snapshot-attempt-a",
        "library",
        revision="a" * 40,
    )
    failed = first_remote.execute(request(
        "attempt-a",
        "pipeline.submit",
        {
            "mode": "image",
            "selection": toolchain.generation,
            "targets": ["library"],
            "recipe_snapshot": first_snapshot,
        },
        revision="a" * 40,
    ))
    assert failed["status"] == "failed"
    assert "pipeline.retry" in failed["allowed_next_operations"]

    # A corrected commit may carry changed recipe bytes, but the old pipeline stays frozen.
    recipe_path = packages / "library" / "build.py"
    recipe_path.write_text(repr({
        "build": [["compile-fixed", "library"]],
        "install": [["install", "library"]],
    }))

    def succeed(build_request):
        if build_request.command[0] == "install":
            target = build_request.output / "usr/share/library"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("library")
        return BuildExecutionResult("runtime", "invocation", 0, True, "journal:fixture")

    builder.runner = BoxControlRunner(execute=succeed)
    second_remote = adapter(repository, builder, "b" * 40)
    second_snapshot = remote_recipe_snapshot(
        second_remote,
        "snapshot-attempt-b",
        "library",
        revision="b" * 40,
    )
    assert second_snapshot != first_snapshot
    retried = second_remote.execute(request(
        "attempt-b",
        "pipeline.retry",
        {
            "mode": "image",
            "selection": toolchain.generation,
            "targets": ["library"],
            "recipe_snapshot": second_snapshot,
        },
        revision="b" * 40,
        predecessor="attempt-a",
    ))
    assert retried["status"] == "completed"
    assert retried["predecessor"] == "attempt-a"
    assert retried["pipeline_id"] != failed["pipeline_id"]
    assert builder.inspect_pipeline(failed["pipeline_id"])["status"] == "released"


def test_resume_refuses_a_different_deployed_revision(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    builder.runner = BoxControlRunner(execute=lambda request: (_ for _ in ()).throw(KeyboardInterrupt()))
    first = adapter(repository, builder, "a" * 40)
    snapshot = remote_recipe_snapshot(
        first, "snapshot-owned", "library"
    )
    submitted = first.execute(request(
        "owned",
        "pipeline.submit",
        {
            "mode": "image",
            "selection": toolchain.generation,
            "targets": ["library"],
            "recipe_snapshot": snapshot,
        },
    ))
    second = adapter(repository, builder, "b" * 40)
    result = second.execute(request(
        "resume-wrong",
        "pipeline.resume",
        {"pipeline_id": submitted["pipeline_id"]},
        revision="b" * 40,
    ))
    assert result["status"] == "failed"
    assert "originally bound" in result["failure"]["reason"]


def test_diagnostic_definition_rejects_shell_and_network_escape(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    root = repository / "project" / "diagnostic" / "bad"
    root.mkdir(parents=True)
    (root / "diagnostic.sh").write_text("#!/bin/sh\ntrue\n")
    (root / "diagnostic.json").write_text(json.dumps({
        "schema": 1,
        "script": "diagnostic.sh",
        "interpreter": "/bin/sh",
        "timeout_seconds": 10,
        "memory_maximum_bytes": 1000000,
        "thread_count_maximum": 4,
        "cpu_weight": 10,
        "output_limit_bytes": 1024,
        "outputs": [],
    }))
    remote = adapter(repository, builder)
    result = remote.execute(request(
        "diagnostic-bad",
        "diagnostic.submit",
        {"diagnostic": "bad", "generation": toolchain.generation, "argv": []},
    ))
    assert result["status"] == "failed"
    assert "Python source" in result["failure"]["reason"]


def test_source_binding_must_match_deployed_revision(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    remote = adapter(repository, builder, "a" * 40)
    with pytest.raises(ImageBuildError, match="differs from deployed"):
        remote.execute(request(
            "wrong-source",
            "package.inspect",
            {"package": "library"},
            revision="b" * 40,
        ))


def test_machine_result_schema_has_stable_core_fields(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    result = adapter(repository, builder).execute(
        request("schema", "package.inspect", {"package": "library"})
    )
    assert set(result) == {
        "schema", "operation_id", "operation_type", "source_repository",
        "source_revision", "recipe_identity", "pipeline_id", "attempt_ids",
        "selected_generation", "package", "stage", "phase", "status",
        "terminal_outcome", "failure", "controller_jobs", "log_locators",
        "artifacts", "provenance", "uncertainty", "missing_evidence",
        "allowed_next_operations", "predecessor",
    }


def test_cancel_releases_owned_prepared_pipeline_without_retry(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    record = builder.prepare_pipeline(
        "image",
        toolchain,
        owner={
            "contract": REQUEST_SCHEMA,
            "operation_id": "prepared-owner",
            "source_repository": "zog144/image-build",
            "source_revision": "a" * 40,
        },
        targets=["library"],
    )
    cancelled = remote.execute(request(
        "cancel-prepared",
        "pipeline.cancel",
        {"pipeline_id": record["pipeline_id"]},
    ))
    assert cancelled["status"] == "released"
    assert cancelled["terminal_outcome"] == "released"
    assert cancelled["allowed_next_operations"] == ["pipeline.inspect"]
    assert builder.inspect_pipeline(record["pipeline_id"])["status"] == "released"


def test_cancel_refuses_pipeline_owned_by_other_source_revision(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    record = builder.prepare_pipeline(
        "image",
        toolchain,
        owner={
            "contract": REQUEST_SCHEMA,
            "operation_id": "foreign-owner",
            "source_repository": "zog144/image-build",
            "source_revision": "b" * 40,
        },
        targets=["library"],
    )
    result = adapter(repository, builder, "a" * 40).execute(request(
        "cancel-foreign",
        "pipeline.cancel",
        {"pipeline_id": record["pipeline_id"]},
    ))
    assert result["status"] == "failed"
    assert "originally bound" in result["failure"]["reason"]
    assert builder.inspect_pipeline(record["pipeline_id"])["status"] == "prepared"


def test_state_local_pipeline_serialization_allows_independent_lanes(tmp_path):
    repository_a, _, builder_a, toolchain_a = setup_repo(tmp_path / "lane-a")
    repository_b, _, builder_b, toolchain_b = setup_repo(tmp_path / "lane-b")
    first = builder_a.prepare_pipeline(
        "image",
        toolchain_a,
        owner={
            "contract": REQUEST_SCHEMA,
            "operation_id": "lane-a",
            "source_repository": "zog144/image-build",
            "source_revision": "a" * 40,
        },
        targets=["library"],
    )
    with pytest.raises(ImageBuildError, match="unfinished pipeline"):
        builder_a.prepare_pipeline(
            "image",
            toolchain_a,
            owner={
                "contract": REQUEST_SCHEMA,
                "operation_id": "lane-a-second",
                "source_repository": "zog144/image-build",
                "source_revision": "a" * 40,
            },
            targets=["consumer"],
        )
    second = builder_b.prepare_pipeline(
        "image",
        toolchain_b,
        owner={
            "contract": REQUEST_SCHEMA,
            "operation_id": "lane-b",
            "source_repository": "zog144/image-build",
            "source_revision": "a" * 40,
        },
        targets=["library"],
    )
    assert first["pipeline_id"] != second["pipeline_id"]
    assert builder_a.state != builder_b.state
    assert repository_a != repository_b


def test_concurrent_duplicate_submit_reuses_one_durable_pipeline(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    snapshot = remote_recipe_snapshot(
        remote, "snapshot-concurrent", "library"
    )
    payload = request(
        "concurrent-submit",
        "pipeline.submit",
        {
            "mode": "image",
            "selection": toolchain.generation,
            "targets": ["library"],
            "recipe_snapshot": snapshot,
        },
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(remote.execute, [payload, payload]))
    assert {item["pipeline_id"] for item in results} == {results[0]["pipeline_id"]}
    owned = []
    for path in (builder.state / "image-build/pipelines").glob("*/pipeline.json"):
        record = json.loads(path.read_text())
        if (record.get("owner") or {}).get("operation_id") == "concurrent-submit":
            owned.append(record)
    assert len(owned) == 1


def test_unresolved_controller_cleanup_is_not_retryable_failure(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    record = builder.prepare_pipeline(
        "image",
        toolchain,
        owner={
            "contract": REQUEST_SCHEMA,
            "operation_id": "cleanup-owner",
            "source_repository": "zog144/image-build",
            "source_revision": "a" * 40,
        },
        targets=["library"],
    )
    attempt = builder.state / "image-build/attempts/cleanup-pending-fixture"
    attempt.mkdir(parents=True)
    (attempt / "failure.observation.json").write_text(json.dumps({
        "job_id": "fixture-job",
        "state": "completed",
        "outcome": "nonzero-exit",
        "exit_code": 7,
        "journal_reference": "journal:fixture-job",
        "process_cleanup_complete": False,
    }))
    record["attempts"] = {"image": attempt.name}
    record["status"] = "pending"
    record["error"] = "controller cleanup remains unresolved"
    pipeline_path = (
        builder.state
        / "image-build/pipelines"
        / record["pipeline_id"]
        / "pipeline.json"
    )
    pipeline_path.write_text(json.dumps(record))
    result = remote.execute(request(
        "inspect-cleanup-pending",
        "pipeline.inspect",
        {"pipeline_id": record["pipeline_id"]},
    ))
    assert result["status"] == "pending"
    assert "pipeline.retry" not in result["allowed_next_operations"]
    assert "pipeline.cancel" in result["allowed_next_operations"]


def test_generation_inspection_bounds_inventory_without_losing_digest(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    root = tmp_path / "large-generation-root"
    root.mkdir()
    for index in range(MAX_INVENTORY_ITEMS + 17):
        (root / f"file-{index:03d}").write_text(str(index))
    selection = builder.import_bootstrap(root, {"fixture": "large"})
    result = adapter(repository, builder).execute(request(
        "inspect-large-generation",
        "generation.inspect",
        {"generation": selection.generation},
    ))
    artifacts = result["artifacts"]
    assert len(artifacts["inventory"]) == MAX_INVENTORY_ITEMS
    assert artifacts["inventory_count"] == MAX_INVENTORY_ITEMS + 17
    assert artifacts["inventory_truncated"] is True
    assert artifacts["inventory_digest"].startswith("sha256:")
    assert artifacts["generation_manifest"].endswith("/manifest.json")


class _FakeRemoteProvenance:
    captures = []

    @staticmethod
    def capture_pin(
        state_dir, path, *, repository, revision, repository_path
    ):
        raw = Path(path).read_bytes()
        record = ast.literal_eval(raw.decode())
        value = {
            "month": record["date"],
            "repository": repository,
            "revision": revision,
            "path": repository_path,
            "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        }
        _FakeRemoteProvenance.captures.append(value)
        return value

    def __init__(self, state_dir, *, host_id, project_id, pin):
        self.state = Path(state_dir)
        self.host_id = host_id
        self.project_id = project_id
        self.pin = pin

    def configuration(self):
        return {
            "schema": 2,
            "host_id": self.host_id,
            "project_id": self.project_id,
            "pin": self.pin,
            "retry_of": {},
            "generation_contract": "rootfs-v1",
        }


def _prepared_inspection_state(state, pipeline_id):
    path = state / "image-build/pipelines" / pipeline_id
    path.mkdir(parents=True)
    (path / "pipeline.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "pipeline_id": pipeline_id,
                "status": "prepared",
                "attempts": {},
            }
        )
    )


def test_remote_cli_pipeline_inspect_uses_explicit_real_monthly_pin(
    tmp_path, monkeypatch, capsys
):
    from zog.image_build import provenance
    from zog.image_build import remote_operations

    repository = Path(__file__).resolve().parents[1]
    package_dir = repository / "project/package"
    pin = repository / "project/pins/2026-10-01/commit-pin.py"
    assert package_dir.is_dir()
    assert not (package_dir / "commit-pin.py").exists()
    digest = "sha256:" + hashlib.sha256(pin.read_bytes()).hexdigest()

    state = tmp_path / "state"
    pipeline_id = "1" * 32
    _prepared_inspection_state(state, pipeline_id)
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            request(
                "pass4-read-only",
                "pipeline.inspect",
                {"pipeline_id": pipeline_id},
            )
        )
    )

    _FakeRemoteProvenance.captures = []
    monkeypatch.setattr(
        provenance, "Provenance", _FakeRemoteProvenance
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "remote_operations",
            "--repository-root",
            str(repository),
            "--source-repository",
            "zog144/image-build",
            "--source-revision",
            "a" * 40,
            "--package-dir",
            str(package_dir),
            "--state-dir",
            str(state),
            "--provenance-host-id",
            "host",
            "--provenance-project-id",
            "project",
            "--provenance-pin",
            str(pin),
            "--expected-pin-digest",
            digest,
            str(request_path),
        ],
    )
    remote_operations.main()
    result = json.loads(capsys.readouterr().out)
    assert result["operation_type"] == "pipeline.inspect"
    assert result["pipeline_id"] == pipeline_id
    assert result["status"] == "pending"
    assert _FakeRemoteProvenance.captures == [
        {
            "month": "2026-10-01",
            "repository": "zog144/image-build",
            "revision": "a" * 40,
            "path": "project/pins/2026-10-01/commit-pin.py",
            "digest": digest,
        }
    ]


def test_explicit_monthly_pin_rejects_wrong_digest(tmp_path):
    repository = tmp_path / "repository"
    pin = repository / "project/pins/2026-10-01/commit-pin.py"
    pin.parent.mkdir(parents=True)
    pin.write_text(
        repr({"schema": 1, "date": "2026-10-01", "packages": {}})
    )
    with pytest.raises(
        ImageBuildError, match="digest differs"
    ):
        _validated_monthly_provenance_pin(
            repository.resolve(),
            pin.resolve(),
            "sha256:" + "0" * 64,
        )


def test_explicit_monthly_pin_rejects_outside_symlink_and_missing(
    tmp_path,
):
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside-pin.py"
    outside.write_text(
        repr({"schema": 1, "date": "2026-10-01", "packages": {}})
    )
    outside_digest = (
        "sha256:" + hashlib.sha256(outside.read_bytes()).hexdigest()
    )
    with pytest.raises(ImageBuildError, match="inside"):
        _validated_monthly_provenance_pin(
            repository.resolve(), outside.resolve(), outside_digest
        )

    link = repository / "pin-link.py"
    link.symlink_to(outside)
    with pytest.raises(ImageBuildError, match="symlink"):
        _validated_monthly_provenance_pin(
            repository.resolve(), link.absolute(), outside_digest
        )

    with pytest.raises(ImageBuildError, match="missing"):
        _validated_monthly_provenance_pin(
            repository.resolve(),
            (repository / "missing.py").absolute(),
            "sha256:" + "1" * 64,
        )


def test_materialized_recipe_pin_is_not_original_provenance_pin(tmp_path):
    repository = tmp_path / "repository"
    pin = repository / "snapshot/commit-pin.py"
    pin.parent.mkdir(parents=True)
    pin.write_text(
        repr(
            {
                "schema": 1,
                "date": "2026-10-01",
                "monthly_identity": "a" * 64,
                "packages": {},
            }
        )
    )
    digest = "sha256:" + hashlib.sha256(pin.read_bytes()).hexdigest()
    with pytest.raises(
        ImageBuildError, match="recipe-snapshot"
    ):
        _validated_monthly_provenance_pin(
            repository.resolve(), pin.resolve(), digest
        )


def _tree_fingerprint(root):
    records = []
    root = Path(root)
    for path in sorted(root.rglob("*")):
        stat = path.lstat()
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            payload = ("symlink", path.readlink().as_posix())
        elif path.is_file():
            payload = (
                "file",
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        elif path.is_dir():
            payload = ("directory", None)
        else:
            payload = ("other", None)
        records.append(
            (
                relative,
                stat.st_mode,
                stat.st_size,
                stat.st_mtime_ns,
                payload,
            )
        )
    return records


def _external_observation_fixture(tmp_path):
    repository, _, control, _ = setup_repo(tmp_path / "control")
    _, _, observed_builder, _ = setup_repo(tmp_path / "observed")
    observed = observed_builder.state

    unique_root = tmp_path / "observed-generation"
    unique_root.mkdir()
    (unique_root / "retained").write_text("external-generation")
    selection = observed_builder.import_bootstrap(
        unique_root, {"fixture": "external-observed"}
    )

    pipeline_id = "c" * 32
    attempt_name = "external-attempt"
    attempt = observed / "image-build/attempts" / attempt_name
    attempt.mkdir(parents=True)
    (attempt / "failure.observation.json").write_text(
        json.dumps(
            {
                "job_id": "observed-job",
                "state": "completed",
                "outcome": "nonzero-exit",
                "exit_code": 9,
                "journal_reference": "journal:observed-job",
                "process_cleanup_complete": True,
            }
        )
    )
    pipeline = {
        "schema": 1,
        "pipeline_id": pipeline_id,
        "operation": "image",
        "selection": "retained-selection",
        "arguments": {"targets": ["fixture"]},
        "recipes": [],
        "policy": None,
        "source_pins": "fixture",
        "attempts": {"image": attempt_name},
        "status": "pending",
        "error": "retained terminal failure",
        "generation": selection.generation,
    }
    pipeline_path = (
        observed
        / "image-build/pipelines"
        / pipeline_id
        / "pipeline.json"
    )
    pipeline_path.parent.mkdir(parents=True)
    pipeline_path.write_text(json.dumps(pipeline, sort_keys=True))

    # Same pipeline identity in control state deliberately disagrees. External
    # observation must never substitute it.
    control_path = (
        control.state
        / "image-build/pipelines"
        / pipeline_id
        / "pipeline.json"
    )
    control_path.parent.mkdir(parents=True)
    control_path.write_text(
        json.dumps(
            {
                "schema": 1,
                "pipeline_id": pipeline_id,
                "status": "released",
                "attempts": {},
            },
            sort_keys=True,
        )
    )
    return (
        repository,
        control,
        observed,
        pipeline_id,
        pipeline_path,
        selection,
    )


def test_external_observed_pipeline_inspection_is_read_only_and_isolated(
    tmp_path,
):
    (
        repository,
        control,
        observed,
        pipeline_id,
        pipeline_path,
        selection,
    ) = _external_observation_fixture(tmp_path)
    before = _tree_fingerprint(observed)
    expected_digest = (
        "sha256:"
        + hashlib.sha256(pipeline_path.read_bytes()).hexdigest()
    )

    remote = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=observed,
    )
    result = remote.execute(
        request(
            "external-inspect",
            "pipeline.inspect",
            {"pipeline_id": pipeline_id},
        )
    )

    assert result["status"] == "failed"
    assert result["terminal_outcome"] == "nonzero-exit"
    assert result["pipeline_id"] == pipeline_id
    assert result["selected_generation"] == selection.generation
    assert result["allowed_next_operations"] == ["pipeline.inspect"]
    assert result["failure"]["job_id"] == "observed-job"
    assert result["failure"]["exit_code"] == 9
    assert result["log_locators"][0]["locator"].startswith(
        "image-build/attempts/external-attempt/"
    )
    assert result["artifacts"]["generation_manifest"] == (
        "image-build/generations/"
        + selection.generation
        + "/manifest.json"
    )
    assert result["artifacts"]["observation_source"] == {
        "kind": "external-state",
        "pipeline_record_sha256": expected_digest,
    }

    operation = (
        control.state
        / "image-build/remote-operations/external-inspect"
    )
    assert (operation / "request.json").is_file()
    assert (operation / "result.json").is_file()
    binding = json.loads((operation / "binding.json").read_text())
    assert binding == {
        "observation_source": {
            "kind": "external-state",
            "state_dir": str(observed.resolve()),
            "pipeline_id": pipeline_id,
        }
    }
    assert not (
        observed / "image-build/remote-operations"
    ).exists()
    assert _tree_fingerprint(observed) == before


def test_external_observed_missing_pipeline_never_falls_back_to_control(
    tmp_path,
):
    repository, _, control, _ = setup_repo(tmp_path / "control")
    observed = tmp_path / "historical/state"
    observed.mkdir(parents=True)
    pipeline_id = "d" * 32
    control_path = (
        control.state
        / "image-build/pipelines"
        / pipeline_id
        / "pipeline.json"
    )
    control_path.parent.mkdir(parents=True)
    control_path.write_text(
        json.dumps(
            {
                "schema": 1,
                "pipeline_id": pipeline_id,
                "status": "complete",
                "attempts": {},
            }
        )
    )
    before = _tree_fingerprint(observed)
    result = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=observed,
    ).execute(
        request(
            "missing-external",
            "pipeline.inspect",
            {"pipeline_id": pipeline_id},
        )
    )
    assert result["status"] == "pending"
    assert result["uncertainty"] is True
    assert result["missing_evidence"] == [
        {"kind": "pipeline-record", "locator": pipeline_id}
    ]
    assert result["artifacts"]["observation_source"] == {
        "kind": "external-state"
    }
    assert _tree_fingerprint(observed) == before


@pytest.mark.parametrize(
    "operation",
    [
        "pipeline.submit",
        "pipeline.resume",
        "pipeline.cancel",
        "pipeline.retry",
        "generation.inspect",
        "diagnostic.submit",
        "diagnostic.inspect",
        "package.inspect",
        "recipe.validate",
        "recipes.snapshot",
        "worker.inspect",
        "dependencies.resolve",
    ],
)
def test_external_observed_state_rejects_every_non_inspection_operation(
    tmp_path, operation
):
    repository, _, control, _ = setup_repo(tmp_path / "control")
    observed = tmp_path / "historical/state"
    observed.mkdir(parents=True)
    remote = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=observed,
    )
    before = _tree_fingerprint(observed)
    with pytest.raises(
        ImageBuildError, match="permits only pipeline.inspect"
    ):
        remote.execute(
            request(
                "blocked-" + operation.replace(".", "-"),
                operation,
                {},
            )
        )
    assert _tree_fingerprint(observed) == before


def test_external_request_cannot_override_observed_state_path(tmp_path):
    repository, _, control, _ = setup_repo(tmp_path / "control")
    observed = tmp_path / "historical/state"
    observed.mkdir(parents=True)
    other = tmp_path / "other/state"
    other.mkdir(parents=True)
    remote = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=observed,
    )
    result = remote.execute(
        request(
            "path-injection",
            "pipeline.inspect",
            {
                "pipeline_id": "e" * 32,
                "observed_state_dir": str(other),
            },
        )
    )
    assert result["status"] == "failed"
    assert result["terminal_outcome"] == "request-error"
    assert "requires pipeline_id" in result["failure"]["reason"]


def test_external_observed_state_path_validation(tmp_path):
    control = tmp_path / "control"
    control.mkdir()
    observed = (
        tmp_path
        / "var/lib/station-access/zog-compiler-view/state"
    )
    observed.mkdir(parents=True)
    assert _validated_observed_state_dir(
        control.resolve(), observed.resolve()
    ) == observed.resolve()

    link = tmp_path / "observed-link"
    link.symlink_to(observed, target_is_directory=True)
    with pytest.raises(ImageBuildError, match="must not be a symlink"):
        _validated_observed_state_dir(control.resolve(), link.absolute())

    with pytest.raises(ImageBuildError, match="must differ"):
        _validated_observed_state_dir(
            control.resolve(), control.resolve()
        )

    with pytest.raises(ImageBuildError, match="absolute"):
        _validated_observed_state_dir(
            control.resolve(), Path("relative/state")
        )


def test_external_observation_binding_cannot_change_on_duplicate_operation(
    tmp_path,
):
    repository, _, control, _ = setup_repo(tmp_path / "control")
    first = tmp_path / "first/state"
    second = tmp_path / "second/state"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    pipeline_id = "f" * 32
    first_remote = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=first,
    )
    first_remote.execute(
        request(
            "bound-observation",
            "pipeline.inspect",
            {"pipeline_id": pipeline_id},
        )
    )
    second_remote = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=second,
    )
    rejected = second_remote.execute(
        request(
            "bound-observation",
            "pipeline.inspect",
            {"pipeline_id": pipeline_id},
        )
    )
    assert rejected["status"] == "failed"
    assert rejected["terminal_outcome"] == "request-error"
    assert "binding changed" in rejected["failure"]["reason"]


def test_external_inspection_never_queries_control_lane_logs(
    tmp_path, monkeypatch
):
    (
        repository,
        control,
        observed,
        pipeline_id,
        _,
        _,
    ) = _external_observation_fixture(tmp_path)
    calls = []

    class Control:
        def build_job_logs(self, *args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("external inspection queried live logs")

    def execute(_request):
        raise AssertionError("external inspection executed a build command")

    execute.control = Control()
    control.runner = BoxControlRunner(execute=execute)
    monkeypatch.setattr(
        "zog.image_build.remote_operations.read_build_commands",
        lambda attempt, limit: {
            "commands": [
                {
                    "job_id": "observed-job",
                    "request_id": "observed-request",
                    "attempt_id": "external-attempt",
                    "package": "fixture",
                    "stage_id": "stage",
                    "phase": "verify",
                    "command_index": 0,
                    "command_key": "fixture.view.json",
                    "command": ["/bin/true"],
                }
            ]
        },
    )
    result = RemoteOperations(
        control,
        repository_root=repository,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        observed_state_dir=observed,
    ).execute(
        request(
            "no-live-logs",
            "pipeline.inspect",
            {"pipeline_id": pipeline_id},
        )
    )
    assert result["controller_jobs"][0]["job_id"] == "observed-job"
    assert "log_excerpt" not in result["controller_jobs"][0]
    assert calls == []


def test_remote_cli_external_pipeline_inspect_needs_no_controller(
    tmp_path, monkeypatch, capsys
):
    from zog.image_build import provenance
    from zog.image_build import remote_operations

    repository = Path(__file__).resolve().parents[1]
    package_dir = repository / "project/package"
    pin = repository / "project/pins/2026-10-01/commit-pin.py"
    digest = "sha256:" + hashlib.sha256(pin.read_bytes()).hexdigest()

    control = tmp_path / "gateway-pass4-readonly/state"
    observed = (
        tmp_path
        / "var/lib/station-access/zog-compiler-view/state"
    )
    observed.mkdir(parents=True)
    pipeline_id = "7" * 32
    pipeline_path = (
        observed
        / "image-build/pipelines"
        / pipeline_id
        / "pipeline.json"
    )
    pipeline_path.parent.mkdir(parents=True)
    pipeline_path.write_text(
        json.dumps(
            {
                "schema": 1,
                "pipeline_id": pipeline_id,
                "status": "complete",
                "attempts": {},
            },
            sort_keys=True,
        )
    )
    expected_pipeline_digest = (
        "sha256:"
        + hashlib.sha256(pipeline_path.read_bytes()).hexdigest()
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            request(
                "pass4-external-read-only",
                "pipeline.inspect",
                {"pipeline_id": pipeline_id},
            )
        )
    )

    _FakeRemoteProvenance.captures = []
    monkeypatch.setattr(
        provenance, "Provenance", _FakeRemoteProvenance
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "remote_operations",
            "--repository-root",
            str(repository),
            "--source-repository",
            "zog144/image-build",
            "--source-revision",
            "a" * 40,
            "--package-dir",
            str(package_dir),
            "--state-dir",
            str(control),
            "--observed-state-dir",
            str(observed),
            "--provenance-host-id",
            "host",
            "--provenance-project-id",
            "gateway-pass4-readonly",
            "--provenance-pin",
            str(pin),
            "--expected-pin-digest",
            digest,
            str(request_path),
        ],
    )
    remote_operations.main()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "completed"
    assert result["allowed_next_operations"] == ["pipeline.inspect"]
    assert result["artifacts"]["observation_source"] == {
        "kind": "external-state",
        "pipeline_record_sha256": expected_pipeline_digest,
    }
    assert (
        control
        / "image-build/remote-operations/pass4-external-read-only/result.json"
    ).is_file()
    assert not (
        observed / "image-build/remote-operations"
    ).exists()


def test_recipe_snapshot_is_deterministic_and_pipeline_binds_exact_selection(
    tmp_path,
):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    first = remote.execute(
        request(
            "snapshot-first",
            "recipes.snapshot",
            {
                "entries": recipe_entries("library", "consumer"),
                "pin_date": "2026-10-01",
            },
        )
    )
    second = remote.execute(
        request(
            "snapshot-second",
            "recipes.snapshot",
            {
                "entries": recipe_entries("consumer", "library"),
                "pin_date": "2026-10-01",
            },
        )
    )
    assert first["status"] == second["status"] == "completed"
    assert first["recipe_identity"] == second["recipe_identity"]
    snapshot = first["recipe_identity"]
    manifest_path = (
        builder.state
        / "image-build/recipe-snapshots/snapshots"
        / snapshot[7:]
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["contract"] == "image-build-recipe-snapshot-v1"
    assert manifest["entries"] == recipe_entries("consumer", "library")
    assert manifest["monthly_identity"].startswith("sha256:")

    builder.runner = BoxControlRunner(
        execute=lambda request: (_ for _ in ()).throw(
            KeyboardInterrupt()
        )
    )
    submitted = remote.execute(
        request(
            "snapshot-bound-submit",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["consumer"],
                "recipe_snapshot": snapshot,
            },
        )
    )
    pipeline = builder.inspect_pipeline(submitted["pipeline_id"])
    assert pipeline["owner"]["recipe_snapshot"] == snapshot
    assert submitted["recipe_identity"] == snapshot
    assert submitted["artifacts"]["recipe_snapshot"] == snapshot
    assert pipeline["recipes"] == manifest["inventory"]


def test_new_pipeline_submit_requires_recipe_snapshot(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    result = adapter(repository, builder).execute(
        request(
            "missing-snapshot",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["library"],
            },
        )
    )
    assert result["status"] == "failed"
    assert "requires recipe_snapshot" in result["failure"]["reason"]


def test_recipe_snapshot_must_be_dependency_complete(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    result = adapter(repository, builder).execute(
        request(
            "incomplete-snapshot",
            "recipes.snapshot",
            {
                "entries": recipe_entries("consumer"),
                "pin_date": "2026-10-01",
            },
        )
    )
    assert result["status"] == "failed"
    assert "missing reviewed package definition: library" in (
        result["failure"]["reason"]
    )


def test_recipe_snapshot_tamper_is_detected_before_submission(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    snapshot = remote_recipe_snapshot(
        remote, "tamper-snapshot", "library"
    )
    package = (
        builder.state
        / "image-build/recipe-snapshots/snapshots"
        / snapshot[7:]
        / "package/library/build.py"
    )
    package.write_text(
        repr(
            {
                "build": [["changed", "library"]],
                "install": [["install", "library"]],
            }
        )
    )
    result = remote.execute(
        request(
            "tampered-submit",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["library"],
                "recipe_snapshot": snapshot,
            },
        )
    )
    assert result["status"] == "failed"
    assert "inventory changed" in result["failure"]["reason"]


def test_recipe_snapshot_pin_is_distinct_from_original_monthly_pin(
    tmp_path,
):
    repository, _, builder, _ = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    snapshot = remote_recipe_snapshot(
        remote, "pin-distinction", "library"
    )
    package_pin = (
        builder.state
        / "image-build/recipe-snapshots/snapshots"
        / snapshot[7:]
        / "package/commit-pin.py"
    )
    original = (
        repository
        / "project/pins/2026-10-01/commit-pin.py"
    )
    materialized = ast.literal_eval(package_pin.read_text())
    assert "monthly_identity" in materialized
    assert package_pin.read_bytes() != original.read_bytes()


def test_worker_contract_explicitly_rejects_generic_pipeline_equivalence(
    tmp_path,
):
    repository, _, builder, _ = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    result = remote.execute(
        request("workers", "worker.inspect", {})
    )
    contract = result["artifacts"]["maintained_worker_contract"]
    assert contract["contract"] == "image-build-maintained-worker-v1"
    assert set(contract["workers"]) == {
        "stages",
        "native-stage",
        "glibc-final",
        "glibc-publish",
        "final-math",
        "final-compiler",
    }
    assert all(
        item["dispatch_interface"] == "maintained-worker"
        and item["generic_pipeline_submit_equivalent"] is False
        and item["entrypoint"].startswith(
            "python -m zog.image_build.worker "
        )
        for item in contract["workers"].values()
    )


def test_worker_contract_can_inspect_one_maintained_task(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    result = adapter(repository, builder).execute(
        request(
            "worker-final-compiler",
            "worker.inspect",
            {"worker": "final-compiler"},
        )
    )
    worker = result["artifacts"][
        "maintained_worker_contract"
    ]["workers"]["final-compiler"]
    assert worker["required_options"] == [
        "project",
        "catalogue",
        "controller",
        "selection",
        "arithmetic",
        "ownership",
        "work",
    ]
    assert "self-hosted-toolchain-publication" in worker["semantics"]


def test_unknown_worker_contract_is_bounded_failure(tmp_path):
    repository, _, builder, _ = setup_repo(tmp_path)
    result = adapter(repository, builder).execute(
        request(
            "worker-unknown",
            "worker.inspect",
            {"worker": "generic-pipeline"},
        )
    )
    assert result["status"] == "failed"
    assert "unknown maintained worker" in result["failure"]["reason"]


def test_recipe_snapshot_cannot_cross_deployed_source_revision(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    first = adapter(repository, builder, "a" * 40)
    snapshot = remote_recipe_snapshot(
        first,
        "snapshot-source-a",
        "library",
        revision="a" * 40,
    )
    second = adapter(repository, builder, "b" * 40)
    result = second.execute(
        request(
            "submit-source-b",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["library"],
                "recipe_snapshot": snapshot,
            },
            revision="b" * 40,
        )
    )
    assert result["status"] == "failed"
    assert "different deployed source revision" in (
        result["failure"]["reason"]
    )


def test_worker_dispatcher_uses_same_machine_contract():
    from zog.image_build.worker import WORKERS
    from zog.image_build.worker_contracts import modules

    assert WORKERS == modules()


def test_github_sequence_retains_snapshot_submit_selection_and_policy_after_interrupt(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    capabilities = remote.execute(
        request("gha-capabilities", "capabilities.inspect", {})
    )
    assert capabilities["status"] == "completed"
    assert capabilities["artifacts"]["remote_capabilities"]["generic_pipeline"]["supported"] is True

    snapshot_result = remote.execute(
        request(
            "gha-snapshot",
            "recipes.snapshot",
            {
                "entries": recipe_entries("library"),
                "pin_date": "2026-10-01",
            },
        )
    )
    snapshot = snapshot_result["recipe_identity"]

    builder.runner = BoxControlRunner(
        execute=lambda build_request: (_ for _ in ()).throw(
            KeyboardInterrupt("simulated client interruption")
        )
    )
    submitted = remote.execute(
        request(
            "gha-submit",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["library"],
                "recipe_snapshot": snapshot,
            },
            predecessor="gha-snapshot",
        )
    )
    assert submitted["status"] == "pending"
    pipeline_id = submitted["pipeline_id"]

    inspected = remote.execute(
        request(
            "gha-inspect",
            "pipeline.inspect",
            {"pipeline_id": pipeline_id},
        )
    )
    evidence = inspected["artifacts"]["execution_evidence"]
    pipeline = builder.inspect_pipeline(pipeline_id)
    assert evidence["contract"] == "image-build-remote-execution-evidence-v1"
    assert evidence["pipeline_id"] == pipeline_id
    assert evidence["pipeline_owner"] == {
        "contract": REQUEST_SCHEMA,
        "operation_id": "gha-submit",
        "source_repository": "zog144/image-build",
        "source_revision": "a" * 40,
        "recipe_snapshot": snapshot,
        "predecessor": "gha-snapshot",
    }
    assert evidence["recipe_snapshot"] == snapshot
    assert evidence["source_pins"] == pipeline["source_pins"]
    assert evidence["selection_generation"] == toolchain.generation
    assert evidence["policy_identity"] is None
    assert evidence["attempt_ids"] == sorted(pipeline["attempts"].values())

    replay = remote.execute(
        request(
            "gha-submit",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["library"],
                "recipe_snapshot": snapshot,
            },
            predecessor="gha-snapshot",
        )
    )
    assert replay["pipeline_id"] == pipeline_id
    assert replay["artifacts"]["execution_evidence"]["pipeline_owner"]["operation_id"] == "gha-submit"


def test_submit_predecessor_must_bind_the_same_completed_snapshot(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    first = remote.execute(
        request(
            "snapshot-library",
            "recipes.snapshot",
            {
                "entries": recipe_entries("library"),
                "pin_date": "2026-10-01",
            },
        )
    )
    second = remote.execute(
        request(
            "snapshot-consumer",
            "recipes.snapshot",
            {
                "entries": recipe_entries("library", "consumer"),
                "pin_date": "2026-10-01",
            },
        )
    )
    rejected = remote.execute(
        request(
            "submit-mismatched-predecessor",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["consumer"],
                "recipe_snapshot": second["recipe_identity"],
            },
            predecessor="snapshot-library",
        )
    )
    assert rejected["status"] == "failed"
    assert "same recipe snapshot" in rejected["failure"]["reason"]


def test_execution_evidence_reports_controller_request_identity_after_interruption(tmp_path):
    repository, _, builder, toolchain = setup_repo(tmp_path)
    remote = adapter(repository, builder)
    snapshot = remote_recipe_snapshot(
        remote, "controller-evidence-snapshot", "library"
    )

    class DurableController:
        def configuration(self):
            return {"contract": "fixture-controller-v1", "lane": "gha"}

        def execute_for_attempt(self, build_request, checkpoint):
            checkpoint = Path(checkpoint)
            request_id = "gha-" + hashlib.sha256(
                checkpoint.name.encode()
            ).hexdigest()
            job_id = hashlib.sha256(request_id.encode()).hexdigest()[:32]
            if not checkpoint.exists():
                checkpoint.write_text(json.dumps({
                    "request_id": request_id,
                    "job_id": job_id,
                }))
                raise KeyboardInterrupt("lost controller reply")
            if build_request.command[0] == "install":
                target = build_request.output / "usr/share/library"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("library")
            return BuildExecutionResult(
                "runtime-fixture",
                "invocation-fixture",
                0,
                True,
                "journal:fixture",
            )

    builder.runner = BoxControlRunner(execute=DurableController())
    pending = remote.execute(
        request(
            "controller-evidence-submit",
            "pipeline.submit",
            {
                "mode": "image",
                "selection": toolchain.generation,
                "targets": ["library"],
                "recipe_snapshot": snapshot,
            },
        )
    )
    assert pending["status"] == "pending"
    first_evidence = pending["artifacts"]["execution_evidence"]
    assert first_evidence["policy_identity"].startswith("sha256:")
    assert first_evidence["controller_jobs"]
    retained_job = first_evidence["controller_jobs"][0]
    assert retained_job["request_id"].startswith("gha-")
    assert retained_job["job_id"] == hashlib.sha256(
        retained_job["request_id"].encode()
    ).hexdigest()[:32]

    resumed = remote.execute(
        request(
            "controller-evidence-resume",
            "pipeline.resume",
            {"pipeline_id": pending["pipeline_id"]},
        )
    )
    assert resumed["status"] == "completed"
    final_jobs = resumed["artifacts"]["execution_evidence"]["controller_jobs"]
    assert any(
        item["request_id"] == retained_job["request_id"]
        and item["job_id"] == retained_job["job_id"]
        for item in final_jobs
    )

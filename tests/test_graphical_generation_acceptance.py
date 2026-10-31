"""Canonical read-only graphical predecessor acceptance regressions."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil

import pytest
pytest.importorskip("zog.build_record")

from zog.image_build import ImageBuild
from zog.image_build import generation_provenance as gp
from zog.image_build import graphical_generation_acceptance as ga
from zog.image_build import installed_verification as iv
from zog.image_build.developer.seed_build import verify as run_verification
from zog.image_build.engine import INFO_INDEX_POLICY, SCHEMA
from zog.image_build.filesystem import inventory, write_json
from zog.image_build.final_compiler import successful_execution
from zog.image_build.metadata import identity, literal, load_packages, order
from zog.image_build.provenance import Provenance
from zog.image_build.recipe_snapshots import _read_snapshot
from zog.image_build.remote_operations import RemoteOperations
from zog.image_build.remote_contract import REQUEST_SCHEMA
from zog.image_build.runner import BoxControlRunner, BuildExecutionResult

REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE = "a" * 40
REQUEST = "1" * 32
TASK = "graphics-fonts-image-v1"
LANE = "graphics-fixture"
INSTALLATION = "fixture-installation"
HOST = "fixture-host"
PROJECT = "fixture-project"


def _operation(name, ordinal=0):
    return hashlib.sha256(
        (
            "zog-generic-pipeline-v1:"
            + REQUEST
            + ":"
            + name
            + ":"
            + str(ordinal)
        ).encode("ascii")
    ).hexdigest()[:32]


def _fixture(tmp_path):
    state = tmp_path / "state"
    pin_path = REPOSITORY / "project/pins/2026-10-01/commit-pin.py"
    pin = Provenance.capture_pin(
        state,
        pin_path,
        repository="zog144/image-build",
        revision=SOURCE,
        repository_path="project/pins/2026-10-01/commit-pin.py",
    )
    provenance = Provenance(
        state, host_id=HOST, project_id=PROJECT, pin=pin
    )
    controller_project = tmp_path / LANE

    def execute(request):
        return BuildExecutionResult(
            "fixture-runtime", "fixture-invocation", 0, True, "fixture-journal"
        )

    execute.configuration = lambda: {
        "project_root": str(controller_project),
        "socket_path": str(tmp_path / "root-control.sock"),
        "execution_user_id": 1000,
        "execution_group_id": 1000,
        "startup_timeout_seconds": 30,
        "termination_grace_seconds": 5,
        "resource_limits": {
            "thread-count-maximum": 128,
            "memory-maximum-bytes": 1024 * 1024 * 1024,
        },
    }
    runner = BoxControlRunner(execute=execute)
    builder = ImageBuild(
        package_dir=REPOSITORY / "project/package",
        state_dir=state,
        runner=runner,
        provenance=provenance,
    )
    adapter = RemoteOperations(
        builder,
        repository_root=REPOSITORY,
        source_repository="zog144/image-build",
        source_revision=SOURCE,
    )
    plan = literal(REPOSITORY / "project/bootstrap/graphics-fonts.py")
    entries = [
        {
            "id": item["id"],
            "project": item["project"],
            "recipe": item["recipe"],
        }
        for item in plan["stages"]
    ]
    snapshot_request = {
        "schema": REQUEST_SCHEMA,
        "operation_id": _operation("snapshot"),
        "operation": "recipes.snapshot",
        "source": {
            "repository": "zog144/image-build", "revision": SOURCE
        },
        "arguments": {"entries": sorted(entries, key=lambda x: x["id"]),
                      "pin_date": "2026-10-01"},
    }
    snapshot_result = adapter.execute(snapshot_request)
    assert snapshot_result["status"] == "completed"
    snapshot_id = snapshot_result["recipe_identity"]
    snapshot = _read_snapshot(
        state / "image-build/recipe-snapshots", snapshot_id
    )

    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "seed").write_text("accepted input")
    input_generation = builder.import_bootstrap(seed, {"fixture": "input"})

    submit_request = {
        "schema": REQUEST_SCHEMA,
        "operation_id": _operation("submit"),
        "operation": "pipeline.submit",
        "source": {
            "repository": "zog144/image-build", "revision": SOURCE
        },
        "arguments": {
            "mode": "image",
            "selection": input_generation.generation,
            "targets": plan["targets"],
            "recipe_snapshot": snapshot_id,
        },
        "predecessor": _operation("snapshot"),
    }
    snapshot_builder = ImageBuild(
        package_dir=snapshot.package_dir,
        state_dir=state,
        runner=runner,
        provenance=provenance,
    )
    pipeline = snapshot_builder.prepare_pipeline(
        "image",
        input_generation,
        owner=adapter._owner(submit_request),
        targets=plan["targets"],
    )
    pipeline_id = pipeline["pipeline_id"]

    packages = load_packages(snapshot.package_dir)
    installed = order(packages, plan["targets"], runtime_only=True)
    built = {}
    composed = tmp_path / "composed"
    composed.mkdir()
    for index, name in enumerate(installed):
        root = tmp_path / "built" / name
        root.mkdir(parents=True)
        path = root / "usr/share" / ("fixture-" + str(index))
        path.parent.mkdir(parents=True)
        path.write_text(name)
        result = {"inputs": {}, "outputs": inventory(root)}
        result["identity"] = identity(result)
        result.update(
            root=str(root),
            provenance=provenance.legacy_output(name, result),
        )
        built[name] = result
        target = composed / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(name)

    selected = order(packages, plan["targets"])
    owner_inputs = {
        "schema": SCHEMA,
        "kind": "image",
        "composition_policy": INFO_INDEX_POLICY,
        "toolchain": input_generation.generation,
        "targets": list(plan["targets"]),
        "recipes": {name: packages[name].fingerprint for name in selected},
        "architecture": platform.machine(),
        "verification_command": "fixture-check",
        "verification_report_contract": iv.CONTRACT,
        "execution_policy": snapshot_builder._policy(),
    }
    attempt_id = "image-fixture"
    attempt = state / "image-build/attempts" / attempt_id
    binding = gp.prepare(
        provenance, attempt, packages, plan["targets"], built, owner_inputs
    )
    check = state / "image-build/attempts/installed-check"
    run_verification(
        snapshot_builder,
        check,
        composed,
        [["/bin/bash", "-eu", "-c", "fixture-check"]],
        owner_inputs,
    )
    execution = successful_execution(check)
    report = iv.capture(
        provenance, binding, composed, owner_inputs, check, execution
    )
    pointer = gp.finish(
        provenance, attempt, binding, composed, verification=[report]
    )
    output = snapshot_builder._publish(
        composed,
        owner_inputs,
        "image",
        {
            "packages": built,
            "build_record": pointer,
            "verification_execution": execution,
        },
    )

    pipeline_path = state / "image-build/pipelines" / pipeline_id / "pipeline.json"
    record = json.loads(pipeline_path.read_text())
    record["attempts"] = {"image": attempt_id}
    record["status"] = "complete"
    record["generation"] = output.generation
    write_json(pipeline_path, record)
    write_json(
        attempt / "status.json",
        {"status": "complete", "generation": output.generation},
    )

    submit_result = adapter.execute(submit_request)
    assert submit_result["status"] == "completed"
    assert submit_result["selected_generation"] == output.generation

    context = {
        "schema": ga.CONTEXT,
        "task": TASK,
        "host_id": HOST,
        "installation_id": INSTALLATION,
        "lane": LANE,
        "lane_owner": HOST,
        "project_id": PROJECT,
        "project_root": str(controller_project),
        "source_repository": "zog144/image-build",
        "source_revision": SOURCE,
        "monthly_pin_identity": pin["digest"],
        "request_id": REQUEST,
        "pipeline_id": pipeline_id,
        "predecessor_catalogue_sha256": "sha256:" + "c" * 64,
        "input_generation_id": input_generation.generation,
    }
    return {
        "builder": builder,
        "context": context,
        "output": output,
        "pointer": pointer,
        "state": state,
        "pipeline_path": pipeline_path,
        "submit_result_path": (
            state
            / "image-build/remote-operations"
            / _operation("submit")
            / "result.json"
        ),
    }


def _attest(data):
    return ga.verify(
        data["builder"],
        repository_root=REPOSITORY,
        trusted_context=data["context"],
    )


def test_canonical_completed_generation_is_accepted_read_only(tmp_path):
    data = _fixture(tmp_path)
    before = {
        path: path.read_bytes()
        for path in data["state"].rglob("*")
        if path.is_file()
    }
    result = _attest(data)
    after = {
        path: path.read_bytes()
        for path in data["state"].rglob("*")
        if path.is_file()
    }
    assert before == after
    assert result == {
        "schema": ga.EVIDENCE,
        "task": TASK,
        "host_id": HOST,
        "installation_id": INSTALLATION,
        "lane": LANE,
        "lane_owner": HOST,
        "project_root": data["context"]["project_root"],
        "source_revision": SOURCE,
        "monthly_pin_identity": data["context"]["monthly_pin_identity"],
        "request_id": REQUEST,
        "pipeline_id": data["context"]["pipeline_id"],
        "predecessor_catalogue_sha256":
            data["context"]["predecessor_catalogue_sha256"],
        "input_generation_id": data["context"]["input_generation_id"],
        "output_generation_id": data["output"].generation,
        "output_kind": "image",
        "generation_manifest_sha256":
            "sha256:" + hashlib.sha256(
                (
                    data["state"]
                    / "image-build/generations"
                    / data["output"].generation
                    / "manifest.json"
                ).read_bytes()
            ).hexdigest(),
        "acceptance_receipt_sha256": data["pointer"]["record"],
        "producer_receipt_sha256":
            "sha256:" + hashlib.sha256(
                data["submit_result_path"].read_bytes()
            ).hexdigest(),
        "status": "accepted",
        "terminal_outcome": "success",
        "uncertainty": False,
        "missing_evidence_count": 0,
    }


def test_missing_generation_manifest_is_rejected(tmp_path):
    data = _fixture(tmp_path)
    (
        data["state"]
        / "image-build/generations"
        / data["output"].generation
        / "manifest.json"
    ).unlink()
    with pytest.raises(Exception, match="required record unavailable|unavailable"):
        _attest(data)


@pytest.mark.parametrize("field", ["source_revision", "monthly_pin_identity"])
def test_wrong_source_or_pin_provenance_is_rejected(tmp_path, field):
    data = _fixture(tmp_path)
    data["context"][field] = (
        "b" * 40 if field == "source_revision" else "sha256:" + "b" * 64
    )
    with pytest.raises(Exception, match="not accepted"):
        _attest(data)


@pytest.mark.parametrize("field", ["request_id", "pipeline_id"])
def test_request_or_pipeline_mismatch_is_rejected(tmp_path, field):
    data = _fixture(tmp_path)
    data["context"][field] = "f" * 32
    with pytest.raises(Exception, match="not accepted|required record unavailable"):
        _attest(data)


def test_tampered_producer_receipt_is_rejected(tmp_path):
    data = _fixture(tmp_path)
    result = json.loads(data["submit_result_path"].read_text())
    result["selected_generation"] = "f" * 64
    write_json(data["submit_result_path"], result)
    with pytest.raises(Exception, match="receipt"):
        _attest(data)


def test_wrong_or_tampered_image_kind_is_rejected(tmp_path):
    data = _fixture(tmp_path)
    manifest = (
        data["state"]
        / "image-build/generations"
        / data["output"].generation
        / "manifest.json"
    )
    value = json.loads(manifest.read_text())
    value["kind"] = "toolchain"
    write_json(manifest, value)
    with pytest.raises(Exception):
        _attest(data)


def test_stale_released_pipeline_is_rejected(tmp_path):
    data = _fixture(tmp_path)
    value = json.loads(data["pipeline_path"].read_text())
    value["released"] = True
    value["status"] = "released"
    write_json(data["pipeline_path"], value)
    with pytest.raises(Exception, match="completed image pipeline"):
        _attest(data)


def test_missing_completed_installed_verification_is_rejected(tmp_path):
    data = _fixture(tmp_path)
    manifest = (
        data["state"]
        / "image-build/generations"
        / data["output"].generation
        / "manifest.json"
    )
    value = json.loads(manifest.read_text())
    value.pop("verification_execution")
    write_json(manifest, value)
    with pytest.raises(Exception):
        _attest(data)


def test_native_wrapper_refuses_nonroot_before_read(monkeypatch):
    monkeypatch.setattr(ga.os, "geteuid", lambda: 1000)
    with pytest.raises(PermissionError):
        ga.attest_native(
            None, repository_root=Path("/no-read"),
            trusted_context={},
        )

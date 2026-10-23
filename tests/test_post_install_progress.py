import hashlib
import json

import pytest

from zog.image_build.application_software import ApplicationSoftwareStore
from zog.image_build.application_views import ApplicationSoftwareViewStore
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import write_json
from zog.image_build.metadata import identity
from zog.image_build.post_install_progress import (
    PIPELINE_OWNER_CONTRACT,
    PUBLICATION_CONTRACT,
    SCHEMA,
    pipeline_owner,
    record_publication,
    producer_source,
    record_selection,
    snapshot,
)
from zog.image_build.post_install_progress_broker import (
    PostInstallProgressBroker,
    ProgressBrokerError,
    WIRE,
)


SOURCE = producer_source("zog144/image-build", "a" * 40)
BOOT = "11111111-2222-3333-4444-555555555555"
CONTROLLER_BOOT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OBSERVED_AT = "2026-10-17T12:00:00+00:00"


def snap(state, applications):
    return snapshot(
        state,
        applications=applications,
        producer_source=SOURCE,
        producer_boot_id=BOOT,
    )


def compat():
    return {
        "schema": 1,
        "mount_contract": "applications-v1",
        "architecture": "x86_64",
        "python": {
            "implementation": "cpython",
            "version": "3.15.0rc2",
            "soabi": "cpython-315-x86_64-linux-gnu",
        },
        "libraries": ["libc.so.6"],
    }


def selection(state, *, firefox=True):
    return record_selection(
        state,
        sequence=7,
        applications={
            "firefox": {
                "requested": firefox,
                "operation_revision": ("sha256:" + "a" * 64) if firefox else None,
            },
            "xorg-server": {"requested": False, "operation_revision": None},
        },
    )


def pipeline(state, receipt, *, status="running", observation=True):
    owner = pipeline_owner(receipt, "firefox")
    assert owner["contract"] == PIPELINE_OWNER_CONTRACT
    pipeline_id = "1" * 32
    attempt_id = "image-" + "2" * 32
    request_id = "signed-build-123"
    job_id = hashlib.sha256(request_id.encode()).hexdigest()[:32]
    source_pin = "3" * 64
    root = state / "image-build"
    directory = root / "pipelines" / pipeline_id
    directory.mkdir(parents=True)
    write_json(
        directory / "pipeline.json",
        {
            "schema": 1,
            "pipeline_id": pipeline_id,
            "operation": "image",
            "owner": owner,
            "source_pins": source_pin,
            "attempts": {"image": attempt_id},
            "status": status,
        },
    )
    attempt = root / "attempts" / attempt_id
    command_dir = attempt / "packages" / "firefox"
    command_dir.mkdir(parents=True)
    write_json(
        command_dir / "build-0.view.json",
        {
            "schema": 1,
            "attempt_id": attempt_id,
            "pipeline_id": pipeline_id,
            "stage_id": "firefox-final",
            "package": "firefox",
            "recipe_identity": "4" * 64,
            "source_pin_identity": source_pin,
            "phase": "build",
            "command_index": 0,
            "command": ["sh", "-c", "SECRET=do-not-expose"],
            "checkpoint": "build-0.controller.json",
        },
    )
    write_json(
        command_dir / "build-0.controller.json",
        {"request_id": request_id, "job_id": job_id},
    )
    write_json(
        command_dir / "build-0.trace.json",
        {
            "schema": 1,
            "attempt_id": attempt_id,
            "command_id": "packages/firefox/build-0",
            "package": "firefox",
            "stage_id": "firefox-final",
            "phase": "build",
            "command_index": 0,
            "pipeline_id": pipeline_id,
            "category": "build",
            "origin": "captured",
            "title": "firefox build",
            "provenance": {
                "recipe_identity": "4" * 64,
                "pin_set_identity": source_pin,
            },
            "relationships": [],
            "receipts": [],
        },
    )
    write_json(
        command_dir / "provenance.json",
        {
            "schema": 1,
            "host_id": "host-fixture",
            "project_id": "project-fixture",
            "attempt_id": "fixture",
            "build_id": "attempt:" + attempt_id,
            "package": "firefox",
            "owner_inputs": "5" * 64,
            "prepared": "sha256:" + "6" * 64,
            "inputs": "sha256:" + "7" * 64,
            "result": "sha256:" + "8" * 64,
            "output": "sha256:" + "9" * 64,
        },
    )
    if observation:
        write_json(
            command_dir / "build-0.observation.json",
            {
                "schema": 1,
                "origin": "captured",
                "observed_at": OBSERVED_AT,
                "boot_id": CONTROLLER_BOOT,
                "request_id": request_id,
                "job_id": job_id,
                "state": "completed",
                "outcome": "success",
                "process_cleanup_complete": True,
            },
        )
    return pipeline_id, attempt_id, request_id, job_id


def rootfs_generation(state, descriptor=None):
    descriptor = descriptor or compat()
    inputs = {
        "kind": "image",
        "application_software_compatibility": descriptor,
    }
    generation = identity(inputs)
    directory = state / "image-build" / "generations" / generation
    root = directory / "root"
    root.mkdir(parents=True, exist_ok=True)
    write_json(
        directory / "manifest.json",
        {
            "schema": 2,
            "generation": generation,
            "kind": "image",
            "inputs": inputs,
            "outputs": [],
            "application_software_compatibility": descriptor,
        },
    )
    return generation


def publish(state, receipt):
    store = ApplicationSoftwareStore(state)
    op = store.begin(
        "firefox-software",
        application="firefox",
        revision="git:" + "5" * 40,
        sources=[{
            "name": "firefox",
            "url": "https://example.invalid/firefox.tar.xz",
            "sha256": "6" * 64,
        }],
        compatibility_requirements=compat(),
        notices=[],
        provenance={"recipe_identity": "4" * 64},
    )
    (op.root / "bin").mkdir()
    (op.root / "bin" / "firefox").write_text("fixture\n")
    artifact = store.finalize(op.operation)
    views = ApplicationSoftwareViewStore(state)
    view = views.publish(
        "firefox-view",
        application="firefox",
        artifacts=[artifact.artifact],
        profile="application",
    )
    generation = rootfs_generation(state)
    return record_publication(
        state,
        application="firefox",
        selection_revision=receipt["selection_revision"],
        operation_revision="sha256:" + "a" * 64,
        artifact=artifact.artifact,
        view=view.view,
        rootfs_generation=generation,
        rootfs_compatibility=compat(),
    )


def test_authoritative_selection_distinguishes_not_requested_from_unobserved(tmp_path):
    state = tmp_path / "state"
    missing = snap(state, ["firefox", "xorg-server"])
    assert {item["state"] for item in missing["items"]} == {"unknown"}
    assert {item["message_code"] for item in missing["items"]} == {"selection-unobserved"}

    receipt = selection(state)
    assert receipt["owner"] == "host-install"
    value = snap(state, ["firefox", "xorg-server"])
    rows = {item["application"]: item for item in value["items"]}
    assert rows["xorg-server"]["state"] == "not-requested"
    assert rows["xorg-server"]["message_code"] == "application-not-requested"
    assert rows["firefox"]["state"] == "waiting"
    assert rows["firefox"]["message_code"] == "intent-awaiting-pipeline"
    assert rows["firefox"]["selection_revision"] == receipt["selection_revision"]
    assert rows["firefox"]["operation_revision"] == "sha256:" + "a" * 64
    assert all(item["progress"] is None for item in value["items"])


def test_selection_sequence_is_monotonic_and_idempotent(tmp_path):
    state = tmp_path / "state"
    first = selection(state)
    assert selection(state) == first
    with pytest.raises(ImageBuildError, match="sequence conflict"):
        record_selection(
            state,
            sequence=7,
            applications={
                "firefox": {"requested": False, "operation_revision": None},
                "xorg-server": {"requested": False, "operation_revision": None},
            },
        )
    with pytest.raises(ImageBuildError, match="rollback"):
        record_selection(
            state,
            sequence=6,
            applications={
                "firefox": {"requested": False, "operation_revision": None},
                "xorg-server": {"requested": False, "operation_revision": None},
            },
        )


def test_command_join_is_exact_sanitized_and_success_is_not_publication(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline_id, attempt_id, request_id, job_id = pipeline(state, receipt)
    value = snap(state, ["firefox"])
    assert value["schema"] == SCHEMA
    assert value["producer_source"] == SOURCE
    assert value["boot_id"] == BOOT
    item = value["items"][0]
    assert item["pipeline_id"] == pipeline_id
    assert item["source_pin_identity"] == "3" * 64
    command = item["commands"][0]
    assert command == {
        "attempt_id": attempt_id,
        "stage_id": "firefox-final",
        "package": "firefox",
        "phase": "build",
        "command_index": 0,
        "controller_request_id": request_id,
        "build_job_id": job_id,
        "recipe_identity": "4" * 64,
        "source_pin_identity": "3" * 64,
        "trace_identity": command["trace_identity"],
        "build_record": {
            "prepared": "sha256:" + "6" * 64,
            "inputs": "sha256:" + "7" * 64,
            "result": "sha256:" + "8" * 64,
            "output": "sha256:" + "9" * 64,
        },
        "controller_observed_at": OBSERVED_AT,
        "controller_boot_id": CONTROLLER_BOOT,
        "state": "succeeded",
        "message_code": "command-succeeded",
        "progress": None,
    }
    assert item["publication"]["state"] == "unknown"
    assert item["state"] == "running"
    assert "SECRET" not in json.dumps(value)
    assert "example.invalid" not in json.dumps(value)


def test_missing_controller_observation_is_uncertain_not_running(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt, observation=False)
    command = snap(state, ["firefox"])["items"][0]["commands"][0]
    assert command["state"] == "uncertain"
    assert command["message_code"] == "command-observation-missing"


def test_conflicting_pipeline_owner_state_is_uncertain(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt)
    first = state / "image-build" / "pipelines" / ("1" * 32) / "pipeline.json"
    value = json.loads(first.read_text())
    value["pipeline_id"] = "9" * 32
    second = state / "image-build" / "pipelines" / ("9" * 32)
    second.mkdir()
    write_json(second / "pipeline.json", value)
    item = snap(state, ["firefox"])["items"][0]
    assert item["state"] == "uncertain"
    assert item["message_code"] == "pipeline-conflict"


def test_publication_receipt_is_independently_reverified(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt, status="complete")
    publication = publish(state, receipt)
    assert publication["contract"] == PUBLICATION_CONTRACT
    item = snap(state, ["firefox"])["items"][0]
    assert item["state"] == "succeeded"
    assert item["message_code"] == "view-published-compatible"
    assert item["publication"]["artifact_id"].startswith("sha256:")
    assert item["publication"]["view_id"].startswith("sha256:")
    assert item["publication"]["receipt"].startswith("sha256:")
    assert item["publication"]["compatibility_checked"] is True
    assert item["publication"]["binding_digest"].startswith("sha256:")
    assert item["publication"]["rootfs_generation"] is not None
    assert item["runtime_admission"] == "unobserved"

    artifact = ApplicationSoftwareStore(state).resolve(
        item["publication"]["artifact_id"]
    )
    (artifact.root / "bin" / "firefox").write_text("tampered\n")
    broken = snap(state, ["firefox"])["items"][0]
    assert broken["state"] == "unknown"
    assert broken["message_code"] == "publication-evidence-conflict"


def test_old_command_view_without_source_bindings_fails_closed(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt)
    view = next((state / "image-build" / "attempts").rglob("*.view.json"))
    raw = json.loads(view.read_text())
    raw.pop("recipe_identity")
    write_json(view, raw)
    item = snap(state, ["firefox"])["items"][0]
    assert item["state"] == "unknown"
    assert item["message_code"] == "pipeline-state-unknown"


def test_broker_is_fixed_allowlist_read_only_and_bounded(tmp_path):
    state = tmp_path / "state"
    selection(state)
    broker = PostInstallProgressBroker(
        state,
        applications=["firefox", "xorg-server"],
        authorized_uid=9901,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
        boot_id=BOOT,
    )
    result = broker.handle({
        "schema": WIRE, "operation": "snapshot", "after": None, "limit": 1
    })
    assert result["schema"] == SCHEMA
    assert result["producer_source"] == SOURCE
    assert result["boot_id"] == BOOT
    assert len(result["items"]) == 1
    assert result["page"]["has_more"] is True
    for hostile in (
        {"schema": WIRE, "operation": "start", "after": None, "limit": 1},
        {"schema": WIRE, "operation": "snapshot", "after": None, "limit": 1,
         "application": "firefox"},
        {"schema": WIRE, "operation": "snapshot", "after": "/etc/passwd", "limit": 1},
        {"schema": WIRE, "operation": "snapshot", "after": None, "limit": 99},
    ):
        with pytest.raises((ProgressBrokerError, ValueError)):
            broker.handle(hostile)


def test_missing_controller_job_receipt_fails_closed(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt)
    observation = next(
        (state / "image-build" / "attempts").rglob("*.observation.json")
    )
    raw = json.loads(observation.read_text())
    raw.pop("job_id")
    write_json(observation, raw)
    command = snap(state, ["firefox"])["items"][0]["commands"][0]
    assert command["state"] == "unknown"
    assert command["message_code"] == "command-evidence-conflict"


def test_reboot_changes_snapshot_boot_not_durable_terminal_evidence(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt)
    first = snap(state, ["firefox"])
    second = snapshot(
        state,
        applications=["firefox"],
        producer_source=SOURCE,
        producer_boot_id="99999999-8888-7777-6666-555555555555",
    )
    assert first["snapshot_id"] != second["snapshot_id"]
    assert first["boot_id"] != second["boot_id"]
    a = first["items"][0]["commands"][0]
    b = second["items"][0]["commands"][0]
    assert a["build_job_id"] == b["build_job_id"]
    assert a["trace_identity"] == b["trace_identity"]
    assert a["state"] == b["state"] == "succeeded"
    assert b["controller_boot_id"] == CONTROLLER_BOOT


def test_rootfs_generation_mismatch_invalidates_publication(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt, status="complete")
    publication = publish(state, receipt)
    generation = publication["rootfs_generation"]
    manifest_path = (
        state / "image-build" / "generations" / generation / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["application_software_compatibility"]["libraries"] = []
    write_json(manifest_path, manifest)
    item = snap(state, ["firefox"])["items"][0]
    assert item["state"] == "unknown"
    assert item["message_code"] == "publication-evidence-conflict"


def test_publication_replay_is_idempotent_and_conflict_is_rejected(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt, status="complete")
    first = publish(state, receipt)
    artifact = first["artifact"]
    view = first["view"]
    second = record_publication(
        state,
        application="firefox",
        selection_revision=receipt["selection_revision"],
        operation_revision="sha256:" + "a" * 64,
        artifact=artifact,
        view=view,
        rootfs_generation=first["rootfs_generation"],
        rootfs_compatibility=compat(),
    )
    assert second == first
    with pytest.raises(ImageBuildError, match="rollback/conflict|conflict"):
        record_publication(
            state,
            application="firefox",
            selection_revision=receipt["selection_revision"],
            operation_revision="sha256:" + "a" * 64,
            artifact=artifact,
            view=None,
        )


def test_success_without_trace_or_build_record_is_not_authoritative(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt)
    attempt = next((state / "image-build" / "attempts").iterdir())
    for path in attempt.rglob("*.trace.json"):
        path.unlink()
    for path in attempt.rglob("provenance.json"):
        path.unlink()
    command = snap(state, ["firefox"])["items"][0]["commands"][0]
    assert command["state"] == "unknown"
    assert command["message_code"] == "command-provenance-unobserved"


@pytest.mark.parametrize(
    ("outcome", "expected_state", "expected_code"),
    [
        ("nonzero-exit", "failed", "command-failed"),
        ("cancelled", "cancelled", "command-cancelled"),
    ],
)
def test_terminal_command_outcome_is_distinct_from_pending_recovery(
    tmp_path, outcome, expected_state, expected_code
):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt, status="pending")
    observation = next(
        (state / "image-build" / "attempts").rglob("*.observation.json")
    )
    raw = json.loads(observation.read_text())
    raw["outcome"] = outcome
    write_json(observation, raw)
    item = snap(state, ["firefox"])["items"][0]
    assert item["pipeline_state"] == "pending"
    assert item["state"] == expected_state
    assert item["message_code"] == expected_code
    assert item["publication"]["state"] == "unknown"


def test_valid_publication_without_pipeline_is_observed_without_build_claims(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    publication = publish(state, receipt)

    item = snap(state, ["firefox"])["items"][0]
    assert item["pipeline_id"] is None
    assert item["pipeline_state"] is None
    assert item["source_pin_identity"] is None
    assert item["commands"] == []
    assert item["commands_truncated"] is False
    assert item["publication"]["state"] == "succeeded"
    assert item["publication"]["message_code"] == "view-published-compatible"
    assert item["publication"]["receipt"] == publication["receipt"]
    assert item["state"] == "succeeded"
    assert item["phase"] == "publishing"
    assert item["message_code"] == "view-published-compatible"
    assert item["runtime_admission"] == "unobserved"


def test_missing_publication_without_pipeline_remains_waiting_for_pipeline(tmp_path):
    state = tmp_path / "state"
    selection(state)
    item = snap(state, ["firefox"])["items"][0]
    assert item["pipeline_id"] is None
    assert item["publication"]["state"] == "unknown"
    assert item["publication"]["message_code"] == "publication-unobserved"
    assert item["state"] == "waiting"
    assert item["phase"] == "queued"
    assert item["message_code"] == "intent-awaiting-pipeline"


def test_invalid_publication_without_pipeline_is_explicit_conflict(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    publication = publish(state, receipt)
    path = (
        state / "image-build" / "post-install-publications" / "firefox"
        / (receipt["applications"][0]["operation_revision"][7:] + ".json")
    )
    raw = json.loads(path.read_text())
    raw["receipt"] = "sha256:" + "0" * 64
    write_json(path, raw)

    item = snap(state, ["firefox"])["items"][0]
    assert item["pipeline_id"] is None
    assert item["commands"] == []
    assert item["publication"]["state"] == "unknown"
    assert item["publication"]["message_code"] == "publication-evidence-conflict"
    assert item["state"] == "unknown"
    assert item["phase"] == "publishing"
    assert item["message_code"] == "publication-evidence-conflict"
    assert publication["receipt"] != raw["receipt"]


def test_publication_selection_mismatch_without_pipeline_is_conflict(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    publish(state, receipt)
    path = (
        state / "image-build" / "post-install-publications" / "firefox"
        / (receipt["applications"][0]["operation_revision"][7:] + ".json")
    )
    raw = json.loads(path.read_text())
    raw["selection_revision"] = "sha256:" + "f" * 64
    body_keys = {
        "schema", "contract", "producer", "application", "selection_revision",
        "operation_revision", "artifact", "view", "compatibility_checked",
        "rootfs_generation", "rootfs_compatibility", "binding_digest",
        "artifact_revision", "artifact_source_identity",
    }
    body = {key: raw[key] for key in body_keys}
    raw["receipt"] = "sha256:" + hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    write_json(path, raw)

    item = snap(state, ["firefox"])["items"][0]
    assert item["publication"]["message_code"] == "publication-evidence-conflict"
    assert item["state"] == "unknown"
    assert item["pipeline_id"] is None


def test_publication_operation_mismatch_without_pipeline_is_conflict(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    publish(state, receipt)
    operation = receipt["applications"][0]["operation_revision"]
    directory = state / "image-build" / "post-install-publications" / "firefox"
    original = directory / (operation[7:] + ".json")
    raw = json.loads(original.read_text())
    wrong = "sha256:" + "b" * 64
    raw["operation_revision"] = wrong
    body_keys = {
        "schema", "contract", "producer", "application", "selection_revision",
        "operation_revision", "artifact", "view", "compatibility_checked",
        "rootfs_generation", "rootfs_compatibility", "binding_digest",
        "artifact_revision", "artifact_source_identity",
    }
    body = {key: raw[key] for key in body_keys}
    raw["receipt"] = "sha256:" + hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    # Keep the mismatched receipt at the selected operation's canonical path so
    # observation sees evidence and classifies it as conflict rather than absence.
    write_json(original, raw)

    item = snap(state, ["firefox"])["items"][0]
    assert item["publication"]["message_code"] == "publication-evidence-conflict"
    assert item["state"] == "unknown"
    assert item["operation_revision"] == operation


def test_incompatible_rootfs_publication_without_pipeline_fails_closed(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    publication = publish(state, receipt)
    manifest_path = (
        state / "image-build" / "generations"
        / publication["rootfs_generation"] / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["application_software_compatibility"]["libraries"] = []
    write_json(manifest_path, manifest)

    item = snap(state, ["firefox"])["items"][0]
    assert item["pipeline_id"] is None
    assert item["publication"]["message_code"] == "publication-evidence-conflict"
    assert item["state"] == "unknown"
    assert item["message_code"] == "publication-evidence-conflict"


def test_pipeline_conflict_is_not_hidden_by_valid_publication(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    publish(state, receipt)
    pipeline(state, receipt)
    first = state / "image-build" / "pipelines" / ("1" * 32) / "pipeline.json"
    value = json.loads(first.read_text())
    value["pipeline_id"] = "9" * 32
    second = state / "image-build" / "pipelines" / ("9" * 32)
    second.mkdir()
    write_json(second / "pipeline.json", value)

    item = snap(state, ["firefox"])["items"][0]
    assert item["publication"]["state"] == "succeeded"
    assert item["publication"]["message_code"] == "view-published-compatible"
    assert item["state"] == "uncertain"
    assert item["message_code"] == "pipeline-conflict"

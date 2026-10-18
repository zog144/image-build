import hashlib
import json

import pytest

from zog.image_build.application_software import ApplicationSoftwareStore
from zog.image_build.application_views import ApplicationSoftwareViewStore
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import write_json
from zog.image_build.post_install_progress import (
    PIPELINE_OWNER_CONTRACT,
    PUBLICATION_CONTRACT,
    SCHEMA,
    pipeline_owner,
    record_publication,
    record_selection,
    snapshot,
)
from zog.image_build.post_install_progress_broker import (
    PostInstallProgressBroker,
    ProgressBrokerError,
    WIRE,
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
    if observation:
        write_json(
            command_dir / "build-0.observation.json",
            {
                "request_id": request_id,
                "job_id": job_id,
                "state": "completed",
                "outcome": "success",
                "process_cleanup_complete": True,
            },
        )
    return pipeline_id, attempt_id, request_id, job_id


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
    return record_publication(
        state,
        application="firefox",
        selection_revision=receipt["selection_revision"],
        operation_revision="sha256:" + "a" * 64,
        artifact=artifact.artifact,
        view=view.view,
        rootfs_compatibility=compat(),
    )


def test_authoritative_selection_distinguishes_not_requested_from_unobserved(tmp_path):
    state = tmp_path / "state"
    missing = snapshot(state, applications=["firefox", "xorg-server"])
    assert {item["state"] for item in missing["items"]} == {"unknown"}
    assert {item["message_code"] for item in missing["items"]} == {"selection-unobserved"}

    receipt = selection(state)
    assert receipt["owner"] == "host-install"
    value = snapshot(state, applications=["firefox", "xorg-server"])
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
    value = snapshot(state, applications=["firefox"])
    assert value["schema"] == SCHEMA
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
    command = snapshot(state, applications=["firefox"])["items"][0]["commands"][0]
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
    item = snapshot(state, applications=["firefox"])["items"][0]
    assert item["state"] == "uncertain"
    assert item["message_code"] == "pipeline-conflict"


def test_publication_receipt_is_independently_reverified(tmp_path):
    state = tmp_path / "state"
    receipt = selection(state)
    pipeline(state, receipt, status="complete")
    publication = publish(state, receipt)
    assert publication["contract"] == PUBLICATION_CONTRACT
    item = snapshot(state, applications=["firefox"])["items"][0]
    assert item["state"] == "succeeded"
    assert item["message_code"] == "view-published-compatible"
    assert item["publication"]["artifact_id"].startswith("sha256:")
    assert item["publication"]["view_id"].startswith("sha256:")
    assert item["publication"]["receipt"].startswith("sha256:")
    assert item["publication"]["compatibility_checked"] is True
    assert item["publication"]["binding_digest"].startswith("sha256:")
    assert item["runtime_admission"] == "unobserved"

    artifact = ApplicationSoftwareStore(state).resolve(
        item["publication"]["artifact_id"]
    )
    (artifact.root / "bin" / "firefox").write_text("tampered\n")
    broken = snapshot(state, applications=["firefox"])["items"][0]
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
    item = snapshot(state, applications=["firefox"])["items"][0]
    assert item["state"] == "unknown"
    assert item["message_code"] == "pipeline-state-unknown"


def test_broker_is_fixed_allowlist_read_only_and_bounded(tmp_path):
    state = tmp_path / "state"
    selection(state)
    broker = PostInstallProgressBroker(
        state, applications=["firefox", "xorg-server"], authorized_uid=9901
    )
    result = broker.handle({
        "schema": WIRE, "operation": "snapshot", "after": None, "limit": 1
    })
    assert result["schema"] == SCHEMA
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

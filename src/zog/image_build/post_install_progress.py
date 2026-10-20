"""Durable, read-only post-install progress owned by image-build.

The authorized selection owner is host-install.  Controller job state is joined to
image-build attempt/recipe/source identities but is never treated as publication.
Application-software publication is separately reverified from immutable artifacts,
views and selected-rootfs compatibility receipts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import uuid

from .application_software import ApplicationSoftwareStore, compatibility
from .application_views import ApplicationSoftwareViewStore
from .build_views import read_build_commands
from .errors import ImageBuildError
from .filesystem import ensure_directory, write_json
from .metadata import identity

SCHEMA = "image-build-post-install-progress-v2"
SELECTION_CONTRACT = "image-build-post-install-selection-v1"
PIPELINE_OWNER_CONTRACT = "image-build-post-install-pipeline-owner-v1"
PUBLICATION_CONTRACT = "image-build-post-install-publication-v2"
PRODUCER_SOURCE_CONTRACT = "image-build-post-install-source-v1"
SELECTION_OWNER = "host-install"

_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SHA = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PIPELINE = re.compile(r"[0-9a-f]{32}\Z")
_ATTEMPT = re.compile(r"[a-z0-9-]+-[0-9a-f]{32}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9-]{1,200}\Z")
_JOB = re.compile(r"[0-9a-f]{32}\Z")
_RECIPE = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_GENERATION = re.compile(r"[0-9a-f]{64}\Z")
_BOOT = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
_PHASES = {"prepare", "configure", "build", "test", "install"}
_STATES = {
    "not-requested", "waiting", "running", "succeeded", "blocked",
    "failed", "cancelled", "uncertain", "unknown",
}
_CODES = {
    "selection-unobserved",
    "application-not-requested",
    "intent-awaiting-pipeline",
    "pipeline-conflict",
    "pipeline-prepared",
    "pipeline-running",
    "pipeline-pending",
    "pipeline-complete-publication-unobserved",
    "pipeline-released",
    "pipeline-state-unknown",
    "command-awaiting-controller-request",
    "command-observation-missing",
    "command-running-unobserved",
    "command-succeeded",
    "command-failed",
    "command-cancelled",
    "command-outcome-uncertain",
    "command-evidence-conflict",
    "command-provenance-unobserved",
    "publication-unobserved",
    "artifact-published",
    "view-published-compatibility-unchecked",
    "view-published-compatible",
    "publication-evidence-conflict",
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _producer_source(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"contract", "repository", "revision"}
        or value.get("contract") != PRODUCER_SOURCE_CONTRACT
        or not isinstance(value.get("repository"), str)
        or not value["repository"]
        or len(value["repository"]) > 256
        or any(ord(c) < 32 for c in value["repository"])
        or not isinstance(value.get("revision"), str)
        or not _REVISION.fullmatch(value["revision"])
    ):
        raise ImageBuildError("invalid post-install producer source binding")
    return dict(value)


def producer_source(repository, revision):
    return _producer_source({
        "contract": PRODUCER_SOURCE_CONTRACT,
        "repository": repository,
        "revision": revision,
    })


def _aware_timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ImageBuildError("invalid progress observation timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as error:
        raise ImageBuildError("invalid progress observation timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ImageBuildError("progress observation timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat()


def _boot(value):
    if value is None:
        return None
    if not isinstance(value, str) or not _BOOT.fullmatch(value):
        raise ImageBuildError("invalid progress boot identity")
    return value


def _generation(value):
    if not isinstance(value, str) or not _GENERATION.fullmatch(value):
        raise ImageBuildError("invalid rootfs generation identity")
    return value


def _name(value):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ImageBuildError("invalid post-install application name")
    return value


def _sha(value, label):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ImageBuildError("invalid " + label)
    return value


def _selection_body(sequence, applications):
    if type(sequence) is not int or not 0 <= sequence < 2**63:
        raise ImageBuildError("invalid post-install selection sequence")
    if not isinstance(applications, dict) or not applications:
        raise ImageBuildError("post-install selection must name applications")
    rows = []
    for application in sorted(applications):
        _name(application)
        item = applications[application]
        if not isinstance(item, dict) or set(item) != {"requested", "operation_revision"}:
            raise ImageBuildError("invalid post-install application selection")
        requested = item["requested"]
        revision = item["operation_revision"]
        if type(requested) is not bool:
            raise ImageBuildError("invalid post-install requested flag")
        if requested:
            _sha(revision, "post-install operation revision")
        elif revision is not None:
            raise ImageBuildError("not-requested application has operation revision")
        rows.append({
            "application": application,
            "requested": requested,
            "operation_revision": revision,
        })
    return {
        "schema": 1,
        "contract": SELECTION_CONTRACT,
        "owner": SELECTION_OWNER,
        "sequence": sequence,
        "applications": rows,
    }


def record_selection(state_dir, *, sequence, applications):
    """Persist an immutable host-install selection and advance its sole current pointer."""
    state = Path(state_dir) / "image-build"
    body = _selection_body(sequence, applications)
    revision = "sha256:" + hashlib.sha256(_canonical(body).encode()).hexdigest()
    receipt = {**body, "selection_revision": revision, "recorded_at": _now()}
    directory = state / "post-install-selections"
    ensure_directory(directory)
    target = directory / (revision[7:] + ".json")
    if target.exists():
        try:
            existing = json.loads(target.read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid retained post-install selection") from error
        if existing != receipt:
            # recorded_at differs on a replay; compare immutable fields.
            existing_body = {k: existing.get(k) for k in receipt if k != "recorded_at"}
            receipt_body = {k: receipt[k] for k in receipt if k != "recorded_at"}
            if existing_body != receipt_body:
                raise ImageBuildError("post-install selection identity collision")
            receipt = existing
    else:
        write_json(target, receipt)

    pointer = state / "post-install-selection.json"
    if pointer.exists():
        try:
            current = json.loads(pointer.read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid current post-install selection") from error
        old_sequence = current.get("sequence")
        if type(old_sequence) is not int:
            raise ImageBuildError("invalid current post-install selection")
        if old_sequence > sequence:
            raise ImageBuildError("post-install selection rollback refused")
        if old_sequence == sequence and current.get("selection_revision") != revision:
            raise ImageBuildError("post-install selection sequence conflict")
        if old_sequence == sequence:
            return receipt
    write_json(pointer, {
        "schema": 1,
        "contract": SELECTION_CONTRACT,
        "owner": SELECTION_OWNER,
        "sequence": sequence,
        "selection_revision": revision,
    })
    return receipt


def pipeline_owner(selection, application):
    """Return the exact owner object passed to prepare_pipeline(owner=...)."""
    if not isinstance(selection, dict) or selection.get("contract") != SELECTION_CONTRACT:
        raise ImageBuildError("invalid post-install selection receipt")
    application = _name(application)
    rows = [row for row in selection.get("applications", [])
            if isinstance(row, dict) and row.get("application") == application]
    if len(rows) != 1 or rows[0].get("requested") is not True:
        raise ImageBuildError("application is not requested")
    return {
        "contract": PIPELINE_OWNER_CONTRACT,
        "intent_owner": SELECTION_OWNER,
        "selection_revision": _sha(selection.get("selection_revision"), "selection revision"),
        "selection_sequence": selection.get("sequence"),
        "application": application,
        "operation_revision": _sha(rows[0].get("operation_revision"), "operation revision"),
    }


def _publication_body(*, application, selection_revision, operation_revision,
                      artifact, view, rootfs_generation, rootfs_compatibility,
                      binding_digest, artifact_revision, artifact_source_identity):
    return {
        "schema": 1,
        "contract": PUBLICATION_CONTRACT,
        "producer": "image-build",
        "application": _name(application),
        "selection_revision": _sha(selection_revision, "selection revision"),
        "operation_revision": _sha(operation_revision, "operation revision"),
        "artifact": _sha(artifact, "artifact identity"),
        "view": None if view is None else _sha(view, "view identity"),
        "compatibility_checked": rootfs_compatibility is not None,
        "rootfs_generation": rootfs_generation,
        "rootfs_compatibility": rootfs_compatibility,
        "binding_digest": binding_digest,
        "artifact_revision": artifact_revision,
        "artifact_source_identity": _sha(artifact_source_identity, "artifact source identity"),
    }


def record_publication(state_dir, *, application, selection_revision,
                       operation_revision, artifact, view=None,
                       rootfs_generation=None, rootfs_compatibility=None):
    """Publish a verified image-build receipt; this never launches the application."""
    artifacts = ApplicationSoftwareStore(state_dir)
    views = ApplicationSoftwareViewStore(state_dir)
    resolved = artifacts.resolve(artifact)
    if resolved.manifest["application"] != application:
        raise ImageBuildError("post-install artifact belongs to another application")
    source_identity = "sha256:" + hashlib.sha256(_canonical({
        "revision": resolved.manifest["revision"],
        "sources": resolved.manifest["sources"],
        "provenance": resolved.manifest["provenance"],
    }).encode()).hexdigest()
    binding_digest = None
    canonical_rootfs = None
    canonical_generation = None
    if view is not None:
        value = views.resolve(view)
        if value.manifest["application"] != application:
            raise ImageBuildError("post-install view belongs to another application")
        if artifact not in value.manifest["artifacts"]:
            raise ImageBuildError("post-install view omits selected artifact")
        if rootfs_compatibility is not None:
            canonical_generation = _generation(rootfs_generation)
            canonical_rootfs = compatibility(rootfs_compatibility)
            from .engine import read_selection
            from .rootfs_compatibility import FIELD
            selected = read_selection(
                Path(state_dir) / "image-build" / "generations" / canonical_generation
            )
            if (
                selected.manifest.get("kind") != "image"
                or selected.manifest.get(FIELD) != canonical_rootfs
            ):
                raise ImageBuildError(
                    "selected rootfs generation differs from compatibility receipt"
                )
            binding = views.consumer_manifest(view, canonical_rootfs)
            binding_digest = binding["binding_digest"]
        elif rootfs_generation is not None:
            raise ImageBuildError(
                "rootfs generation requires a compatibility-checked view"
            )
    elif rootfs_compatibility is not None or rootfs_generation is not None:
        raise ImageBuildError("artifact-only publication cannot claim rootfs compatibility")
    body = _publication_body(
        application=application,
        selection_revision=selection_revision,
        operation_revision=operation_revision,
        artifact=artifact,
        view=view,
        rootfs_generation=canonical_generation,
        rootfs_compatibility=canonical_rootfs,
        binding_digest=binding_digest,
        artifact_revision=resolved.manifest["revision"],
        artifact_source_identity=source_identity,
    )
    receipt_id = "sha256:" + hashlib.sha256(_canonical(body).encode()).hexdigest()
    receipt = {**body, "receipt": receipt_id, "published_at": _now()}
    directory = Path(state_dir) / "image-build" / "post-install-publications" / application
    ensure_directory(directory)
    path = directory / (operation_revision[7:] + ".json")
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid retained post-install publication receipt") from error
        immutable_existing = {k: existing.get(k) for k in receipt if k != "published_at"}
        immutable_receipt = {k: receipt[k] for k in receipt if k != "published_at"}
        if immutable_existing == immutable_receipt:
            return existing
        stable = (
            "schema", "contract", "producer", "application", "selection_revision",
            "operation_revision", "artifact", "artifact_revision",
            "artifact_source_identity",
        )
        if any(existing.get(key) != receipt.get(key) for key in stable):
            raise ImageBuildError("post-install publication receipt conflict")
        old_view, new_view = existing.get("view"), receipt.get("view")
        old_checked, new_checked = existing.get("compatibility_checked"), receipt.get("compatibility_checked")
        forward = (
            old_view is None and new_view is not None
            or old_view == new_view and old_checked is False and new_checked is True
        )
        if not forward:
            raise ImageBuildError("post-install publication receipt rollback/conflict")
        history = directory / "history"
        ensure_directory(history)
        old_receipt = existing.get("receipt")
        _sha(old_receipt, "publication receipt")
        history_path = history / (old_receipt[7:] + ".json")
        if not history_path.exists():
            write_json(history_path, existing)
        write_json(path, receipt)
        return receipt
    write_json(path, receipt)
    return receipt


def _read_selection(state):
    pointer = state / "image-build" / "post-install-selection.json"
    if not pointer.exists():
        return None
    try:
        current = json.loads(pointer.read_text())
        if (current.get("schema") != 1 or current.get("contract") != SELECTION_CONTRACT
                or current.get("owner") != SELECTION_OWNER):
            raise ValueError("shape")
        revision = _sha(current.get("selection_revision"), "selection revision")
        sequence = current.get("sequence")
        if type(sequence) is not int:
            raise ValueError("sequence")
        receipt_path = state / "image-build" / "post-install-selections" / (revision[7:] + ".json")
        receipt = json.loads(receipt_path.read_text())
        expected = _selection_body(sequence, {
            row["application"]: {
                "requested": row["requested"],
                "operation_revision": row["operation_revision"],
            }
            for row in receipt["applications"]
        })
        expected_revision = "sha256:" + hashlib.sha256(_canonical(expected).encode()).hexdigest()
        if (receipt.get("selection_revision") != revision or expected_revision != revision
                or receipt.get("owner") != SELECTION_OWNER):
            raise ValueError("identity")
        return receipt
    except (OSError, ValueError, TypeError, KeyError, ImageBuildError):
        return False


def _pipelines(state, owner):
    root = state / "image-build" / "pipelines"
    matches = []
    if not root.exists():
        return matches
    for path in sorted(root.glob("*/pipeline.json")):
        try:
            value = json.loads(path.read_text())
        except (OSError, ValueError, TypeError):
            continue
        if value.get("owner") == owner:
            matches.append(value)
    return matches


def _observation_for(attempt, command_key, checkpoint):
    view_path = attempt / PurePosixPath(command_key)
    if view_path.name.endswith(".view.json") is False:
        raise ImageBuildError("invalid command view key")
    observation = view_path.with_name(checkpoint.removesuffix(".controller.json") + ".observation.json")
    if not observation.exists():
        return None
    try:
        return json.loads(observation.read_text())
    except (OSError, ValueError, TypeError):
        return False


def _command_provenance(attempt, command):
    view_path = attempt / PurePosixPath(command["command_key"])
    stem = view_path.name.removesuffix(".view.json")
    trace_path = view_path.with_name(stem + ".trace.json")
    trace_identity = None
    if trace_path.exists():
        try:
            trace = json.loads(trace_path.read_text())
        except (OSError, ValueError, TypeError):
            return False, None, None
        if (
            trace.get("schema") != 1
            or trace.get("attempt_id") != command["attempt_id"]
            or trace.get("pipeline_id") != command["pipeline_id"]
            or trace.get("stage_id") != command["stage_id"]
            or trace.get("package") != command["package"]
            or trace.get("phase") != command["phase"]
            or trace.get("command_index") != command["command_index"]
        ):
            return False, None, None
        trace_provenance = trace.get("provenance")
        if (
            not isinstance(trace_provenance, dict)
            or trace_provenance.get("recipe_identity") != command["recipe_identity"]
            or trace_provenance.get("pin_set_identity")
            != command["source_pin_identity"]
        ):
            return False, None, None
        trace_identity = "sha256:" + hashlib.sha256(
            _canonical(trace).encode()
        ).hexdigest()

    provenance_path = view_path.parent / "provenance.json"
    build_record = None
    if provenance_path.exists():
        try:
            provenance = json.loads(provenance_path.read_text())
        except (OSError, ValueError, TypeError):
            return False, trace_identity, None
        if (
            provenance.get("schema") != 1
            or provenance.get("build_id") != "attempt:" + command["attempt_id"]
        ):
            return False, trace_identity, None
        build_record = {}
        for key in ("prepared", "inputs", "result", "output"):
            value = provenance.get(key)
            if value is not None:
                try:
                    _sha(value, "build-record identity")
                except ImageBuildError:
                    return False, trace_identity, None
            build_record[key] = value
    return True, trace_identity, build_record


def _command_state(command, observation):
    if command["request_id"] is None:
        return "waiting", "command-awaiting-controller-request"
    if observation is None:
        return "uncertain", "command-observation-missing"
    if observation is False or not isinstance(observation, dict):
        return "unknown", "command-evidence-conflict"
    try:
        _aware_timestamp(observation.get("observed_at"))
        _boot(observation.get("boot_id"))
    except ImageBuildError:
        return "unknown", "command-evidence-conflict"
    if (
        observation.get("schema") != 1
        or observation.get("request_id") != command["request_id"]
        or observation.get("job_id") != command["job_id"]
    ):
        return "unknown", "command-evidence-conflict"
    state, outcome = observation.get("state"), observation.get("outcome")
    cleanup = observation.get("process_cleanup_complete")
    if state == "completed" and cleanup is True:
        if outcome == "success":
            return "succeeded", "command-succeeded"
        if outcome == "cancelled":
            return "cancelled", "command-cancelled"
        if outcome in {"timeout", "nonzero-exit", "signal", "fault"}:
            return "failed", "command-failed"
        return "uncertain", "command-outcome-uncertain"
    if state in {"starting", "running"}:
        return "uncertain", "command-running-unobserved"
    return "uncertain", "command-outcome-uncertain"


def _safe_command(attempt, command, pipeline_source):
    required = {
        "attempt_id", "pipeline_id", "stage_id", "package", "phase",
        "command_index", "checkpoint", "command_key", "job_id", "request_id",
        "recipe_identity", "source_pin_identity",
    }
    if not required.issubset(command):
        raise ImageBuildError("post-install command view predates progress binding")
    if (command["attempt_id"] != attempt.name
            or not _ATTEMPT.fullmatch(command["attempt_id"])
            or not _PIPELINE.fullmatch(command["pipeline_id"])
            or command["phase"] not in _PHASES
            or type(command["command_index"]) is not int
            or command["command_index"] < 0
            or not isinstance(command["stage_id"], str)
            or len(command["stage_id"]) > 80
            or not isinstance(command["package"], str)
            or len(command["package"]) > 96
            or not _RECIPE.fullmatch(command["recipe_identity"])
            or command["source_pin_identity"] != pipeline_source):
        raise ImageBuildError("invalid post-install command binding")
    request_id = command["request_id"]
    job_id = command["job_id"]
    if request_id is not None and (not isinstance(request_id, str) or not _TOKEN.fullmatch(request_id)):
        raise ImageBuildError("invalid controller request identity")
    if job_id is not None and (not isinstance(job_id, str) or not _JOB.fullmatch(job_id)):
        raise ImageBuildError("invalid build job identity")
    observation = _observation_for(attempt, command["command_key"], command["checkpoint"])
    state, code = _command_state(command, observation)
    provenance_ok, trace_identity, build_record = _command_provenance(attempt, command)
    if not provenance_ok:
        state, code = "unknown", "command-evidence-conflict"
    elif state == "succeeded" and (trace_identity is None or build_record is None):
        state, code = "unknown", "command-provenance-unobserved"
    observed_at = observation.get("observed_at") if isinstance(observation, dict) else None
    boot_id = observation.get("boot_id") if isinstance(observation, dict) else None
    return {
        "attempt_id": command["attempt_id"],
        "stage_id": command["stage_id"],
        "package": command["package"],
        "phase": command["phase"],
        "command_index": command["command_index"],
        "controller_request_id": request_id,
        "build_job_id": job_id,
        "recipe_identity": command["recipe_identity"],
        "source_pin_identity": command["source_pin_identity"],
        "trace_identity": trace_identity,
        "build_record": build_record,
        "controller_observed_at": observed_at,
        "controller_boot_id": boot_id,
        "state": state,
        "message_code": code,
        "progress": None,
    }


def _publication(state, application, selection_revision, operation_revision):
    path = (state / "image-build" / "post-install-publications" / application
            / (operation_revision[7:] + ".json"))
    if not path.exists():
        return {
            "state": "unknown", "message_code": "publication-unobserved",
            "artifact_id": None, "view_id": None, "receipt": None,
            "compatibility_checked": False, "rootfs_generation": None,
            "binding_digest": None,
            "artifact_revision": None, "artifact_source_identity": None,
        }
    try:
        raw = json.loads(path.read_text())
        body_keys = {
            "schema", "contract", "producer", "application", "selection_revision",
            "operation_revision", "artifact", "view", "compatibility_checked",
            "rootfs_generation", "rootfs_compatibility", "binding_digest", "artifact_revision",
            "artifact_source_identity",
        }
        body = {key: raw[key] for key in body_keys}
        expected_receipt = "sha256:" + hashlib.sha256(_canonical(body).encode()).hexdigest()
        if (raw.get("schema") != 1
                or raw.get("contract") != PUBLICATION_CONTRACT
                or raw.get("producer") != "image-build"
                or raw.get("receipt") != expected_receipt
                or raw.get("selection_revision") != selection_revision
                or raw.get("operation_revision") != operation_revision
                or raw.get("application") != application):
            raise ValueError("receipt binding")
        artifacts = ApplicationSoftwareStore(state)
        artifact = artifacts.resolve(raw["artifact"])
        if artifact.manifest["application"] != application:
            raise ValueError("artifact app")
        source_identity = "sha256:" + hashlib.sha256(_canonical({
            "revision": artifact.manifest["revision"],
            "sources": artifact.manifest["sources"],
            "provenance": artifact.manifest["provenance"],
        }).encode()).hexdigest()
        if (raw["artifact_revision"] != artifact.manifest["revision"]
                or raw["artifact_source_identity"] != source_identity):
            raise ValueError("artifact source")
        if raw["view"] is None:
            if (
                raw["compatibility_checked"]
                or raw["binding_digest"] is not None
                or raw["rootfs_generation"] is not None
            ):
                raise ValueError("artifact-only compatibility")
            state_value, code = "succeeded", "artifact-published"
        else:
            views = ApplicationSoftwareViewStore(state)
            view = views.resolve(raw["view"])
            if (view.manifest["application"] != application
                    or raw["artifact"] not in view.manifest["artifacts"]):
                raise ValueError("view binding")
            if raw["compatibility_checked"] is not True:
                state_value, code = "uncertain", "view-published-compatibility-unchecked"
            else:
                generation = _generation(raw["rootfs_generation"])
                from .engine import read_selection
                from .rootfs_compatibility import FIELD
                selected = read_selection(
                    state / "image-build" / "generations" / generation
                )
                expected_rootfs = compatibility(raw["rootfs_compatibility"])
                if (
                    selected.manifest.get("kind") != "image"
                    or selected.manifest.get(FIELD) != expected_rootfs
                ):
                    raise ValueError("rootfs generation compatibility")
                binding = views.consumer_manifest(raw["view"], expected_rootfs)
                if binding["binding_digest"] != raw["binding_digest"]:
                    raise ValueError("binding digest")
                state_value, code = "succeeded", "view-published-compatible"
        return {
            "state": state_value,
            "message_code": code,
            "artifact_id": raw["artifact"],
            "view_id": raw["view"],
            "receipt": raw["receipt"],
            "compatibility_checked": bool(raw["compatibility_checked"]),
            "rootfs_generation": raw["rootfs_generation"],
            "binding_digest": raw["binding_digest"],
            "artifact_revision": raw["artifact_revision"],
            "artifact_source_identity": raw["artifact_source_identity"],
        }
    except (OSError, ValueError, TypeError, KeyError, ImageBuildError):
        return {
            "state": "unknown", "message_code": "publication-evidence-conflict",
            "artifact_id": None, "view_id": None, "receipt": None,
            "compatibility_checked": False, "rootfs_generation": None,
            "binding_digest": None,
            "artifact_revision": None, "artifact_source_identity": None,
        }


def _app_item(state, application, selection, *, command_limit):
    now = _now()
    base = {
        "application": application,
        "producer": "image-build",
        "producer_source": source,
        "boot_id": boot_id,
        "selection_owner": SELECTION_OWNER,
        "selection_revision": None,
        "selection_sequence": None,
        "operation_revision": None,
        "requested": None,
        "pipeline_id": None,
        "pipeline_state": None,
        "source_pin_identity": None,
        "commands": [],
        "commands_truncated": False,
        "publication": {
            "state": "unknown", "message_code": "publication-unobserved",
            "artifact_id": None, "view_id": None, "receipt": None,
            "compatibility_checked": False, "rootfs_generation": None,
            "binding_digest": None,
            "artifact_revision": None, "artifact_source_identity": None,
        },
        "runtime_admission": "unobserved",
        "phase": "intent",
        "state": "unknown",
        "message_code": "selection-unobserved",
        "progress": None,
        "observed_at": now,
    }
    if selection is None or selection is False:
        return base
    rows = [row for row in selection["applications"] if row["application"] == application]
    if len(rows) != 1:
        return base
    row = rows[0]
    base.update(
        selection_revision=selection["selection_revision"],
        selection_sequence=selection["sequence"],
        operation_revision=row["operation_revision"],
        requested=row["requested"],
    )
    if not row["requested"]:
        base.update(state="not-requested", message_code="application-not-requested")
        return base

    owner = pipeline_owner(selection, application)
    matches = _pipelines(state, owner)
    if not matches:
        base.update(phase="queued", state="waiting", message_code="intent-awaiting-pipeline")
        return base
    if len(matches) != 1:
        base.update(phase="building", state="uncertain", message_code="pipeline-conflict")
        return base
    pipeline = matches[0]
    pipeline_id = pipeline.get("pipeline_id")
    source_pin = pipeline.get("source_pins")
    if (not isinstance(pipeline_id, str) or not _PIPELINE.fullmatch(pipeline_id)
            or not isinstance(source_pin, str) or not _RECIPE.fullmatch(source_pin)):
        base.update(phase="building", state="unknown", message_code="pipeline-state-unknown")
        return base
    base["pipeline_id"] = pipeline_id
    base["pipeline_state"] = pipeline.get("status")
    base["source_pin_identity"] = source_pin

    commands = []
    try:
        attempts = pipeline.get("attempts")
        if not isinstance(attempts, dict):
            raise ImageBuildError("invalid pipeline attempts")
        for attempt_name in sorted(attempts.values()):
            if not isinstance(attempt_name, str) or not _ATTEMPT.fullmatch(attempt_name):
                raise ImageBuildError("invalid attempt identity")
            attempt = state / "image-build" / "attempts" / attempt_name
            page = read_build_commands(attempt, limit=100)
            while True:
                for command in page["commands"]:
                    commands.append(_safe_command(attempt, command, source_pin))
                    if len(commands) > command_limit:
                        break
                if len(commands) > command_limit or not page["has_more"]:
                    break
                page = read_build_commands(attempt, after=page["next_after"], limit=100)
            if len(commands) > command_limit:
                break
    except (OSError, ValueError, TypeError, KeyError, ImageBuildError):
        base.update(phase="building", state="unknown", message_code="pipeline-state-unknown")
        return base
    base["commands_truncated"] = len(commands) > command_limit
    base["commands"] = commands[:command_limit]

    status = pipeline.get("status")
    if status == "prepared":
        build_state, code, phase = "waiting", "pipeline-prepared", "queued"
    elif status == "running":
        build_state, code, phase = "running", "pipeline-running", "building"
    elif status == "pending":
        build_state, code, phase = "uncertain", "pipeline-pending", "building"
    elif status == "released":
        build_state, code, phase = "cancelled", "pipeline-released", "building"
    elif status == "complete":
        build_state, code, phase = "succeeded", "pipeline-complete-publication-unobserved", "publishing"
    else:
        build_state, code, phase = "unknown", "pipeline-state-unknown", "building"

    publication = _publication(
        state, application, selection["selection_revision"], row["operation_revision"]
    )
    base["publication"] = publication
    if publication["state"] == "succeeded":
        base.update(phase="publishing", state="succeeded",
                    message_code=publication["message_code"])
    elif publication["message_code"] == "publication-evidence-conflict":
        base.update(phase="publishing", state="unknown",
                    message_code="publication-evidence-conflict")
    else:
        base.update(phase=phase, state=build_state, message_code=code)
    return base


def snapshot(state_dir, *, applications, producer_source=None, producer_boot_id=None,
             after=None, limit=4, command_limit=16):
    """Return a bounded sanitized projection. It never refreshes controller state."""
    state = Path(state_dir)
    source = None if producer_source is None else _producer_source(producer_source)
    boot_id = _boot(producer_boot_id)
    names = sorted({_name(value) for value in applications})
    if type(limit) is not int or not 1 <= limit <= 16:
        raise ValueError("post-install progress limit must be 1..16")
    if type(command_limit) is not int or not 1 <= command_limit <= 64:
        raise ValueError("post-install command limit must be 1..64")
    if after is not None and (not isinstance(after, str) or after not in names):
        raise ValueError("invalid post-install progress cursor")
    selected = [name for name in names if after is None or name > after]
    page_names = selected[:limit]
    selection = _read_selection(state)
    items = [_app_item(state, name, selection, command_limit=command_limit)
             for name in page_names]
    observed = _now()
    for item in items:
        item["observed_at"] = observed
    return {
        "schema": SCHEMA,
        "snapshot_id": uuid.uuid4().hex,
        "observed_at": observed,
        "producer": "image-build",
        "producer_source": source,
        "boot_id": boot_id,
        "selection_owner": SELECTION_OWNER,
        "items": items,
        "page": {
            "has_more": len(selected) > limit,
            "next_after": page_names[-1] if page_names else after,
        },
    }

#!/usr/bin/env python3
"""Read-only Resident B compiler-base Project/operation provenance audit.

The signed compiler capability receipt binds a Host/installation/STATE/Project,
generation and measured execution environment. It does NOT, by itself, contain
the operation that produced the historical image. Do not conflate an assembly
Build Record's attempt ID with a remote operation ID.

CLI runs the exact reviewed compiler_base_acceptance.resolve reader first.
This audit can only report an operation when an original completed pipeline,
its assembly attempt, owner, frozen remote request, binding and result agree.
Missing historical records leave the link unresolved and never mutate it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
from types import SimpleNamespace

GENERATION = "3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc"
RECEIPT = "sha256:a205c07bde4e6cf61e48061affd9a0b40c3a101e18dff67a9871995a3a2afafc"
REVIEWED_READER_BLOB = "3eb562bbf2460fb95af0780a079cb2b058650f80"
REVIEWED_COMPANIONS = {
    "compiler_base_isolation.py": "210a3f81b5796db66a8798ce9d172669e1cf8814",
    "compiler_base_probe.py": "32c36d01d36453df20867945d7535ea117cad774",
}
HEX32 = re.compile(r"[a-f0-9]{32}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_RECORD = 128 * 1024
MAX_PIPELINES = 10000


class ProvenanceHold(ValueError):
    pass


def deny(reason):
    raise ProvenanceHold("Resident B original compiler provenance HOLD: " + reason)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            deny("duplicate persisted JSON field")
        result[key] = value
    return result


def bounded_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        deny("original evidence file missing or linked: " + str(path))
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_RECORD:
        deny("original evidence file not bounded and regular")
    raw = path.read_bytes()
    after = path.stat()
    keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if (len(raw) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in keys)):
        deny("original evidence changed during readback")
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: deny("nonfinite retained evidence"))
    except ProvenanceHold:
        raise  # preserve the specific duplicate-field refusal
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProvenanceHold("Resident B original compiler provenance HOLD: invalid retained JSON") from exc


def _record_directory(state, relative):
    path = Path(state)
    if path.is_symlink() or not path.is_dir():
        deny("selected state directory unavailable or linked")
    for piece in relative.split("/"):
        if piece in ("", ".", ".."):
            deny("invalid retained source directory path")
        path = path / piece
        if path.is_symlink():
            deny("protected source directory is linked: " + relative)
        if not path.exists():
            return None
        if not path.is_dir():
            deny("non-directory in original source hierarchy: " + relative)
    return path


def _read_optional(state, relative):
    parts = relative.split("/")
    parent = _record_directory(state, "/".join(parts[:-1]))
    if parent is None:
        return None
    return bounded_json(parent / parts[-1]) if (parent / parts[-1]).exists() else None


def checked_reader():
    """Source integrity is not an issuer policy: verify both separately."""
    from zog.image_build import compiler_base_acceptance as reader
    folder = Path(reader.__file__).resolve().parent
    if git_blob(Path(reader.__file__).read_bytes()) != REVIEWED_READER_BLOB:
        deny("installed compiler-base reader differs from reviewed PR #20")
    for filename, blob in REVIEWED_COMPANIONS.items():
        path = folder / filename
        if path.is_symlink() or not path.is_file() or git_blob(path.read_bytes()) != blob:
            deny("installed compiler-base reader dependency differs: " + filename)
    return reader


def trace_records(*, state, manifest, binding):
    """Trace an *already verified* receipt and Build Record to native records.

    Returns an explicit unresolved operation, never an inferred value. The
    caller must obtain binding via the signed protected reader, not user JSON.
    """
    if (type(binding) is not dict
            or binding.get("schema") != "image-build-compiler-base-binding-v1"
            or binding.get("status") != "independent-compiler-capability-observed-not-job-authorization"
            or binding.get("generation_id") != GENERATION
            or binding.get("acceptance_receipt_sha256") != RECEIPT):
        deny("missing exactly selected signed compiler capability binding")
    pointer = manifest.get("build_record")
    if (type(pointer) is not dict
            or pointer.get("project_id") != binding.get("project_id")
            or pointer.get("host_id") != binding.get("host_id")
            or pointer.get("generation") != GENERATION
            or pointer.get("record") != binding.get("generation_record_sha256")):
        deny("signed compiler Project differs from original Build Record scope")
    config = manifest.get("inputs", {}).get("provenance")
    if (type(config) is not dict or config.get("host_id") != binding.get("host_id")
            or config.get("project_id") != binding.get("project_id")):
        deny("original generation lacks matching authoritative Project configuration")
    attempt = pointer.get("build_id")
    if type(attempt) is not str or not attempt.startswith("attempt:"):
        deny("original assembly Build Record has no bounded attempt")
    attempt = attempt[len("attempt:"):]
    if not attempt or len(attempt) > 160 or "/" in attempt or ".." in attempt:
        deny("original assembly attempt is invalid")
    source_attempt = _read_optional(state, "image-build/attempts/" + attempt + "/assembly/generation.json")
    if source_attempt is not None and (
            source_attempt.get("generation") != GENERATION or
            source_attempt.get("record") != pointer["record"] or
            source_attempt.get("build_id") != pointer["build_id"]):
        deny("retained assembly attempt changed the original Build Record")

    root = _record_directory(state, "image-build/pipelines")
    matches = []
    if root is not None:
        paths = list(root.iterdir())
        if len(paths) > MAX_PIPELINES:
            deny("unbounded original pipeline directory")
        for entry in sorted(paths):
            if entry.is_symlink() or not entry.is_dir() or not HEX32.fullmatch(entry.name):
                deny("unreviewed original pipeline directory entry")
            record = _read_optional(state, "image-build/pipelines/" + entry.name + "/pipeline.json")
            if record is None:
                deny("unreadable persisted pipeline identity")
            if (record.get("generation") == GENERATION
                    and attempt in (record.get("attempts") or {}).values()):
                if (record.get("pipeline_id") != entry.name
                        or record.get("status") != "complete"
                        or record.get("operation") not in ("image", "bootstrap")):
                    deny("generation-producing pipeline was not durably complete")
                matches.append(record)

    report = {
        "schema": "zog-resident-b-original-compiler-provenance-trace-v1",
        "generation": GENERATION,
        "receipt_sha256": RECEIPT,
        "project_id": binding["project_id"],
        "build_record_project_id": pointer["project_id"],
        "build_record_sha256": pointer["record"],
        "assembly_attempt": attempt,
        "assembly_attempt_record_retained": source_attempt is not None,
        "operation_id": None,
        "pipeline_id": None,
        "authenticated_operation": False,
        "native_build_permitted": False,
        "service_activation_permitted": False,
    }
    if not matches:
        return dict(report, status="HISTORICAL_OPERATION_UNRESOLVED",
                    missing=["original generation-producing pipeline with same assembly attempt"])
    if len(matches) != 1:
        deny("multiple original pipelines claim the same Build Record assembly")
    pipe = matches[0]
    report["pipeline_id"] = pipe["pipeline_id"]
    owner = pipe.get("owner")
    if type(owner) is not dict or not HEX32.fullmatch(str(owner.get("operation_id", ""))):
        return dict(report, status="HISTORICAL_OPERATION_UNRESOLVED",
                    missing=["unique authenticated remote operation owner"])
    oid = owner["operation_id"]
    request = _read_optional(state, "image-build/remote-operations/" + oid + "/request.json")
    frozen = _read_optional(state, "image-build/remote-operations/" + oid + "/binding.json")
    outcome = _read_optional(state, "image-build/remote-operations/" + oid + "/result.json")
    if any(record is None for record in (request, frozen, outcome)):
        return dict(report, status="HISTORICAL_OPERATION_UNRESOLVED",
                    missing=["retained request, binding and terminal result for original operation"])
    if (request.get("operation_id") != oid
            or request.get("operation") != "pipeline.submit"
            or owner.get("contract") != request.get("schema")
            or owner.get("source_repository") != request.get("source", {}).get("repository")
            or owner.get("source_revision") != request.get("source", {}).get("revision")
            or frozen.get("pipeline_id") != pipe["pipeline_id"]
            or outcome.get("operation_id") != oid
            or outcome.get("operation_type") != "pipeline.submit"
            or outcome.get("pipeline_id") != pipe["pipeline_id"]
            or outcome.get("status") != "completed"
            or outcome.get("terminal_outcome") != "success"
            or outcome.get("uncertainty") is not False):
        deny("persisted remote operation cannot authenticate generation producer")
    return dict(report, status="ORIGINAL_PROJECT_AND_OPERATION_LINKED",
                operation_id=oid, authenticated_operation=True, missing=[])


def native_trace(*, project, state, authority, controller):
    """Read-only protected entry point; signer and original bytes are not CLI values."""
    from zog.image_build.engine import read_selection
    from zog.image_build.configuration import configured_runner
    from zog.image_build.provenance import Provenance
    from zog.image_build.generation_provenance import verify as verify_record

    reader = checked_reader()
    project = Path(project).resolve(strict=True)
    state = Path(state).resolve(strict=True)
    if not project.is_dir() or not state.is_dir():
        deny("original Project or STATE directory missing")
    selected_controller = bounded_json(controller)
    controller_project = selected_controller.get("project_root")
    if (type(controller_project) is not str
            or Path(controller_project).resolve(strict=True) != project):
        deny("controller-selected Project differs from native Project argument")
    selection = read_selection(state / "image-build/generations" / GENERATION)
    config = selection.manifest.get("inputs", {}).get("provenance")
    if type(config) is not dict:
        deny("original compiler lacks canonical Build Record owner configuration")
    provenance = Provenance.open_read_only(
        state, host_id=config["host_id"], project_id=config["project_id"],
        pin=config["pin"], retry_of=config["retry_of"],
        generation_contract=config.get("generation_contract"),
    )
    # This validates canonical records without generation index repair.
    verify_record(provenance, selection)
    builder = SimpleNamespace(
        state=state, runner=configured_runner(controller, state),
        provenance=provenance,
        compiler_base_authority=reader.native_authority(str(authority)),
    )
    binding = reader.resolve(builder, selection, RECEIPT)
    if binding.get("project_id") != provenance.project_id:
        deny("signed Project identity does not match canonical Build Record")
    report = trace_records(state=state, manifest=selection.manifest, binding=binding)
    report["host_id"] = binding["host_id"]
    report["installation_id"] = binding["installation_id"]
    report["state_volume_id"] = binding["state_volume_id"]
    report["original_signed_receipt_authenticated"] = True
    report["original_build_record_verified"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-project", type=Path, required=True)
    parser.add_argument("--compiler-state", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--controller-config", type=Path, required=True)
    options = parser.parse_args()
    report = native_trace(
        project=options.compiler_project, state=options.compiler_state,
        authority=options.authority, controller=options.controller_config,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

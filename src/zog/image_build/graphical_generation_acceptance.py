"""Read-only acceptance attester for the finite graphical generation chain.

This module does not submit, resume, retry, publish, activate or repair anything.
The protected host-deploy owner supplies trusted Host/installation/lane context;
image-build independently reopens the exact producer request, recipe snapshot,
pipeline, generation manifest, build-record closure and installed verification.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from types import SimpleNamespace
from pathlib import Path
import re
import stat

from .errors import ImageBuildError
from .engine import read_selection
from .filesystem import inventory
from .metadata import identity, literal, load_packages, names
from .pins import load as load_pin, validate as validate_pin
from .recipe_snapshots import _read_snapshot, normalize_entries
from .remote_contract import REQUEST_SCHEMA, RESULT_SCHEMA

CONTEXT = "image-build-graphical-predecessor-attestation-context-v1"
CONTEXT_COMPILER_BASE = "image-build-graphical-predecessor-attestation-context-v2"
EVIDENCE = "image-build-verified-graphical-predecessor-v1"
TASK_PLANS = {
    "graphics-fonts-image-v1": "project/bootstrap/graphics-fonts.py",
    "graphics-xcb-core-image-v1": "project/bootstrap/graphics-xcb.py",
    "graphics-x11-core-image-v1": "project/bootstrap/graphics-x11-core.py",
}
_HEX32 = re.compile(r"[0-9a-f]{32}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SHA = re.compile(r"sha256:[0-9a-f]{64}\Z")
MAX_RECORD_BYTES = 256 * 1024
MAX_INSPECTS = 64


def _fail(reason):
    raise ImageBuildError("graphical predecessor not accepted: " + reason)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _fail("duplicate JSON field")
        value[key] = item
    return value


def _read_json(path, *, maximum=MAX_RECORD_BYTES):
    path = Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as error:
        raise ImageBuildError(
            "graphical predecessor not accepted: required record unavailable: "
            + str(path)
        ) from error
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            _fail("required record is not a bounded regular file")
        raw = b""
        while len(raw) <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not block:
                break
            raw += block
    finally:
        os.close(fd)
    if len(raw) > maximum:
        _fail("required record exceeds bounded size")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ImageBuildError("non-finite JSON number: " + value)
            ),
        )
    except ImageBuildError:
        raise
    except (UnicodeError, ValueError, TypeError) as error:
        raise ImageBuildError(
            "graphical predecessor not accepted: invalid retained JSON"
        ) from error
    return value, raw


def _sha256(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _context(value):
    fields = {
        "schema", "task", "host_id", "installation_id", "lane", "lane_owner",
        "project_id", "project_root", "source_repository", "source_revision",
        "monthly_pin_identity", "request_id", "pipeline_id",
        "predecessor_catalogue_sha256", "input_generation_id",
    }
    if isinstance(value, dict) and value.get("task") in (
        "graphics-xcb-core-image-v1", "graphics-x11-core-image-v1"
    ):
        fields.add("graphical_predecessor_id")
    if isinstance(value,dict) and value.get("schema")==CONTEXT_COMPILER_BASE:
        fields.add("compiler_base")
    if not isinstance(value, dict) or set(value) != fields:
        _fail("trusted attestation context fields differ")
    if value["schema"] not in (CONTEXT,CONTEXT_COMPILER_BASE) or value["task"] not in TASK_PLANS:
        _fail("unsupported graphical attestation context")
    for key in (
        "host_id", "installation_id", "lane", "lane_owner", "project_id",
        "project_root", "source_repository",
    ):
        item = value[key]
        if (
            not isinstance(item, str)
            or not item
            or len(item) > 512
            or any(ord(char) < 32 or ord(char) == 127 for char in item)
        ):
            _fail("invalid trusted context field: " + key)
    if value["lane_owner"] != value["host_id"]:
        _fail("lane owner differs from provenance Host")
    if not Path(value["project_root"]).is_absolute():
        _fail("Project root must be absolute")
    if not _HEX40.fullmatch(value["source_revision"]):
        _fail("source revision must be an exact commit")
    if not _SHA.fullmatch(value["monthly_pin_identity"]):
        _fail("monthly pin identity must be SHA-256")
    if not _HEX32.fullmatch(value["request_id"]):
        _fail("gateway request identity is invalid")
    if not _HEX32.fullmatch(value["pipeline_id"]):
        _fail("pipeline identity is invalid")
    if not _SHA.fullmatch(value["predecessor_catalogue_sha256"]):
        _fail("predecessor catalogue identity is invalid")
    if not _HEX64.fullmatch(value["input_generation_id"]):
        _fail("input generation identity is invalid")
    if value["schema"]==CONTEXT_COMPILER_BASE and not _SHA.fullmatch(value["compiler_base"]):
        _fail("compiler-base receipt binding is not canonical SHA-256")
    if "graphical_predecessor_id" in value and (
        not isinstance(value["graphical_predecessor_id"], str)
        or not _HEX64.fullmatch(value["graphical_predecessor_id"])
        or value["graphical_predecessor_id"] == value["input_generation_id"]
    ):
        _fail("graphical predecessor identity differs")
    return json.loads(json.dumps(value, sort_keys=True))


def _gateway_operation_id(request_id, name, ordinal=0):
    if not _HEX32.fullmatch(request_id) or name not in {
        "capabilities", "snapshot", "submit", "inspect"
    } or type(ordinal) is not int or not 0 <= ordinal < MAX_INSPECTS:
        _fail("gateway operation identity input is invalid")
    return hashlib.sha256(
        (
            "zog-generic-pipeline-v1:"
            + request_id
            + ":"
            + name
            + ":"
            + str(ordinal)
        ).encode("ascii")
    ).hexdigest()[:32]


def _plan(repository_root, task):
    path = repository_root / TASK_PLANS[task]
    value = literal(path)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "architecture", "stages", "targets"}
        or value["schema"] != 1
        or not isinstance(value["stages"], list)
        or not value["stages"]
    ):
        _fail("reviewed graphical plan is invalid")
    entries = normalize_entries(
        [
            {
                "id": item["id"],
                "project": item["project"],
                "recipe": item["recipe"],
            }
            for item in value["stages"]
        ]
    )
    targets = list(names(value["targets"]))
    if not targets or not set(targets) <= {item["id"] for item in entries}:
        _fail("reviewed graphical targets differ from selected recipes")
    return entries, targets


def _operation_directory(state, operation_id):
    return Path(state) / "image-build" / "remote-operations" / operation_id


def _read_operation(state, operation_id):
    directory = _operation_directory(state, operation_id)
    request, request_raw = _read_json(directory / "request.json")
    binding, binding_raw = _read_json(directory / "binding.json")
    result, result_raw = _read_json(directory / "result.json")
    return {
        "directory": directory,
        "request": request,
        "request_raw": request_raw,
        "binding": binding,
        "binding_raw": binding_raw,
        "result": result,
        "result_raw": result_raw,
    }


def _source(value, context):
    return value == {
        "repository": context["source_repository"],
        "revision": context["source_revision"],
    }


def _validated_producer_result(
    result,
    *,
    operation_id,
    operation,
    context,
    snapshot_id,
    generation,
    manifest,
):
    if (
        not isinstance(result, dict)
        or result.get("schema") != RESULT_SCHEMA
        or result.get("operation_id") != operation_id
        or result.get("operation_type") != operation
        or result.get("source_repository") != context["source_repository"]
        or result.get("source_revision") != context["source_revision"]
        or result.get("pipeline_id") != context["pipeline_id"]
        or result.get("recipe_identity") != snapshot_id
        or result.get("selected_generation") != generation
        or result.get("status") != "completed"
        or result.get("terminal_outcome") != "success"
        or result.get("uncertainty") is not False
        or result.get("failure") is not None
        or result.get("missing_evidence") != []
    ):
        _fail("authenticated producer completion receipt differs")
    artifacts = result.get("artifacts")
    provenance = result.get("provenance")
    expected_manifest = (
        "image-build/generations/" + generation + "/manifest.json"
    )
    if (
        not isinstance(artifacts, dict)
        or artifacts.get("generation_manifest") != expected_manifest
        or artifacts.get("generation_inventory_digest")
        != "sha256:" + identity(manifest["outputs"])
        or not isinstance(provenance, dict)
        or provenance.get("build_record") != manifest.get("build_record")
        or provenance.get("verification_execution")
        != manifest.get("verification_execution")
    ):
        _fail("producer completion receipt is not bound to canonical generation")


def _producer_receipt(
    state,
    *,
    context,
    snapshot_id,
    generation,
    manifest,
    submit_operation,
):
    candidates = []
    submit = submit_operation["result"]
    if submit.get("status") == "completed":
        _validated_producer_result(
            submit,
            operation_id=_gateway_operation_id(context["request_id"], "submit"),
            operation="pipeline.submit",
            context=context,
            snapshot_id=snapshot_id,
            generation=generation,
            manifest=manifest,
        )
        candidates.append((-1, submit_operation["result_raw"]))

    last_inspect = None
    for ordinal in range(MAX_INSPECTS):
        operation_id = _gateway_operation_id(
            context["request_id"], "inspect", ordinal
        )
        directory = _operation_directory(state, operation_id)
        if not directory.exists() and not directory.is_symlink():
            continue
        operation = _read_operation(state, operation_id)
        expected = {
            "schema": REQUEST_SCHEMA,
            "operation_id": operation_id,
            "operation": "pipeline.inspect",
            "source": {
                "repository": context["source_repository"],
                "revision": context["source_revision"],
            },
            "arguments": {"pipeline_id": context["pipeline_id"]},
        }
        if operation["request"] != expected:
            _fail("retained pipeline inspection request differs")
        if operation["binding"].get("observation_source") is not None:
            _fail("external historical observation cannot accept a live predecessor")
        last_inspect = (ordinal, operation)
    if last_inspect is not None:
        ordinal, operation = last_inspect
        _validated_producer_result(
            operation["result"],
            operation_id=_gateway_operation_id(
                context["request_id"], "inspect", ordinal
            ),
            operation="pipeline.inspect",
            context=context,
            snapshot_id=snapshot_id,
            generation=generation,
            manifest=manifest,
        )
        candidates.append((ordinal, operation["result_raw"]))

    if not candidates:
        _fail("no completed producer receipt exists")
    return _sha256(max(candidates, key=lambda item: item[0])[1])


def verify(builder, *, repository_root, trusted_context):
    """Verify one completed graphical predecessor without mutating producer state."""
    context = _context(trusted_context)
    repository_root = Path(repository_root)
    if (
        not repository_root.is_absolute()
        or repository_root.is_symlink()
        or not repository_root.is_dir()
    ):
        _fail("installed repository root is not a real absolute directory")
    repository_root = repository_root.resolve()

    provenance = builder.provenance
    if provenance is None or provenance.generation_contract != "rootfs-v1":
        _fail("canonical generation provenance is not configured")
    if (
        provenance.host_id != context["host_id"]
        or provenance.project_id != context["project_id"]
    ):
        _fail("producer Host/Project scope differs")
    pin = provenance.pin
    if (
        not isinstance(pin, dict)
        or pin.get("repository") != context["source_repository"]
        or pin.get("revision") != context["source_revision"]
        or pin.get("digest") != context["monthly_pin_identity"]
        or not isinstance(pin.get("path"), str)
        or not isinstance(pin.get("month"), str)
    ):
        _fail("captured source/monthly pin differs from trusted lane")

    pin_path = repository_root / pin["path"]
    try:
        pin_relative = pin_path.resolve(strict=True).relative_to(repository_root)
    except (OSError, ValueError) as error:
        raise ImageBuildError(
            "graphical predecessor not accepted: captured monthly pin is unavailable"
        ) from error
    if pin_path.is_symlink() or pin_relative.as_posix() != pin["path"]:
        _fail("captured monthly pin path differs")
    pin_raw = pin_path.read_bytes()
    if _sha256(pin_raw) != context["monthly_pin_identity"]:
        _fail("installed monthly pin bytes differ")
    parsed_pin = load_pin(pin_path)
    if parsed_pin.get("date") != pin["month"]:
        _fail("installed monthly pin month differs")
    snapshot_monthly_identity = "sha256:" + identity(parsed_pin)

    entries, targets = _plan(repository_root, context["task"])
    snapshot_operation_id = _gateway_operation_id(
        context["request_id"], "snapshot"
    )
    snapshot_operation = _read_operation(builder.state, snapshot_operation_id)
    expected_snapshot_request = {
        "schema": REQUEST_SCHEMA,
        "operation_id": snapshot_operation_id,
        "operation": "recipes.snapshot",
        "source": {
            "repository": context["source_repository"],
            "revision": context["source_revision"],
        },
        "arguments": {"entries": entries, "pin_date": pin["month"]},
    }
    if snapshot_operation["request"] != expected_snapshot_request:
        _fail("retained recipe snapshot request differs")
    snapshot_id = snapshot_operation["binding"].get("recipe_snapshot")
    if (
        not isinstance(snapshot_id, str)
        or not _SHA.fullmatch(snapshot_id)
        or snapshot_operation["binding"] != {"recipe_snapshot": snapshot_id}
    ):
        _fail("recipe snapshot binding is invalid")
    snapshot_result = snapshot_operation["result"]
    if (
        snapshot_result.get("status") != "completed"
        or snapshot_result.get("terminal_outcome") != "success"
        or snapshot_result.get("uncertainty") is not False
        or snapshot_result.get("recipe_identity") != snapshot_id
        or snapshot_result.get("missing_evidence") != []
    ):
        _fail("recipe snapshot producer result is incomplete")
    snapshot = _read_snapshot(
        Path(builder.state) / "image-build" / "recipe-snapshots",
        snapshot_id,
    )
    if (
        snapshot.manifest["source"]
        != {
            "repository": context["source_repository"],
            "revision": context["source_revision"],
        }
        or snapshot.manifest["entries"] != entries
        or snapshot.manifest["pin_date"] != pin["month"]
        or snapshot.manifest["monthly_identity"] != snapshot_monthly_identity
    ):
        _fail("published recipe snapshot source/pin differs")

    submit_operation_id = _gateway_operation_id(
        context["request_id"], "submit"
    )
    submit_operation = _read_operation(builder.state, submit_operation_id)
    expected_submit_request = {
        "schema": REQUEST_SCHEMA,
        "operation_id": submit_operation_id,
        "operation": "pipeline.submit",
        "source": {
            "repository": context["source_repository"],
            "revision": context["source_revision"],
        },
        "arguments": {
            "mode": "image",
            "selection": context["input_generation_id"],
            "targets": targets,
            "recipe_snapshot": snapshot_id,
            **({"graphical_predecessor": context["graphical_predecessor_id"]}
               if "graphical_predecessor_id" in context else {}),
            **({"compiler_base":context["compiler_base"]}
               if "compiler_base" in context else {}),
        },
        "predecessor": snapshot_operation_id,
    }
    if submit_operation["request"] != expected_submit_request:
        _fail("retained pipeline submit request differs")
    if submit_operation["binding"] != {
        "pipeline_id": context["pipeline_id"],
        "recipe_snapshot": snapshot_id,
    }:
        _fail("pipeline submit binding differs")

    pipeline_path = (
        Path(builder.state)
        / "image-build"
        / "pipelines"
        / context["pipeline_id"]
        / "pipeline.json"
    )
    pipeline, pipeline_raw = _read_json(pipeline_path)
    if (
        pipeline.get("schema") != 1
        or pipeline.get("pipeline_id") != context["pipeline_id"]
        or pipeline.get("operation") != "image"
        or pipeline.get("status") != "complete"
        or pipeline.get("released") is not None
        or pipeline.get("error") is not None
        or pipeline.get("arguments") != {
            "targets": targets,
            **({"graphical_predecessor": context["graphical_predecessor_id"]}
               if "graphical_predecessor_id" in context else {}),
            **({"compiler_base":context["compiler_base"]}
               if "compiler_base" in context else {}),
        }
    ):
        _fail("durable producer pipeline is not a completed image pipeline")
    owner = pipeline.get("owner")
    expected_owner = {
        "contract": REQUEST_SCHEMA,
        "operation_id": submit_operation_id,
        "source_repository": context["source_repository"],
        "source_revision": context["source_revision"],
        "recipe_snapshot": snapshot_id,
        "predecessor": snapshot_operation_id,
    }
    if owner != expected_owner:
        _fail("pipeline owner/request identity differs")
    policy = pipeline.get("policy")
    if (
        not isinstance(policy, dict)
        or policy.get("provenance") != provenance.configuration()
        or not isinstance(policy.get("controller"), dict)
        or policy["controller"].get("project_root") != context["project_root"]
    ):
        _fail("pipeline Host/Project/provenance policy differs")

    input_directory = (
        Path(builder.state)
        / "image-build"
        / "generations"
        / context["input_generation_id"]
    )
    if input_directory.is_symlink() or not input_directory.is_dir():
        _fail("selected input generation is unavailable")
    base_selection = read_selection(input_directory)
    accepted_compiler=None
    if "compiler_base" in context:
        from .compiler_base_acceptance import resolve as resolve_compiler
        accepted_compiler=resolve_compiler(builder,base_selection,context["compiler_base"])
        if (accepted_compiler["host_id"]!=context["host_id"] or
            accepted_compiler["installation_id"]!=context["installation_id"] or
            accepted_compiler["project_id"]!=context["project_id"]):
            _fail("independent compiler-base Host/installation/Project differs")
    if Path(pipeline.get("selection", "")) != input_directory.resolve():
        _fail("pipeline selected input generation differs")

    pipeline_package = pipeline_path.parent / "package"
    if (
        pipeline_package.is_symlink()
        or inventory(pipeline_package) != pipeline.get("recipes")
        or pipeline.get("recipes") != snapshot.manifest["inventory"]
    ):
        _fail("pipeline recipe snapshot inventory differs")
    packages = load_packages(pipeline_package)
    if identity(validate_pin(pipeline_package, packages)) != pipeline.get(
        "source_pins"
    ):
        _fail("pipeline source pins changed")

    generation = pipeline.get("generation")
    if (
        not isinstance(generation, str)
        or not _HEX64.fullmatch(generation)
        or generation == context["input_generation_id"]
    ):
        _fail("output generation is absent or not distinct")
    generation_directory = (
        Path(builder.state) / "image-build" / "generations" / generation
    )
    if (
        generation_directory.is_symlink()
        or (generation_directory / "manifest.json").is_symlink()
        or not generation_directory.is_dir()
    ):
        _fail("canonical output generation is unavailable")
    manifest_path = generation_directory / "manifest.json"
    manifest, manifest_raw = _read_json(manifest_path)
    selection = read_selection(generation_directory)
    if selection.manifest != manifest or selection.generation != generation:
        _fail("generation catalogue and manifest differ")
    if manifest.get("kind") != "image":
        _fail("graphical predecessor output kind is not image")
    expected_graphical_fields = {}
    if "graphical_predecessor_id" in context:
        from .graphical_composition import (
            validate as validate_graphical, input_fields,
        )
        expected_graphical_fields = input_fields(validate_graphical(
            builder, base_selection,
            context["graphical_predecessor_id"], targets,
            compiler_base=accepted_compiler,
        ))
    generation_inputs = manifest.get("inputs")
    if (
        not isinstance(generation_inputs, dict)
        or generation_inputs.get("kind") != "image"
        or generation_inputs.get("toolchain")
        != context["input_generation_id"]
        or generation_inputs.get("targets") != targets
        or generation_inputs.get("recipes") != snapshot.manifest["packages"]
        or generation_inputs.get("compiler_base") != accepted_compiler
        or any(generation_inputs.get(k) != v for k, v in expected_graphical_fields.items())
        or ("graphical_predecessor" in generation_inputs)
           != ("graphical_predecessor_id" in context)
    ):
        _fail("generation input ancestry differs from submitted pipeline")

    from .generation_provenance import verify as verify_generation
    bundle = verify_generation(provenance, selection)
    pointer = manifest.get("build_record")
    if (
        not isinstance(pointer, dict)
        or not _SHA.fullmatch(pointer.get("record", ""))
        or pointer.get("generation") != generation
    ):
        _fail("canonical generation provenance root is invalid")
    root_record = bundle["records"].get(pointer["record"])
    verification = (
        root_record.get("data", {}).get("verification")
        if isinstance(root_record, dict)
        else None
    )
    if (
        not isinstance(manifest.get("verification_execution"), dict)
        or not isinstance(verification, list)
        or len(verification) != 1
    ):
        _fail("completed installed verification is required")

    attempts = pipeline.get("attempts")
    if not isinstance(attempts, dict):
        _fail("pipeline attempt ledger is invalid")
    for attempt_id in attempts.values():
        if (
            not isinstance(attempt_id, str)
            or not attempt_id
            or "/" in attempt_id
            or attempt_id in {".", ".."}
        ):
            _fail("pipeline attempt identity is invalid")
        status, _ = _read_json(
            Path(builder.state)
            / "image-build"
            / "attempts"
            / attempt_id
            / "status.json"
        )
        if status != {"status": "complete", "generation": generation}:
            _fail("pipeline has outstanding or stale attempt evidence")

    producer_receipt = _producer_receipt(
        builder.state,
        context=context,
        snapshot_id=snapshot_id,
        generation=generation,
        manifest=manifest,
        submit_operation=submit_operation,
    )
    # Re-read the pipeline after every generation/provenance check. A concurrent
    # release/status rewrite invalidates the attestation rather than racing it.
    pipeline_after, pipeline_raw_after = _read_json(pipeline_path)
    if pipeline_after != pipeline or pipeline_raw_after != pipeline_raw:
        _fail("pipeline changed during attestation")

    return {
        "schema": EVIDENCE,
        "task": context["task"],
        "host_id": context["host_id"],
        "installation_id": context["installation_id"],
        "lane": context["lane"],
        "lane_owner": context["lane_owner"],
        "project_root": context["project_root"],
        "source_revision": context["source_revision"],
        "monthly_pin_identity": context["monthly_pin_identity"],
        "request_id": context["request_id"],
        "pipeline_id": context["pipeline_id"],
        "predecessor_catalogue_sha256":
            context["predecessor_catalogue_sha256"],
        "input_generation_id": context["input_generation_id"],
        "output_generation_id": generation,
        "output_kind": "image",
        **({"compiler_base_acceptance_sha256":context["compiler_base"],
            "compiler_base_generation_kind":accepted_compiler["generation_kind"],
            "compiler_base_historical_provenance_status":
                accepted_compiler["historical_provenance"]["status"]}
            if accepted_compiler is not None else {}),
        "generation_manifest_sha256": _sha256(manifest_raw),
        # Existing immutable build-record generation root; no synthetic receipt.
        "acceptance_receipt_sha256": pointer["record"],
        # Exact retained completed image-build remote result bytes.
        "producer_receipt_sha256": producer_receipt,
        "status": "accepted",
        "terminal_outcome": "success",
        "uncertainty": False,
        "missing_evidence_count": 0,
    }


def attest_native(builder, *, repository_root, trusted_context):
    """Root-only protected capability wrapper around the read-only verifier."""
    if os.geteuid() != 0:
        raise PermissionError(
            "graphical predecessor attestation is a protected local capability"
        )
    return verify(
        builder,
        repository_root=repository_root,
        trusted_context=trusted_context,
    )


def _native_cli_pin(
    repository_root, pin_path, *, source_repository, source_revision,
    expected_digest
):
    repository_root = Path(repository_root).resolve()
    pin_path = Path(pin_path)
    if not pin_path.is_absolute():
        pin_path = repository_root / pin_path
    try:
        resolved = pin_path.resolve(strict=True)
        relative = resolved.relative_to(repository_root).as_posix()
    except (OSError, ValueError) as error:
        raise ImageBuildError(
            "graphical predecessor not accepted: provenance pin is outside source"
        ) from error
    if pin_path.is_symlink() or not pin_path.is_file():
        _fail("provenance pin must be a regular installed source file")
    raw = pin_path.read_bytes()
    if len(raw) > 1024 * 1024 or _sha256(raw) != expected_digest:
        _fail("installed provenance pin bytes differ")
    try:
        parsed = ast.literal_eval(raw.decode("utf-8"))
        month = parsed["date"]
    except (UnicodeError, ValueError, SyntaxError, KeyError, TypeError) as error:
        raise ImageBuildError(
            "graphical predecessor not accepted: invalid installed provenance pin"
        ) from error
    if not isinstance(month, str):
        _fail("installed provenance pin has no canonical month")
    return {
        "month": month,
        "repository": source_repository,
        "revision": source_revision,
        "path": relative,
        "digest": expected_digest,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m zog.image_build.graphical_generation_acceptance"
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--provenance-host-id", required=True)
    parser.add_argument("--provenance-project-id", required=True)
    parser.add_argument("--provenance-pin", required=True)
    parser.add_argument("--expected-pin-digest", required=True)
    args = parser.parse_args(argv)
    if not _HEX40.fullmatch(args.source_revision):
        raise SystemExit("source revision must be an exact 40-hex commit")
    if not _SHA.fullmatch(args.expected_pin_digest):
        raise SystemExit("expected pin digest must be SHA-256")
    raw_context = sys.stdin.buffer.read(65537)
    if len(raw_context) > 65536:
        raise SystemExit("trusted graphical attestation context exceeds 64 KiB")
    try:
        context = json.loads(
            raw_context.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ImageBuildError("non-finite JSON number: " + value)
            ),
        )
    except (UnicodeError, ValueError, TypeError, ImageBuildError) as error:
        raise SystemExit("invalid trusted graphical attestation context") from error
    pin = _native_cli_pin(
        args.repository_root,
        args.provenance_pin,
        source_repository=args.source_repository,
        source_revision=args.source_revision,
        expected_digest=args.expected_pin_digest,
    )
    from .provenance import Provenance
    provenance = Provenance.open_read_only(
        args.state_dir,
        host_id=args.provenance_host_id,
        project_id=args.provenance_project_id,
        pin=pin,
    )
    reader = SimpleNamespace(
        state=Path(args.state_dir).resolve(),
        provenance=provenance,
    )
    evidence = attest_native(
        reader,
        repository_root=Path(args.repository_root).resolve(),
        trusted_context=context,
    )
    sys.stdout.buffer.write(
        json.dumps(
            evidence, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False
        ).encode("ascii") + b"\n"
    )


if __name__ == "__main__":
    main()

"""Versioned disconnected-control adapter for image-build.

This module is transport-neutral.  It knows nothing about GitHub, SQS, AWS, or
ChatGPT.  A trusted caller supplies the repository identity/revision actually
deployed on the host and a versioned request.  Mutable execution always flows
through ImageBuild and its configured box-control/root-control adapter.
"""
from __future__ import annotations

from dataclasses import asdict
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

from .build_views import read_build_commands
from .errors import ImageBuildError
from .filesystem import ensure_directory, inventory, write_json
from .metadata import identity, load_package, load_packages, names, order
from .runner import BuildExecutionRequest

from .remote_contract import (
    CAPABILITIES_SCHEMA,
    EXECUTION_EVIDENCE_SCHEMA,
    GENERIC_PIPELINE_MODES,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    SUPPORTED_OPERATIONS,
)

DIAGNOSTIC_SCHEMA = "image-build-diagnostic-v1"
_OPERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_REVISION = re.compile(r"[0-9a-f]{40,64}")
_DIAGNOSTIC = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}")
_GENERATION = re.compile(r"[0-9a-f]{64}")
MAX_COMMANDS = 24
MAX_MISSING = 24
MAX_INVENTORY_ITEMS = 128


def _json(value, label):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ImageBuildError(label + " must be JSON data") from error


def _relative(value, label):
    if not isinstance(value, str) or not value or "\0" in value:
        raise ImageBuildError("invalid " + label)
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ImageBuildError("unsafe " + label)
    return path.as_posix()


def _sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _validated_monthly_provenance_pin(
    repository_root, pin_path, expected_digest
):
    """Bind an original reviewed monthly pin inside the exact deployed tree."""
    root = Path(repository_root)
    pin = Path(pin_path)
    if not root.is_absolute() or not pin.is_absolute():
        raise ImageBuildError(
            "repository root and monthly provenance pin must be absolute paths"
        )
    root = Path(os.path.abspath(root))
    pin = Path(os.path.abspath(pin))
    if root.is_symlink() or not root.is_dir():
        raise ImageBuildError(
            "deployed repository root must be a real directory"
        )
    try:
        relative = pin.relative_to(root)
    except ValueError as error:
        raise ImageBuildError(
            "monthly provenance pin must be inside the deployed repository"
        ) from error
    if not relative.parts or relative.parts[0] == ".git":
        raise ImageBuildError(
            "monthly provenance pin must be repository source evidence"
        )
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ImageBuildError(
                "monthly provenance pin must not traverse a symlink"
            )
    if not current.exists():
        raise ImageBuildError(
            "monthly provenance pin is missing"
        )
    try:
        mode = current.lstat().st_mode
    except OSError as error:
        raise ImageBuildError(
            "monthly provenance pin is unavailable"
        ) from error
    if not stat.S_ISREG(mode):
        raise ImageBuildError(
            "monthly provenance pin must be a regular file"
        )
    try:
        current.resolve(strict=True).relative_to(
            root.resolve(strict=True)
        )
    except (OSError, ValueError) as error:
        raise ImageBuildError(
            "monthly provenance pin escapes the deployed repository"
        ) from error

    if (
        not isinstance(expected_digest, str)
        or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", expected_digest
        )
    ):
        raise ImageBuildError(
            "expected monthly provenance pin digest must be sha256"
        )
    from .pins import load as load_monthly_pin

    monthly = load_monthly_pin(current)
    if "monthly_identity" in monthly:
        raise ImageBuildError(
            "materialized recipe-snapshot pin cannot be used as the original monthly provenance pin"
        )
    observed = "sha256:" + _sha256(current)
    if observed != expected_digest:
        raise ImageBuildError(
            "deployed monthly provenance pin digest differs from lane binding"
        )
    return {
        "path": current,
        "repository_path": relative.as_posix(),
        "digest": observed,
        "month": monthly["date"],
    }


def _validated_observed_state_dir(control_state, observed_state):
    """Return a canonical external state root without creating or changing it."""
    control = Path(control_state)
    observed = Path(observed_state)
    if not observed.is_absolute():
        raise ImageBuildError(
            "observed state directory must be an absolute path"
        )
    # Check the supplied object before resolve so a symlink cannot be hidden by
    # canonicalization.
    if observed.is_symlink():
        raise ImageBuildError(
            "observed state directory must not be a symlink"
        )
    if not observed.exists() or not observed.is_dir():
        raise ImageBuildError(
            "observed state directory must be an existing directory"
        )
    try:
        canonical = observed.resolve(strict=True)
        control_canonical = control.resolve(strict=True)
    except OSError as error:
        raise ImageBuildError(
            "observed/control state directory is unavailable"
        ) from error
    if canonical == control_canonical:
        raise ImageBuildError(
            "external observed state must differ from control state"
        )
    return canonical


class RemoteOperations:
    def __init__(
        self,
        builder,
        *,
        repository_root,
        source_repository,
        source_revision,
        observed_state_dir=None,
    ):
        self.builder = builder
        self.repository_root = Path(repository_root).resolve()
        self.source_repository = source_repository
        self.source_revision = source_revision
        self.control_state = Path(builder.state).resolve()
        self.external_observed_state = observed_state_dir is not None
        self.observed_state = (
            _validated_observed_state_dir(
                self.control_state, observed_state_dir
            )
            if self.external_observed_state
            else self.control_state
        )
        if (
            not isinstance(source_repository, str)
            or not source_repository
            or len(source_repository) > 512
            or any(ord(c) < 32 for c in source_repository)
        ):
            raise ImageBuildError("invalid deployed source repository identity")
        if not isinstance(source_revision, str) or not _REVISION.fullmatch(source_revision):
            raise ImageBuildError("deployed source revision must be an immutable commit identity")
        try:
            Path(builder.package_dir).resolve().relative_to(self.repository_root)
        except ValueError as error:
            raise ImageBuildError(
                "package directory must be inside the deployed repository"
            ) from error
        self.root = self.control_state / "image-build" / "remote-operations"
        ensure_directory(self.root)

    def _directory(self, operation_id):
        if not isinstance(operation_id, str) or not _OPERATION_ID.fullmatch(operation_id):
            raise ImageBuildError("invalid remote operation identity")
        return self.root / operation_id

    def _owner(self, request):
        value = {
            "contract": REQUEST_SCHEMA,
            "operation_id": request["operation_id"],
            "source_repository": request["source"]["repository"],
            "source_revision": request["source"]["revision"],
        }
        recipe_snapshot = request.get("arguments", {}).get(
            "recipe_snapshot"
        )
        if recipe_snapshot is not None:
            value["recipe_snapshot"] = recipe_snapshot
        if request.get("predecessor") is not None:
            value["predecessor"] = request["predecessor"]
        return value

    def _validate_request(self, request):
        request = _json(request, "remote request")
        required = {"schema", "operation_id", "operation", "source", "arguments"}
        if set(request) not in (required, required | {"predecessor"}):
            raise ImageBuildError("remote request has missing or unsupported fields")
        if request["schema"] != REQUEST_SCHEMA:
            raise ImageBuildError("unsupported remote request schema")
        self._directory(request["operation_id"])
        if request["operation"] not in SUPPORTED_OPERATIONS:
            raise ImageBuildError("unsupported remote operation")
        source = request["source"]
        if not isinstance(source, dict) or set(source) != {"repository", "revision"}:
            raise ImageBuildError("remote source binding requires repository and revision")
        if (
            source["repository"] != self.source_repository
            or source["revision"] != self.source_revision
        ):
            raise ImageBuildError("remote request source differs from deployed source")
        if not isinstance(request["arguments"], dict):
            raise ImageBuildError("remote operation arguments must be an object")
        if (
            self.external_observed_state
            and request["operation"] != "pipeline.inspect"
        ):
            raise ImageBuildError(
                "external observed state permits only pipeline.inspect"
            )
        predecessor = request.get("predecessor")
        if predecessor is not None:
            self._directory(predecessor)
            if predecessor == request["operation_id"]:
                raise ImageBuildError("remote operation cannot precede itself")
        return request

    def _save_request(self, request):
        directory = self._directory(request["operation_id"])
        ensure_directory(directory)
        path = directory / "request.json"
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except (OSError, ValueError, TypeError) as error:
                raise ImageBuildError("invalid retained remote request") from error
            if existing != request:
                raise ImageBuildError("remote operation identity belongs to different input")
        else:
            write_json(path, request)
        return directory

    def _binding(self, directory):
        path = directory / "binding.json"
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid retained remote operation binding") from error
        if not isinstance(value, dict):
            raise ImageBuildError("invalid retained remote operation binding")
        return value

    def _write_binding(self, directory, value):
        value = _json(value, "remote operation binding")
        path = directory / "binding.json"
        if path.exists():
            existing = self._binding(directory)
            if existing != value:
                raise ImageBuildError("remote operation binding changed")
        else:
            write_json(path, value)
        return value

    def _write_result(self, directory, result):
        result = _json(result, "remote result")
        encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        if len(encoded) > 128 * 1024:
            raise ImageBuildError("remote result exceeds bounded summary limit")
        write_json(directory / "result.json", result)
        return result

    def _state_generation(self, generation, state):
        if not isinstance(generation, str) or not _GENERATION.fullmatch(generation):
            raise ImageBuildError("invalid generation identity")
        from .engine import read_selection
        return read_selection(
            Path(state)
            / "image-build"
            / "generations"
            / generation
        )

    def _generation(self, generation):
        return self._state_generation(generation, self.control_state)

    def _observed_generation(self, generation):
        return self._state_generation(generation, self.observed_state)

    def _recipe(self, package):
        names([package])
        path = Path(self.builder.package_dir) / package
        if not path.is_dir():
            raise ImageBuildError("unknown package: " + package)
        return load_package(path)

    def _recipe_snapshot_store(self):
        from .recipe_snapshots import RecipeSnapshotStore

        return RecipeSnapshotStore(
            self.control_state, self.builder.package_dir
        )

    def _recipe_snapshot_context(self, arguments):
        allowed = {"entries", "pin_date"}
        if set(arguments) - allowed or "entries" not in arguments:
            raise ImageBuildError(
                "recipe snapshot requires entries and optional pin_date"
            )
        pin_date = arguments.get("pin_date")
        expected_monthly_identity = None
        provenance = self.builder.provenance
        if provenance is not None:
            bound = provenance.pin
            month = bound.get("month")
            if not isinstance(month, str):
                raise ImageBuildError(
                    "configured provenance lacks monthly pin identity"
                )
            if pin_date is not None and pin_date != month:
                raise ImageBuildError(
                    "recipe snapshot pin date differs from provenance pin"
                )
            pin_date = month
            monthly_path = (
                Path(self.builder.package_dir).resolve().parent
                / "pins"
                / month
                / "commit-pin.py"
            )
            try:
                relative = monthly_path.resolve(strict=True).relative_to(
                    self.repository_root
                ).as_posix()
            except (OSError, ValueError) as error:
                raise ImageBuildError(
                    "recipe snapshot monthly pin is outside deployed repository"
                ) from error
            if (
                relative != bound.get("path")
                or "sha256:" + _sha256(monthly_path)
                != bound.get("digest")
            ):
                raise ImageBuildError(
                    "recipe snapshot monthly pin differs from captured provenance"
                )
            from .pins import load as load_pin

            expected_monthly_identity = (
                "sha256:" + identity(load_pin(monthly_path))
            )
        if pin_date is None:
            raise ImageBuildError(
                "recipe snapshot requires explicit pin_date without provenance"
            )
        return pin_date, expected_monthly_identity

    def _recipe_snapshot_prepare(self, request, directory):
        arguments = request["arguments"]
        binding = self._binding(directory)
        if binding is not None:
            if set(binding) != {"recipe_snapshot"}:
                raise ImageBuildError(
                    "invalid retained recipe snapshot binding"
                )
            snapshot = self._resolve_recipe_snapshot(
                binding["recipe_snapshot"]
            )
        else:
            pin_date, expected_monthly_identity = (
                self._recipe_snapshot_context(arguments)
            )
            store = self._recipe_snapshot_store()
            with self.builder.locked():
                snapshot = store.prepare(
                    request["operation_id"],
                    entries=arguments["entries"],
                    pin_date=pin_date,
                    source_repository=self.source_repository,
                    source_revision=self.source_revision,
                    expected_monthly_identity=expected_monthly_identity,
                )
            self._write_binding(
                directory,
                {"recipe_snapshot": snapshot.snapshot},
            )
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
            allowed_next_operations=["pipeline.submit"],
        )
        result["recipe_identity"] = snapshot.snapshot
        result["artifacts"] = {
            "recipe_snapshot": snapshot.snapshot,
            "contract": snapshot.manifest["contract"],
            "pin_date": snapshot.manifest["pin_date"],
            "monthly_identity": snapshot.manifest[
                "monthly_identity"
            ],
            "packages": snapshot.manifest["packages"],
            "inventory_digest": (
                "sha256:" + identity(snapshot.manifest["inventory"])
            ),
            "manifest": (
                "image-build/recipe-snapshots/snapshots/"
                + snapshot.snapshot[7:]
                + "/manifest.json"
            ),
        }
        return result

    def _worker_inspect(self, request):
        arguments = request["arguments"]
        if set(arguments) not in (set(), {"worker"}):
            raise ImageBuildError(
                "worker inspection accepts only optional worker"
            )
        from .worker_contracts import describe

        contract = describe(arguments.get("worker"))
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
            allowed_next_operations=[],
        )
        result["artifacts"] = {
            "maintained_worker_contract": contract
        }
        return result

    def _resolve_recipe_snapshot(self, snapshot):
        value = self._recipe_snapshot_store().resolve(snapshot)
        if value.manifest["source"] != {
            "repository": self.source_repository,
            "revision": self.source_revision,
        }:
            raise ImageBuildError(
                "recipe snapshot belongs to a different deployed source revision"
            )
        return value

    def _builder_for_recipe_snapshot(self, snapshot):
        from .engine import ImageBuild

        return ImageBuild(
            package_dir=snapshot.package_dir,
            state_dir=self.builder.state,
            runner=self.builder.runner,
            maximum_generations=self.builder.maximum_generations,
            dependency_replacements=self.builder.dependency_replacements,
            provenance=self.builder.provenance,
            source_mirror=self.builder.source_mirror,
        )

    def _pipeline_owner(self, record):
        owner = record.get("owner")
        return owner if isinstance(owner, dict) else None

    def _find_owned_pipeline(self, request):
        matches = []
        pipelines = Path(self.builder.state) / "image-build" / "pipelines"
        if not pipelines.exists():
            return None
        for path in pipelines.glob("*/pipeline.json"):
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError, TypeError):
                continue
            owner = self._pipeline_owner(record)
            if (
                owner
                and owner.get("contract") == REQUEST_SCHEMA
                and owner.get("operation_id") == request["operation_id"]
            ):
                matches.append(record)
        if len(matches) > 1:
            raise ImageBuildError("remote operation owns multiple pipelines")
        return matches[0] if matches else None

    def _validate_submit_snapshot_predecessor(self, request, snapshot):
        predecessor = request.get("predecessor")
        if predecessor is None or request["operation"] != "pipeline.submit":
            return
        directory = self._directory(predecessor)
        try:
            previous_request = json.loads((directory / "request.json").read_text())
            previous_result = json.loads((directory / "result.json").read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError(
                "pipeline submit predecessor snapshot operation is unavailable"
            ) from error
        if (
            previous_request.get("operation_id") != predecessor
            or previous_request.get("operation") != "recipes.snapshot"
            or previous_request.get("source") != request["source"]
            or previous_result.get("schema") != RESULT_SCHEMA
            or previous_result.get("operation_id") != predecessor
            or previous_result.get("operation_type") != "recipes.snapshot"
            or previous_result.get("status") != "completed"
            or previous_result.get("terminal_outcome") != "success"
            or previous_result.get("recipe_identity") != snapshot.snapshot
        ):
            raise ImageBuildError(
                "pipeline submit predecessor must be the completed operation for the same recipe snapshot"
            )

    def _pipeline_arguments(self, request):
        arguments = request["arguments"]
        if set(arguments) - {
            "mode",
            "selection",
            "targets",
            "stages",
            "recipe_snapshot",
        }:
            raise ImageBuildError(
                "unsupported pipeline submission argument"
            )
        if "recipe_snapshot" not in arguments:
            raise ImageBuildError(
                "new remote pipeline submission requires recipe_snapshot"
            )
        snapshot = self._resolve_recipe_snapshot(
            arguments["recipe_snapshot"]
        )
        self._validate_submit_snapshot_predecessor(request, snapshot)
        packages = set(snapshot.manifest["packages"])
        mode = arguments.get("mode")
        if mode not in GENERIC_PIPELINE_MODES:
            raise ImageBuildError("invalid remote pipeline mode")
        selection = self._generation(arguments.get("selection"))
        if mode == "bootstrap":
            if set(arguments) != {
                "mode",
                "selection",
                "stages",
                "recipe_snapshot",
            }:
                raise ImageBuildError(
                    "bootstrap requires selection, stages, and recipe_snapshot"
                )
            stages = arguments["stages"]
            if (
                not isinstance(stages, list)
                or not stages
                or any(
                    not isinstance(stage, list) or not stage
                    for stage in stages
                )
            ):
                raise ImageBuildError(
                    "bootstrap stages must be nonempty package lists"
                )
            stages = [list(names(stage)) for stage in stages]
            selected = {
                package
                for stage in stages
                for package in stage
            }
            if not selected <= packages:
                raise ImageBuildError(
                    "pipeline stages are not present in recipe snapshot"
                )
            return (
                mode,
                selection,
                {"stages": stages},
                snapshot,
            )
        if set(arguments) != {
            "mode",
            "selection",
            "targets",
            "recipe_snapshot",
        }:
            raise ImageBuildError(
                "image/native pipeline requires selection, targets, and recipe_snapshot"
            )
        targets = list(names(arguments["targets"]))
        if not set(targets) <= packages:
            raise ImageBuildError(
                "pipeline targets are not present in recipe snapshot"
            )
        return (
            mode,
            selection,
            {"targets": targets},
            snapshot,
        )

    def _prepare_pipeline(self, request, directory):
        binding = self._binding(directory)
        if binding and binding.get("pipeline_id"):
            return binding["pipeline_id"]
        recovered = self._find_owned_pipeline(request)
        if recovered is not None:
            recipe_snapshot = self._pipeline_owner(
                recovered
            ).get("recipe_snapshot")
            value = {"pipeline_id": recovered["pipeline_id"]}
            if recipe_snapshot is not None:
                value["recipe_snapshot"] = recipe_snapshot
            self._write_binding(directory, value)
            return recovered["pipeline_id"]
        mode, selection, arguments, snapshot = (
            self._pipeline_arguments(request)
        )
        snapshot_builder = self._builder_for_recipe_snapshot(
            snapshot
        )
        record = snapshot_builder.prepare_pipeline(
            mode,
            selection,
            owner=self._owner(request),
            **arguments,
        )
        self._write_binding(
            directory,
            {
                "pipeline_id": record["pipeline_id"],
                "recipe_snapshot": snapshot.snapshot,
            },
        )
        return record["pipeline_id"]

    def _observed_pipeline_path(self, pipeline_id):
        if (
            not isinstance(pipeline_id, str)
            or len(pipeline_id) != 32
            or any(c not in "0123456789abcdef" for c in pipeline_id)
        ):
            raise ImageBuildError("invalid pipeline identity")
        return (
            self.observed_state
            / "image-build"
            / "pipelines"
            / pipeline_id
            / "pipeline.json"
        )

    def _inspect_pipeline_record(self, pipeline_id):
        if not self.external_observed_state:
            return self.builder.inspect_pipeline(pipeline_id), None
        path = self._observed_pipeline_path(pipeline_id)
        try:
            raw = path.read_bytes()
            record = json.loads(raw)
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError(
                "invalid or unavailable observed pipeline record"
            ) from error
        if (
            not isinstance(record, dict)
            or record.get("schema") != 1
            or record.get("pipeline_id") != pipeline_id
        ):
            raise ImageBuildError(
                "observed pipeline record identity differs"
            )
        return record, "sha256:" + hashlib.sha256(raw).hexdigest()

    def _attempt_paths(self, record):
        root = self.observed_state / "image-build" / "attempts"
        return [root / name for name in record.get("attempts", {}).values()]

    def _log_excerpt(self, job_id):
        if self.external_observed_state:
            return None
        execute = getattr(self.builder.runner, "execute", None)
        control = getattr(execute, "control", None)
        if control is None or not job_id:
            return None
        try:
            page = control.build_job_logs(job_id, limit=12)
        except Exception:
            return None
        entries = page.get("entries", []) if isinstance(page, dict) else []
        from .trace_records import sanitize
        messages = []
        total = 0
        for entry in entries[:12]:
            message = sanitize(str(entry.get("message", "")))
            encoded = message.encode("utf-8", "replace")
            if len(encoded) > 2048:
                message = encoded[:2048].decode("utf-8", "ignore") + "…"
                encoded = message.encode("utf-8")
            if total + len(encoded) > 8192:
                break
            total += len(encoded)
            messages.append(message)
        return {
            "messages": messages,
            "has_more": bool(page.get("has_more")),
        }

    def _evidence(self, record):
        commands = []
        failures = []
        missing = []
        observations = {}
        for attempt in self._attempt_paths(record):
            if not attempt.exists():
                missing.append(
                    {
                        "kind": "attempt-directory",
                        "locator": str(attempt.relative_to(self.observed_state)),
                    }
                )
                continue
            try:
                page = read_build_commands(attempt, limit=MAX_COMMANDS)
                commands.extend(page["commands"])
            except Exception:
                missing.append(
                    {
                        "kind": "command-view",
                        "locator": str(attempt.relative_to(self.observed_state)),
                    }
                )
            for path in sorted(attempt.rglob("*.execution.json")):
                try:
                    value = json.loads(path.read_text())
                except (OSError, ValueError, TypeError):
                    continue
                if (
                    value.get("cleanup_complete") is True
                    and type(value.get("exit_code")) is int
                    and value["exit_code"] != 0
                ):
                    failures.append(
                        {
                            "kind": "command-exit",
                            "exit_code": value["exit_code"],
                            "journal_reference": value.get("journal_reference"),
                            "process_cleanup_complete": value.get(
                                "process_cleanup_complete"
                            ),
                            "locator": str(path.relative_to(self.observed_state)),
                        }
                    )
            for path in sorted(attempt.rglob("*.observation.json")):
                try:
                    value = json.loads(path.read_text())
                except (OSError, ValueError, TypeError):
                    continue
                if value.get("job_id"):
                    observations[value["job_id"]] = {
                        key: value.get(key)
                        for key in (
                            "state",
                            "outcome",
                            "exit_code",
                            "signal",
                            "journal_reference",
                            "process_cleanup_complete",
                        )
                        if key in value
                    }
                if value.get("outcome") in {
                    "nonzero-exit",
                    "signal",
                    "timeout",
                    "fault",
                    "cancelled",
                    "unknown",
                }:
                    failures.append(
                        {
                            "kind": "controller-outcome",
                            "outcome": value.get("outcome"),
                            "job_id": value.get("job_id"),
                            "exit_code": value.get("exit_code"),
                            "signal": value.get("signal"),
                            "journal_reference": value.get("journal_reference"),
                            "process_cleanup_complete": value.get(
                                "process_cleanup_complete"
                            ),
                            "locator": str(path.relative_to(self.observed_state)),
                        }
                    )
        commands = commands[:MAX_COMMANDS]
        missing = missing[:MAX_MISSING]
        jobs = []
        for command in commands:
            if command.get("job_id"):
                job = {
                    "job_id": command["job_id"],
                    "request_id": command.get("request_id"),
                    "attempt_id": command.get("attempt_id"),
                    "package": command.get("package"),
                    "stage": command.get("stage_id"),
                    "phase": command.get("phase"),
                    "command_index": command.get("command_index"),
                    "command_key": command.get("command_key"),
                    "command": command.get("command"),
                }
                job.update(observations.get(command["job_id"], {}))
                excerpt = self._log_excerpt(command["job_id"])
                if excerpt is not None:
                    job["log_excerpt"] = excerpt
                jobs.append(job)
        return commands, jobs, failures, missing

    def _pipeline_selection_generation(self, record):
        selection = record.get("selection")
        if not isinstance(selection, str):
            return None
        candidate = Path(selection).name
        return candidate if _GENERATION.fullmatch(candidate) else None

    def _pipeline_execution_evidence(
        self, record, pipeline_record_digest, jobs
    ):
        owner = self._pipeline_owner(record)
        compact_jobs = []
        fields = (
            "job_id",
            "request_id",
            "attempt_id",
            "package",
            "stage",
            "phase",
            "command_index",
            "state",
            "outcome",
            "exit_code",
            "signal",
            "journal_reference",
            "process_cleanup_complete",
        )
        for job in jobs[:MAX_COMMANDS]:
            compact_jobs.append(
                {key: job.get(key) for key in fields if key in job}
            )
        policy = record.get("policy")
        value = {
            "contract": EXECUTION_EVIDENCE_SCHEMA,
            "pipeline_id": record.get("pipeline_id"),
            "pipeline_operation": record.get("operation"),
            "pipeline_status": record.get("status"),
            "pipeline_record_sha256": pipeline_record_digest,
            "pipeline_owner": owner,
            "recipe_snapshot": (
                owner.get("recipe_snapshot") if owner else None
            ),
            "source_pins": record.get("source_pins"),
            "selection_generation": self._pipeline_selection_generation(record),
            "policy_identity": (
                None if policy is None else "sha256:" + identity(policy)
            ),
            "attempt_ids": sorted(record.get("attempts", {}).values()),
            "controller_jobs": compact_jobs,
            "output_generation": record.get("generation"),
            "observation_snapshot": record.get("observation_snapshot"),
        }
        return value

    def _pipeline_summary(self, request, pipeline_id, *, raised=None):
        try:
            record, pipeline_record_digest = self._inspect_pipeline_record(
                pipeline_id
            )
        except Exception as error:
            result = self._base_result(
                request,
                status="pending",
                terminal_outcome=None,
                uncertainty=True,
                failure={"type": type(error).__name__, "reason": str(error)},
                missing_evidence=[{"kind": "pipeline-record", "locator": pipeline_id}],
                allowed_next_operations=["pipeline.inspect"],
                pipeline_id=pipeline_id,
            )
            if self.external_observed_state:
                result["artifacts"]["observation_source"] = {
                    "kind": "external-state"
                }
            return result
        commands, jobs, failures, missing = self._evidence(record)
        status = record.get("status")
        uncertainty = False
        outcome = None
        allowed = []
        failure = None
        if status == "complete":
            remote_status = "completed"
            outcome = "success"
        elif status == "released":
            remote_status = "released"
            outcome = "released"
            allowed = ["pipeline.inspect"]
        else:
            unknown = any(item.get("outcome") == "unknown" for item in failures)
            terminal = [
                item
                for item in failures
                if item.get("kind") == "command-exit"
                or (
                    item.get("outcome") not in (None, "unknown")
                    and item.get("process_cleanup_complete") is not False
                )
            ]
            if terminal:
                remote_status = "failed"
                outcome = terminal[-1].get("outcome") or "nonzero-exit"
                failure = terminal[-1]
                allowed = ["pipeline.retry", "pipeline.inspect"]
            else:
                remote_status = "pending"
                uncertainty = unknown or "unknown" in str(record.get("error", "")).lower()
                failure = (
                    {"type": type(raised).__name__, "reason": str(raised)}
                    if raised is not None
                    else (
                        {"type": "pending", "reason": record.get("error")}
                        if record.get("error")
                        else None
                    )
                )
                allowed = ["pipeline.resume", "pipeline.inspect", "pipeline.cancel"]
        if status == "complete":
            allowed = ["pipeline.inspect"]
        result = self._base_result(
            request,
            status=remote_status,
            terminal_outcome=outcome,
            uncertainty=uncertainty,
            failure=failure,
            missing_evidence=missing,
            allowed_next_operations=allowed,
            pipeline_id=pipeline_id,
        )
        if self.external_observed_state:
            result["allowed_next_operations"] = ["pipeline.inspect"]
            result["artifacts"]["observation_source"] = {
                "kind": "external-state",
                "pipeline_record_sha256": pipeline_record_digest,
            }
        owner = self._pipeline_owner(record)
        if owner and owner.get("recipe_snapshot"):
            result["recipe_identity"] = owner["recipe_snapshot"]
            result["artifacts"]["recipe_snapshot"] = owner[
                "recipe_snapshot"
            ]
        result["attempt_ids"] = sorted(record.get("attempts", {}).values())
        result["controller_jobs"] = jobs[:MAX_COMMANDS]
        result["log_locators"] = [
            {
                "job_id": item.get("job_id"),
                "journal_reference": item.get("journal_reference"),
                "locator": item.get("locator"),
            }
            for item in failures
            if item.get("journal_reference") or item.get("locator")
        ][:MAX_COMMANDS]
        result["package"] = jobs[-1].get("package") if jobs else None
        result["stage"] = jobs[-1].get("stage") if jobs else None
        result["phase"] = jobs[-1].get("phase") if jobs else None
        if record.get("generation"):
            result["selected_generation"] = record["generation"]
            try:
                selection = self._observed_generation(record["generation"])
                result["artifacts"].update({
                    "generation_manifest": str(
                        selection.root.parent.relative_to(self.observed_state)
                        / "manifest.json"
                    ),
                    "generation_inventory_digest": "sha256:"
                    + identity(selection.manifest["outputs"]),
                })
                result["provenance"] = {
                    key: selection.manifest[key]
                    for key in ("build_record", "verification_execution")
                    if key in selection.manifest
                }
                if record.get("observation_snapshot"):
                    result["provenance"]["observation_snapshot"] = record[
                        "observation_snapshot"
                    ]
                    result["provenance"]["build_trace"] = {
                        "snapshot": record["observation_snapshot"]
                    }
            except Exception:
                result["missing_evidence"].append(
                    {"kind": "generation", "locator": record["generation"]}
                )
        result["artifacts"]["execution_evidence"] = self._pipeline_execution_evidence(
            record, pipeline_record_digest, jobs
        )
        return result

    def _base_result(
        self,
        request,
        *,
        status,
        terminal_outcome,
        uncertainty=False,
        failure=None,
        missing_evidence=None,
        allowed_next_operations=None,
        pipeline_id=None,
    ):
        return {
            "schema": RESULT_SCHEMA,
            "operation_id": request["operation_id"],
            "operation_type": request["operation"],
            "source_repository": request["source"]["repository"],
            "source_revision": request["source"]["revision"],
            "recipe_identity": None,
            "pipeline_id": pipeline_id,
            "attempt_ids": [],
            "selected_generation": None,
            "package": None,
            "stage": None,
            "phase": None,
            "status": status,
            "terminal_outcome": terminal_outcome,
            "failure": failure,
            "controller_jobs": [],
            "log_locators": [],
            "artifacts": {},
            "provenance": {},
            "uncertainty": bool(uncertainty),
            "missing_evidence": list(missing_evidence or [])[:MAX_MISSING],
            "allowed_next_operations": list(allowed_next_operations or []),
            "predecessor": request.get("predecessor"),
        }

    def _capabilities_inspect(self, request):
        if request["arguments"]:
            raise ImageBuildError(
                "capability inspection accepts no arguments"
            )
        from .recipe_snapshots import CONTRACT as SNAPSHOT_CONTRACT
        from .runtime_requirements import describe as describe_runtime
        from .worker_contracts import describe as describe_workers

        workers = describe_workers()
        capabilities = {
            "contract": CAPABILITIES_SCHEMA,
            "request_contract": REQUEST_SCHEMA,
            "result_contract": RESULT_SCHEMA,
            "source": {
                "repository": self.source_repository,
                "revision": self.source_revision,
            },
            "operations": list(SUPPORTED_OPERATIONS),
            "generic_pipeline": {
                "supported": True,
                "recipe_snapshot": {
                    "operation": "recipes.snapshot",
                    "contract": SNAPSHOT_CONTRACT,
                    "required_for": [
                        "pipeline.submit",
                        "pipeline.retry",
                    ],
                },
                "submit": {
                    "operation": "pipeline.submit",
                    "modes": list(GENERIC_PIPELINE_MODES),
                    "requires_recipe_snapshot": True,
                    "snapshot_predecessor": {
                        "field": "predecessor",
                        "operation": "recipes.snapshot",
                        "required": False,
                        "when_present": "must-bind-same-completed-snapshot",
                    },
                    "image_like_arguments": [
                        "mode",
                        "selection",
                        "targets",
                        "recipe_snapshot",
                    ],
                    "bootstrap_arguments": [
                        "mode",
                        "selection",
                        "stages",
                        "recipe_snapshot",
                    ],
                },
                "recovery": {
                    "inspect": "pipeline.inspect",
                    "resume": "pipeline.resume",
                    "cancel": "pipeline.cancel",
                    "retry": "pipeline.retry",
                    "automatic_retry": False,
                    "retry_requires_resolved_terminal_failure": True,
                },
            },
            "maintained_workers": {
                "contract": workers["contract"],
                "inspection_operation": "worker.inspect",
                "remote_execution_operation": None,
                "generic_pipeline_submit_equivalent": False,
                "workers": sorted(workers["workers"]),
            },
            "external_observed_state": {
                "operations": ["pipeline.inspect"],
                "mutation": False,
            },
            "reporting": {
                "execution_evidence_contract": EXECUTION_EVIDENCE_SCHEMA,
                "controller_jobs_limit": MAX_COMMANDS,
                "result_bytes_limit": 128 * 1024,
            },
            "runtime_dependencies": describe_runtime(),
        }
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
            allowed_next_operations=[
                "recipes.snapshot",
                "pipeline.submit",
                "pipeline.inspect",
            ],
        )
        result["artifacts"] = {
            "remote_capabilities": capabilities
        }
        return result

    def _recipe_validate(self, request):
        from .pins import validate
        packages = load_packages(self.builder.package_dir)
        pin = validate(self.builder.package_dir, packages)
        package = request["arguments"].get("package")
        if set(request["arguments"]) - {"package"}:
            raise ImageBuildError("recipe validation accepts only package")
        if package is not None:
            value = self._recipe(package)
            packages = {package: value}
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
            allowed_next_operations=[],
        )
        result["artifacts"] = {
            "pin_identity": "sha256:" + identity(pin),
            "packages": {
                name: {"recipe_identity": value.fingerprint}
                for name, value in sorted(packages.items())
            },
        }
        return result

    def _package_inspect(self, request):
        if set(request["arguments"]) != {"package"}:
            raise ImageBuildError("package inspection requires package")
        package = self._recipe(request["arguments"]["package"])
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
        )
        result["package"] = package.name
        result["recipe_identity"] = package.fingerprint
        result["artifacts"] = {
            "sources": list(package.sources),
            "build_dependencies": list(package.build_dependencies),
            "runtime_dependencies": list(package.runtime_dependencies),
            "test_dependencies": list(package.test_dependencies),
            "outputs": list(package.outputs),
            "output_trees": list(package.output_trees),
            "licensing": package.licensing,
            "source_provenance": package.source_provenance,
        }
        return result

    def _dependencies(self, request):
        arguments = request["arguments"]
        if set(arguments) not in ({"targets"}, {"targets", "runtime_only"}):
            raise ImageBuildError("dependency resolution requires targets")
        packages = load_packages(self.builder.package_dir)
        targets = list(names(arguments["targets"]))
        resolved = order(
            packages,
            targets,
            runtime_only=arguments.get("runtime_only", False) is True,
        )
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
        )
        result["artifacts"] = {"targets": targets, "dependency_order": list(resolved)}
        return result

    def _pipeline_submit(self, request, directory):
        pipeline_id = self._prepare_pipeline(request, directory)
        try:
            self.builder.resume(pipeline_id)
            raised = None
        except BaseException as error:
            raised = error
        return self._pipeline_summary(request, pipeline_id, raised=raised)

    def _pipeline_inspect(self, request, directory):
        if set(request["arguments"]) != {"pipeline_id"}:
            raise ImageBuildError("pipeline inspection requires pipeline_id")
        pipeline_id = request["arguments"]["pipeline_id"]
        if self.external_observed_state:
            self._write_binding(
                directory,
                {
                    "observation_source": {
                        "kind": "external-state",
                        "state_dir": str(self.observed_state),
                        "pipeline_id": pipeline_id,
                    }
                },
            )
        return self._pipeline_summary(request, pipeline_id)

    def _owned_pipeline(self, pipeline_id, action):
        record = self.builder.inspect_pipeline(pipeline_id)
        owner = self._pipeline_owner(record)
        if (
            owner is None
            or owner.get("contract") != REQUEST_SCHEMA
            or owner.get("source_revision") != self.source_revision
            or owner.get("source_repository") != self.source_repository
        ):
            raise ImageBuildError(
                "remote " + action
                + " requires the originally bound deployed source revision"
            )
        return record

    def _pipeline_resume(self, request):
        if set(request["arguments"]) != {"pipeline_id"}:
            raise ImageBuildError("pipeline resume requires pipeline_id")
        pipeline_id = request["arguments"]["pipeline_id"]
        self._owned_pipeline(pipeline_id, "resume")
        try:
            self.builder.resume(pipeline_id)
            raised = None
        except BaseException as error:
            raised = error
        return self._pipeline_summary(request, pipeline_id, raised=raised)

    def _cancel_pipeline_jobs(self, record):
        checkpoints = []
        for attempt in self._attempt_paths(record):
            if attempt.exists():
                checkpoints.extend(sorted(attempt.rglob("*.controller.json")))
        if not checkpoints:
            return
        execute = getattr(self.builder.runner, "execute", None)
        control = getattr(execute, "control", None)
        if control is None:
            raise ImageBuildError(
                "pipeline cancellation requires configured box-control execution"
            )
        from .box_control_adapter import BuildExecutionPending
        from .trace_records import capture_observation

        for checkpoint in checkpoints:
            try:
                saved = json.loads(checkpoint.read_text())
                job_id = saved["job_id"]
            except (OSError, KeyError, ValueError, TypeError) as error:
                raise ImageBuildError(
                    "invalid retained controller checkpoint during cancellation"
                ) from error
            observed = control.refresh_build_job(job_id)
            capture_observation(checkpoint, observed)
            if not observed.get("process_cleanup_complete"):
                observed = control.cancel_build_job(job_id)
                capture_observation(checkpoint, observed)
            if not observed.get("process_cleanup_complete"):
                raise BuildExecutionPending(observed)

    def _pipeline_cancel(self, request, directory):
        if set(request["arguments"]) != {"pipeline_id"}:
            raise ImageBuildError("pipeline cancellation requires pipeline_id")
        pipeline_id = request["arguments"]["pipeline_id"]
        record = self._owned_pipeline(pipeline_id, "cancellation")
        summary = self._pipeline_summary(request, pipeline_id)
        if summary["status"] in {"completed", "released"}:
            return summary
        if summary["status"] == "failed" and not summary["uncertainty"]:
            raise ImageBuildError(
                "terminal failed pipeline requires retry or inspection, not cancellation"
            )

        binding = self._binding(directory)
        if binding is None:
            binding = self._write_binding(
                directory,
                {"pipeline_id": pipeline_id, "phase": "cancel-jobs"},
            )
        elif binding.get("pipeline_id") != pipeline_id:
            raise ImageBuildError("remote cancellation pipeline identity changed")

        if binding.get("phase") == "cancel-jobs":
            self._cancel_pipeline_jobs(record)
            binding = {"pipeline_id": pipeline_id, "phase": "release"}
            write_json(directory / "binding.json", binding)
        if binding.get("phase") == "release":
            self.builder.release_pipeline(pipeline_id)
            binding = {"pipeline_id": pipeline_id, "phase": "complete"}
            write_json(directory / "binding.json", binding)
        if binding.get("phase") != "complete":
            raise ImageBuildError("invalid retained pipeline cancellation phase")
        return self._pipeline_summary(request, pipeline_id)

    def _predecessor_pipeline(self, request):
        predecessor = request.get("predecessor")
        if predecessor is None:
            raise ImageBuildError("retry requires predecessor remote operation")
        directory = self._directory(predecessor)
        binding = self._binding(directory)
        if not binding or not binding.get("pipeline_id"):
            raise ImageBuildError("predecessor has no retained pipeline identity")
        prior_request = json.loads((directory / "request.json").read_text())
        summary = self._pipeline_summary(
            prior_request,
            binding["pipeline_id"],
        )
        return binding["pipeline_id"], summary

    def _pipeline_retry(self, request, directory):
        # Validate the replacement snapshot/generation before releasing the
        # terminal predecessor.
        mode, selection, arguments, snapshot = (
            self._pipeline_arguments(request)
        )
        binding = self._binding(directory)
        if binding is None:
            predecessor_pipeline, summary = self._predecessor_pipeline(request)
            if (
                summary["status"] != "failed"
                or summary["uncertainty"]
            ):
                raise ImageBuildError(
                    "retry requires a terminal failed predecessor with resolved outcome"
                )
            binding = self._write_binding(
                directory,
                {
                    "predecessor_pipeline_id": predecessor_pipeline,
                    "recipe_snapshot": snapshot.snapshot,
                    "phase": "release-predecessor",
                },
            )
        if binding.get("recipe_snapshot") != snapshot.snapshot:
            raise ImageBuildError(
                "retry recipe snapshot differs from durable binding"
            )
        predecessor_pipeline = binding["predecessor_pipeline_id"]
        if binding["phase"] == "release-predecessor":
            self.builder.release_pipeline(predecessor_pipeline)
            binding = {
                "predecessor_pipeline_id": predecessor_pipeline,
                "recipe_snapshot": snapshot.snapshot,
                "phase": "prepare-retry",
            }
            write_json(directory / "binding.json", binding)
        if binding["phase"] == "prepare-retry":
            recovered = self._find_owned_pipeline(request)
            if recovered is None:
                snapshot_builder = (
                    self._builder_for_recipe_snapshot(snapshot)
                )
                record = snapshot_builder.prepare_pipeline(
                    mode,
                    selection,
                    owner=self._owner(request),
                    **arguments,
                )
                pipeline_id = record["pipeline_id"]
            else:
                pipeline_id = recovered["pipeline_id"]
            binding = {
                "predecessor_pipeline_id": predecessor_pipeline,
                "recipe_snapshot": snapshot.snapshot,
                "phase": "run-retry",
                "pipeline_id": pipeline_id,
            }
            write_json(directory / "binding.json", binding)
        pipeline_id = binding["pipeline_id"]
        try:
            self.builder.resume(pipeline_id)
            raised = None
        except BaseException as error:
            raised = error
        return self._pipeline_summary(
            request, pipeline_id, raised=raised
        )

    def _generation_inspect(self, request):
        if set(request["arguments"]) != {"generation"}:
            raise ImageBuildError("generation inspection requires generation")
        selection = self._generation(request["arguments"]["generation"])
        result = self._base_result(
            request,
            status="completed",
            terminal_outcome="success",
        )
        result["selected_generation"] = selection.generation
        generation_inventory = selection.manifest["outputs"]
        result["artifacts"] = {
            "kind": selection.manifest["kind"],
            "generation_manifest": str(
                selection.root.parent.relative_to(Path(self.builder.state))
                / "manifest.json"
            ),
            "inventory": generation_inventory[:MAX_INVENTORY_ITEMS],
            "inventory_count": len(generation_inventory),
            "inventory_truncated": len(generation_inventory) > MAX_INVENTORY_ITEMS,
            "inventory_digest": "sha256:" + identity(generation_inventory),
        }
        result["provenance"] = {
            key: selection.manifest[key]
            for key in (
                "build_record",
                "verification_execution",
                "source_built",
                "self_hosted",
            )
            if key in selection.manifest
        }
        if (
            self.builder.provenance is not None
            and self.builder.provenance.generation_contract
        ):
            try:
                snapshot = self.builder.selected_observation_snapshot(
                    selection.generation
                )
            except Exception:
                result["missing_evidence"].append(
                    {
                        "kind": "observation-snapshot",
                        "locator": selection.generation,
                    }
                )
            else:
                if snapshot is None:
                    result["missing_evidence"].append(
                        {
                            "kind": "observation-snapshot",
                            "locator": selection.generation,
                        }
                    )
                else:
                    result["provenance"]["observation_snapshot"] = snapshot
                    result["provenance"]["build_trace"] = {
                        "snapshot": snapshot["snapshot"]
                    }
        return result

    def _diagnostic_definition(self, name):
        if not isinstance(name, str) or not _DIAGNOSTIC.fullmatch(name):
            raise ImageBuildError("invalid diagnostic identity")
        root = self.repository_root / "project" / "diagnostic" / name
        declaration = root / "diagnostic.json"
        if root.is_symlink() or declaration.is_symlink():
            raise ImageBuildError("diagnostic definition must not be a symlink")
        try:
            value = json.loads(declaration.read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid diagnostic declaration") from error
        required = {
            "schema",
            "script",
            "interpreter",
            "timeout_seconds",
            "memory_maximum_bytes",
            "thread_count_maximum",
            "cpu_weight",
            "output_limit_bytes",
            "outputs",
        }
        if not isinstance(value, dict) or set(value) != required or value["schema"] != 1:
            raise ImageBuildError("unsupported diagnostic declaration")
        script = _relative(value["script"], "diagnostic script")
        if not script.endswith(".py"):
            raise ImageBuildError("diagnostic script must be Python source")
        source = root / script
        if source.is_symlink() or not source.is_file() or source.stat().st_size > 256 * 1024:
            raise ImageBuildError("diagnostic script is missing, unsafe, or too large")
        interpreter = value["interpreter"]
        if (
            not isinstance(interpreter, str)
            or not interpreter.startswith("/")
            or ".." in PurePosixPath(interpreter).parts
            or "\0" in interpreter
        ):
            raise ImageBuildError("diagnostic interpreter must be an absolute guest path")
        for key, maximum in (
            ("timeout_seconds", 3600),
            ("memory_maximum_bytes", 2**63 - 1),
            ("thread_count_maximum", 2**31 - 1),
            ("output_limit_bytes", 1024**3),
        ):
            if type(value[key]) is not int or not 1 <= value[key] <= maximum:
                raise ImageBuildError("invalid diagnostic " + key)
        if type(value["cpu_weight"]) is not int or not 1 <= value["cpu_weight"] <= 10000:
            raise ImageBuildError("diagnostic cpu_weight must be 1..10000")
        if (
            not isinstance(value["outputs"], list)
            or len(value["outputs"]) > 32
            or len(set(value["outputs"])) != len(value["outputs"])
        ):
            raise ImageBuildError("invalid diagnostic outputs")
        outputs = [_relative(item, "diagnostic output") for item in value["outputs"]]
        return root, dict(value, script=script, outputs=outputs), source

    def _diagnostic_binding(self, request, directory):
        binding = self._binding(directory)
        if binding is not None:
            return binding
        arguments = request["arguments"]
        if set(arguments) != {"diagnostic", "generation", "argv"}:
            raise ImageBuildError(
                "diagnostic submission requires diagnostic, generation, and argv"
            )
        argv = arguments["argv"]
        if (
            not isinstance(argv, list)
            or len(argv) > 64
            or any(
                not isinstance(value, str)
                or "\0" in value
                or len(value) > 4096
                for value in argv
            )
        ):
            raise ImageBuildError("invalid diagnostic argument vector")
        selection = self._generation(arguments["generation"])
        definition_root, definition, script = self._diagnostic_definition(
            arguments["diagnostic"]
        )
        attempt = (
            Path(self.builder.state)
            / "image-build"
            / "attempts"
            / ("diagnostic-" + request["operation_id"])
        )
        ensure_directory(attempt)
        root = attempt / "root"
        source = attempt / "source"
        output = attempt / "output"
        if not (attempt / "diagnostic-binding.json").exists():
            if root.exists() or source.exists() or output.exists():
                raise ImageBuildError("partial diagnostic staging exists without binding")
            shutil.copytree(selection.root, root, symlinks=True)
            source.mkdir()
            output.mkdir()
            target = source / definition["script"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(script, target)
            prepared = {
                "root": inventory(root),
                "binding": {
                    "contract": DIAGNOSTIC_SCHEMA,
                    "source_revision": self.source_revision,
                    "generation": selection.generation,
                    "diagnostic": arguments["diagnostic"],
                    "script_sha256": _sha256(script),
                },
            }
            write_json(attempt / "prepared.json", prepared)
            diagnostic_binding = {
                "schema": 1,
                "attempt_id": attempt.name,
                "generation": selection.generation,
                "diagnostic": arguments["diagnostic"],
                "script": definition["script"],
                "script_sha256": _sha256(script),
                "argv": argv,
                "definition": definition,
            }
            write_json(attempt / "diagnostic-binding.json", diagnostic_binding)
            write_json(
                attempt / "status.json",
                {
                    "status": "running",
                    "kind": "diagnostic",
                    "remote_operation_id": request["operation_id"],
                },
            )
        diagnostic_binding = json.loads(
            (attempt / "diagnostic-binding.json").read_text()
        )
        binding = {
            "attempt_id": attempt.name,
            "diagnostic": diagnostic_binding,
        }
        self._write_binding(directory, binding)
        return binding

    def _diagnostic_result(self, request, binding, *, refresh):
        attempt = (
            Path(self.builder.state)
            / "image-build"
            / "attempts"
            / binding["attempt_id"]
        )
        diagnostic = binding["diagnostic"]
        definition = diagnostic["definition"]
        checkpoint = attempt / "diagnostic.controller.json"
        raised = None
        result = None
        if refresh:
            execute = getattr(self.builder.runner, "execute", None)
            if execute is None or not hasattr(execute, "execute_for_attempt"):
                raise ImageBuildError(
                    "diagnostics require configured box-control execution"
                )
            from .box_control_adapter import BoxControlExecutionAdapter
            from .configuration import input_manifest

            limits = {
                "thread-count-maximum": definition["thread_count_maximum"],
                "memory-maximum-bytes": definition["memory_maximum_bytes"],
                "cpu-weight": definition["cpu_weight"],
            }
            adapter = BoxControlExecutionAdapter(
                execute.control,
                execution_user_id=execute.execution_user_id,
                execution_group_id=execute.execution_group_id,
                startup_timeout_seconds=execute.startup_timeout_seconds,
                termination_grace_seconds=execute.termination_grace_seconds,
                wait_timeout_seconds=execute.wait_timeout_seconds,
                resource_limits=limits,
                input_manifest_id=input_manifest,
            )
            request_value = BuildExecutionRequest(
                root=attempt / "root",
                source=attempt / "source",
                output=attempt / "output",
                command=(
                    definition["interpreter"],
                    "/image-build/source/" + definition["script"],
                    *diagnostic["argv"],
                ),
                environment={
                    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                    "LANG": "C",
                    "LC_ALL": "C",
                    "HOME": "/tmp",
                    "IMAGE_BUILD_SOURCE": "/image-build/source",
                    "IMAGE_BUILD_OUTPUT": "/image-build/output",
                },
                working_directory="/image-build/source",
                timeout_seconds=definition["timeout_seconds"],
                read_only_root=True,
                network_access=False,
            )
            try:
                result = adapter.execute_for_attempt(request_value, checkpoint)
            except BaseException as error:
                raised = error
        observation = checkpoint.with_name("diagnostic.observation.json")
        record = None
        if observation.exists():
            try:
                record = json.loads(observation.read_text())
            except (OSError, ValueError, TypeError):
                record = None
        status = "pending"
        terminal = None
        uncertainty = False
        failure = None
        if result is not None:
            status = "completed" if result.exit_code == 0 else "failed"
            terminal = "success" if result.exit_code == 0 else "nonzero-exit"
        elif record and record.get("outcome") in {
            "nonzero-exit",
            "signal",
            "timeout",
            "fault",
            "cancelled",
        }:
            status = "failed"
            terminal = record["outcome"]
            failure = {
                "type": "controller-outcome",
                "reason": record.get("error"),
                "job_id": record.get("job_id"),
            }
        elif record and record.get("outcome") == "unknown":
            uncertainty = True
            failure = {"type": "unknown-controller-outcome", "reason": record.get("error")}
        elif raised is not None:
            failure = {"type": type(raised).__name__, "reason": str(raised)}
            uncertainty = "unknown" in str(raised).lower()
        outputs = []
        total = 0
        for relative in definition["outputs"]:
            path = attempt / "output" / relative
            if path.is_symlink():
                failure = {"type": "unsafe-output", "reason": relative}
                status = "failed"
                terminal = "invalid-output"
                break
            if path.is_file():
                size = path.stat().st_size
                total += size
                outputs.append(
                    {
                        "path": relative,
                        "bytes": size,
                        "sha256": _sha256(path),
                    }
                )
        if total > definition["output_limit_bytes"]:
            status = "failed"
            terminal = "output-limit"
            failure = {
                "type": "output-limit",
                "reason": f"{total} bytes exceeds {definition['output_limit_bytes']}",
            }
        if status in {"completed", "failed"}:
            write_json(
                attempt / "status.json",
                {
                    "status": "complete" if status == "completed" else "failed",
                    "kind": "diagnostic",
                    "remote_operation_id": request["operation_id"],
                },
            )
        result_value = self._base_result(
            request,
            status=status,
            terminal_outcome=terminal,
            uncertainty=uncertainty,
            failure=failure,
            allowed_next_operations=(
                ["diagnostic.inspect"]
                if status == "completed"
                else (
                    ["diagnostic.inspect", "diagnostic.submit"]
                    if status == "failed"
                    else ["diagnostic.submit", "diagnostic.inspect"]
                )
            ),
        )
        result_value["attempt_ids"] = [attempt.name]
        result_value["selected_generation"] = diagnostic["generation"]
        result_value["stage"] = "diagnostic"
        result_value["phase"] = diagnostic["diagnostic"]
        result_value["artifacts"] = {
            "script_sha256": diagnostic["script_sha256"],
            "outputs": outputs,
            "output_directory": str(
                (attempt / "output").relative_to(Path(self.builder.state))
            ),
        }
        if checkpoint.exists():
            try:
                saved = json.loads(checkpoint.read_text())
                result_value["controller_jobs"] = [
                    {
                        "job_id": saved.get("job_id"),
                        "request_id": saved.get("request_id"),
                        "attempt_id": attempt.name,
                        "package": "diagnostic",
                        "stage": "diagnostic",
                        "phase": diagnostic["diagnostic"],
                        "command_index": 0,
                        "command_key": "diagnostic",
                    }
                ]
            except Exception:
                result_value["missing_evidence"].append(
                    {"kind": "diagnostic-checkpoint", "locator": str(checkpoint)}
                )
        return result_value

    def _diagnostic_submit(self, request, directory):
        binding = self._diagnostic_binding(request, directory)
        return self._diagnostic_result(request, binding, refresh=True)

    def _diagnostic_inspect(self, request):
        if set(request["arguments"]) != {"operation_id"}:
            raise ImageBuildError("diagnostic inspection requires operation_id")
        target = self._directory(request["arguments"]["operation_id"])
        binding = self._binding(target)
        if not binding or not binding.get("attempt_id"):
            raise ImageBuildError("diagnostic operation has no retained attempt")
        return self._diagnostic_result(request, binding, refresh=False)

    def execute(self, raw):
        request = self._validate_request(raw)
        directory = self._directory(request["operation_id"])
        ensure_directory(directory)
        # Duplicate callers for one durable operation identity serialize before
        # request/binding creation. Different operation identities may inspect in
        # parallel; image-build's state-local lock still serializes pipeline mutation.
        with (directory / "operation.lock").open("a+") as operation_lock:
            fcntl.flock(operation_lock, fcntl.LOCK_EX)
            directory = self._save_request(request)
            operation = request["operation"]
            try:
                if operation == "capabilities.inspect":
                    result = self._capabilities_inspect(request)
                elif operation == "recipe.validate":
                    result = self._recipe_validate(request)
                elif operation == "recipes.snapshot":
                    result = self._recipe_snapshot_prepare(
                        request, directory
                    )
                elif operation == "worker.inspect":
                    result = self._worker_inspect(request)
                elif operation == "package.inspect":
                    result = self._package_inspect(request)
                elif operation == "dependencies.resolve":
                    result = self._dependencies(request)
                elif operation == "pipeline.submit":
                    result = self._pipeline_submit(request, directory)
                elif operation == "pipeline.inspect":
                    result = self._pipeline_inspect(request, directory)
                elif operation == "pipeline.resume":
                    result = self._pipeline_resume(request)
                elif operation == "pipeline.cancel":
                    result = self._pipeline_cancel(request, directory)
                elif operation == "pipeline.retry":
                    result = self._pipeline_retry(request, directory)
                elif operation == "generation.inspect":
                    result = self._generation_inspect(request)
                elif operation == "diagnostic.submit":
                    result = self._diagnostic_submit(request, directory)
                else:
                    result = self._diagnostic_inspect(request)
            except BaseException as error:
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise
                result = self._base_result(
                    request,
                    status="failed",
                    terminal_outcome="request-error",
                    failure={"type": type(error).__name__, "reason": str(error)},
                    allowed_next_operations=[],
                )
            return self._write_result(directory, result)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument(
        "--observed-state-dir",
        type=Path,
        help="absolute read-only historical state root used only by pipeline.inspect",
    )
    parser.add_argument("--controller-config", type=Path)
    parser.add_argument("--source-mirror-config", type=Path)
    parser.add_argument("--provenance-host-id")
    parser.add_argument("--provenance-project-id")
    parser.add_argument(
        "--provenance-pin",
        type=Path,
        help="absolute path to the original reviewed monthly provenance pin inside --repository-root",
    )
    parser.add_argument("--expected-pin-digest")
    parser.add_argument("request", type=Path)
    args = parser.parse_args()

    runner = None
    if args.controller_config is not None:
        from .configuration import configured_runner

        runner = configured_runner(args.controller_config, args.state_dir)
    source_mirror = None
    if args.source_mirror_config is not None:
        from .archive_mirror import configured_source_mirror

        source_mirror = configured_source_mirror(args.source_mirror_config)
    provenance = None
    if (args.provenance_host_id is None) != (args.provenance_project_id is None):
        raise SystemExit("provenance host/project identities must be supplied together")
    provenance_enabled = args.provenance_host_id is not None
    if provenance_enabled:
        if args.provenance_pin is None or args.expected_pin_digest is None:
            raise SystemExit(
                "provenance capture requires --provenance-pin and --expected-pin-digest"
            )
        if not _REVISION.fullmatch(args.source_revision):
            raise SystemExit(
                "source revision must be the exact immutable deployed commit"
            )
    elif args.provenance_pin is not None or args.expected_pin_digest is not None:
        raise SystemExit(
            "provenance pin/digest require provenance host/project identities"
        )
    if provenance_enabled:
        try:
            validated_pin = _validated_monthly_provenance_pin(
                args.repository_root,
                args.provenance_pin,
                args.expected_pin_digest,
            )
        except ImageBuildError as error:
            raise SystemExit(str(error)) from error
        from .provenance import Provenance
        pin = Provenance.capture_pin(
            args.state_dir,
            validated_pin["path"],
            repository=args.source_repository,
            revision=args.source_revision,
            repository_path=validated_pin["repository_path"],
        )
        # Re-read source evidence after capture so a concurrent path/byte change
        # cannot silently replace the lane-bound monthly pin.
        try:
            rechecked = _validated_monthly_provenance_pin(
                args.repository_root,
                args.provenance_pin,
                args.expected_pin_digest,
            )
        except ImageBuildError as error:
            raise SystemExit(str(error)) from error
        if (
            rechecked != validated_pin
            or pin.get("digest") != validated_pin["digest"]
            or pin.get("path") != validated_pin["repository_path"]
            or pin.get("month") != validated_pin["month"]
            or pin.get("repository") != args.source_repository
            or pin.get("revision") != args.source_revision
        ):
            raise SystemExit(
                "captured monthly provenance pin differs from deployed source binding"
            )
        provenance = Provenance(
            args.state_dir,
            host_id=args.provenance_host_id,
            project_id=args.provenance_project_id,
            pin=pin,
        )
    from .engine import ImageBuild

    builder = ImageBuild(
        package_dir=args.package_dir,
        state_dir=args.state_dir,
        runner=runner,
        source_mirror=source_mirror,
        provenance=provenance,
    )
    adapter = RemoteOperations(
        builder,
        repository_root=args.repository_root,
        source_repository=args.source_repository,
        source_revision=args.source_revision,
        observed_state_dir=args.observed_state_dir,
    )
    result = adapter.execute(json.loads(args.request.read_text()))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

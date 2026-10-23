"""Typed unattended toolchain execution over retained image-build workers.

Callers select only a reviewed phase and, for the initial phase, a seed generation.
All filesystem paths, plans, worker modules and subsequent generation/attempt
references are resolved by image-build from its own retained state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import ImageBuildError
from .metadata import names
from .remote_contract import REQUEST_SCHEMA
from .toolchain_contract import (
    REMOTE_EXECUTION_CONTRACT,
    REMOTE_PHASES,
    specification_binding,
)

BINDING_CONTRACT = "image-build-toolchain-remote-binding-v1"
MAX_EVIDENCE = 24
_GENERATION_LENGTH = 64

_PREDECESSORS = {
    "cross-bootstrap": (),
    "temporary-userspace": ("cross-bootstrap",),
    "native-transition": ("temporary-userspace",),
    "native-environment": ("native-transition",),
    "final-libc-build": ("native-environment",),
    "final-libc-publish": ("final-libc-build",),
    "final-libc-recover": ("final-libc-publish",),
    "final-math": ("final-libc-publish", "final-libc-recover"),
    "final-compiler": ("final-math",),
}

_RECORD = {
    "cross-bootstrap": "operation.json",
    "temporary-userspace": "operation.json",
    "native-transition": "operation.json",
    "native-environment": "operation.json",
    "final-libc-build": "operation.json",
    "final-libc-publish": "result.json",
    "final-libc-recover": "result.json",
    "final-math": "result.json",
    "final-compiler": "result.json",
}

_OUTPUT_FIELDS = {
    "cross-bootstrap": ("stages_generation", "runtime_generation"),
    "temporary-userspace": (
        "compiler_generation",
        "packages_generation",
        "runtime_generation",
    ),
    "native-transition": (
        "packages_generation",
        "native_generation",
        "m4_generation",
    ),
    "native-environment": ("generation",),
    "final-libc-build": ("generation",),
    "final-libc-publish": ("generation",),
    "final-libc-recover": ("generation",),
    "final-math": ("generation", "base_generation"),
    "final-compiler": ("generation", "m4_generation", "toolchain_artifact"),
}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _generation(value):
    if (
        not isinstance(value, str)
        or len(value) != _GENERATION_LENGTH
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ImageBuildError("invalid toolchain generation identity")
    return value


class ToolchainRemoteExecutor:
    def __init__(
        self,
        builder,
        *,
        repository_root,
        source_repository,
        source_revision,
        remote_root,
        controller_config=None,
    ):
        self.builder = builder
        self.state = Path(builder.state).resolve()
        self.repository_root = Path(repository_root).resolve()
        self.source_repository = source_repository
        self.source_revision = source_revision
        self.remote_root = Path(remote_root).resolve()
        self.controller_config = (
            None if controller_config is None else Path(controller_config).resolve()
        )

    def _project(self):
        if self.state.name != "state":
            raise ImageBuildError(
                "typed toolchain execution requires a project/state control root"
            )
        return self.state.parent

    def _catalogue(self):
        path = self.repository_root / "project" / "package"
        if path.is_symlink() or not path.is_dir():
            raise ImageBuildError("deployed toolchain catalogue is unavailable")
        return path

    def _controller(self):
        if self.controller_config is None:
            raise ImageBuildError(
                "typed toolchain execution requires server-owned controller configuration"
            )
        if (
            self.controller_config.is_symlink()
            or not self.controller_config.is_file()
        ):
            raise ImageBuildError("controller configuration is unavailable")
        return self.controller_config

    def _plan(self, name):
        allowed = {
            "cross": "lfs-cross.py",
            "temporary": "lfs-temporary.py",
            "final-libc": "lfs-final-start.py",
        }
        if name not in allowed:
            raise ImageBuildError("unknown toolchain plan")
        path = self.repository_root / "project" / "bootstrap" / allowed[name]
        if path.is_symlink() or not path.is_file():
            raise ImageBuildError("reviewed toolchain plan is unavailable")
        return path

    def _generation_path(self, value, *, kinds=None):
        value = _generation(value)
        from .engine import read_selection

        path = self.state / "image-build" / "generations" / value
        selection = read_selection(path)
        if kinds is not None and selection.manifest.get("kind") not in set(kinds):
            raise ImageBuildError(
                "toolchain generation kind differs from phase requirement"
            )
        return path, selection

    def _remote_submission(self, operation_id):
        names([operation_id])
        directory = self.remote_root / operation_id
        try:
            request = json.loads((directory / "request.json").read_text())
            binding = json.loads((directory / "binding.json").read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError(
                "toolchain predecessor operation is unavailable"
            ) from error
        if (
            request.get("schema") != REQUEST_SCHEMA
            or request.get("operation") != "toolchain.submit"
            or request.get("operation_id") != operation_id
            or request.get("source")
            != {
                "repository": self.source_repository,
                "revision": self.source_revision,
            }
        ):
            raise ImageBuildError("toolchain predecessor source binding differs")
        self.validate_binding(request, binding)
        return request, binding

    def _work(self, binding):
        name = binding.get("work_name")
        names([name])
        return self.state / "image-build" / name

    def _record(self, binding):
        path = self._work(binding) / _RECORD[binding["phase"]]
        if not path.exists():
            return path, None
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid retained toolchain phase record") from error
        if not isinstance(record, dict):
            raise ImageBuildError("invalid retained toolchain phase record")
        return path, record

    def _status(self, binding):
        path, record = self._record(binding)
        if record is None:
            return "pending", None, path
        phase = record.get("phase")
        if phase == "complete":
            return "completed", record, path
        if phase == "failed":
            return "failed", record, path
        return "pending", record, path

    def _outputs(self, binding, record=None):
        if record is None:
            _, record = self._record(binding)
        if record is None:
            return {}
        outputs = {}
        for field in _OUTPUT_FIELDS[binding["phase"]]:
            if field not in record:
                continue
            value = record[field]
            if field.endswith("generation"):
                _generation(value)
            outputs[field] = value
        return outputs

    def _pipeline_for_generation(self, generation):
        generation = _generation(generation)
        root = self.state / "image-build" / "pipelines"
        matches = []
        if root.exists():
            for path in root.glob("*/pipeline.json"):
                try:
                    value = json.loads(path.read_text())
                except (OSError, ValueError, TypeError):
                    continue
                if value.get("generation") == generation:
                    matches.append(value)
        if len(matches) != 1:
            raise ImageBuildError(
                "toolchain retained generation has ambiguous or missing pipeline"
            )
        return matches[0]

    def _attempt_for_packages(self, generation, packages):
        pipeline = self._pipeline_for_generation(generation)
        candidates = []
        for attempt_id in sorted(set(pipeline.get("attempts", {}).values())):
            names([attempt_id])
            root = self.state / "image-build" / "attempts" / attempt_id / "packages"
            if all((root / package / "result.json").is_file() for package in packages):
                candidates.append(attempt_id)
        if len(candidates) != 1:
            raise ImageBuildError(
                "toolchain package ownership attempt is ambiguous or unavailable"
            )
        return candidates[0]

    def _predecessor(self, request, phase, *, failed=False):
        allowed = _PREDECESSORS[phase]
        predecessor = request.get("predecessor")
        if not allowed:
            if predecessor is not None:
                raise ImageBuildError(
                    "initial toolchain phase does not accept predecessor"
                )
            return None, None, {}
        if predecessor is None:
            raise ImageBuildError("toolchain phase requires predecessor")
        _, binding = self._remote_submission(predecessor)
        if binding["phase"] not in allowed:
            raise ImageBuildError("toolchain predecessor phase differs")
        status, record, _ = self._status(binding)
        required = "failed" if failed else "completed"
        if status != required:
            raise ImageBuildError(
                "toolchain predecessor must be " + required
            )
        lineage = dict(binding["lineage"])
        lineage[binding["phase"]] = predecessor
        return binding, record, lineage

    def _lineage_submission(self, lineage, phase):
        operation_id = lineage.get(phase)
        if not operation_id:
            raise ImageBuildError("toolchain lineage is missing " + phase)
        _, binding = self._remote_submission(operation_id)
        status, record, _ = self._status(binding)
        if status != "completed":
            raise ImageBuildError("toolchain lineage phase is not complete")
        return binding, record

    def prepare(self, request):
        arguments = request["arguments"]
        if (
            not isinstance(arguments, dict)
            or "phase" not in arguments
            or arguments["phase"] not in REMOTE_PHASES
        ):
            raise ImageBuildError("unknown typed toolchain phase")
        phase = arguments["phase"]
        if phase == "cross-bootstrap":
            if set(arguments) != {"phase", "seed_generation"}:
                raise ImageBuildError(
                    "cross-bootstrap accepts only phase and seed_generation"
                )
            seed = _generation(arguments["seed_generation"])
            self._generation_path(seed, kinds={"host-bootstrap"})
            predecessor = None
            lineage = {}
            inputs = {"seed_generation": seed}
        else:
            if set(arguments) != {"phase"}:
                raise ImageBuildError(
                    "subsequent toolchain phases accept only phase"
                )
            predecessor_binding, predecessor_record, lineage = self._predecessor(
                request,
                phase,
                failed=(phase == "final-libc-recover"),
            )
            predecessor = request["predecessor"]
            previous = self._outputs(
                predecessor_binding, predecessor_record
            )
            if phase == "temporary-userspace":
                inputs = {
                    "seed_generation": predecessor_binding["inputs"][
                        "seed_generation"
                    ],
                    "cross_generation": previous["stages_generation"],
                }
            elif phase == "native-transition":
                packages_generation = previous["packages_generation"]
                inputs = {
                    "compiler_generation": previous["compiler_generation"],
                    "runtime_generation": previous["runtime_generation"],
                    "prior_attempt_id": self._attempt_for_packages(
                        packages_generation,
                        (
                            "gcc-temporary-libstdcpp",
                            "ncurses-temporary",
                            "bash-temporary",
                        ),
                    ),
                }
            elif phase == "native-environment":
                inputs = {
                    "selection_generation": previous["native_generation"]
                }
            elif phase == "final-libc-build":
                inputs = {
                    "selection_generation": previous["generation"]
                }
            elif phase == "final-libc-publish":
                build_generation = previous["generation"]
                build_attempt = self._attempt_for_packages(
                    build_generation, ("glibc-final",)
                )
                cross_binding, cross_record = self._lineage_submission(
                    lineage, "cross-bootstrap"
                )
                cross_outputs = self._outputs(cross_binding, cross_record)
                old_attempt = self._attempt_for_packages(
                    cross_outputs["stages_generation"],
                    ("glibc-cross-initial",),
                )
                inputs = {
                    "base_generation": predecessor_binding["inputs"][
                        "selection_generation"
                    ],
                    "build_generation": build_generation,
                    "build_attempt_id": build_attempt,
                    "previous_package_attempt_id": old_attempt,
                }
            elif phase == "final-libc-recover":
                inputs = {
                    "previous_operation_id": predecessor,
                    "source_attempt_id": predecessor_binding["inputs"][
                        "build_attempt_id"
                    ],
                }
            elif phase == "final-math":
                inputs = {
                    "selection_generation": previous["generation"]
                }
            else:
                native_binding, native_record = self._lineage_submission(
                    lineage, "native-transition"
                )
                native_outputs = self._outputs(native_binding, native_record)
                ownership_attempt = self._attempt_for_packages(
                    native_outputs["packages_generation"],
                    (
                        "binutils-native-temporary",
                        "gcc-native-temporary",
                    ),
                )
                inputs = {
                    "selection_generation": previous["base_generation"],
                    "arithmetic_generation": previous["generation"],
                    "ownership_attempt_id": ownership_attempt,
                }
        work_name = "toolchain-" + request["operation_id"] + "-" + phase
        names([work_name])
        binding = {
            "contract": BINDING_CONTRACT,
            "execution_contract": REMOTE_EXECUTION_CONTRACT,
            "specification": specification_binding(),
            "operation_id": request["operation_id"],
            "source": dict(request["source"]),
            "phase": phase,
            "predecessor": predecessor,
            "lineage": lineage,
            "inputs": inputs,
            "work_name": work_name,
        }
        from .metadata import identity
        binding["identity"] = "sha256:" + identity(binding)
        return binding

    def validate_binding(self, request, binding):
        if not isinstance(binding, dict):
            raise ImageBuildError("invalid toolchain remote binding")
        required = {
            "contract",
            "execution_contract",
            "specification",
            "operation_id",
            "source",
            "phase",
            "predecessor",
            "lineage",
            "inputs",
            "work_name",
            "identity",
        }
        if set(binding) != required:
            raise ImageBuildError("invalid toolchain remote binding fields")
        from .metadata import identity
        payload = {key: value for key, value in binding.items() if key != "identity"}
        if binding.get("identity") != "sha256:" + identity(payload):
            raise ImageBuildError("toolchain remote binding identity changed")
        if (
            binding["contract"] != BINDING_CONTRACT
            or binding["execution_contract"] != REMOTE_EXECUTION_CONTRACT
            or binding["specification"] != specification_binding()
            or binding["operation_id"] != request["operation_id"]
            or binding["source"] != request["source"]
            or binding["phase"] != request["arguments"].get("phase")
            or binding["predecessor"] != request.get("predecessor")
        ):
            raise ImageBuildError("toolchain remote binding changed")
        names([binding["work_name"]])
        if not isinstance(binding["lineage"], dict) or not isinstance(
            binding["inputs"], dict
        ):
            raise ImageBuildError("invalid toolchain remote binding data")
        return binding

    def execute(self, binding):
        phase = binding["phase"]
        inputs = binding["inputs"]
        work = self._work(binding)
        project = self._project()
        catalogue = self._catalogue()
        controller = self._controller()
        generation_root = self.state / "image-build" / "generations"
        attempts = self.state / "image-build" / "attempts"

        if phase == "cross-bootstrap":
            from . import stages
            return stages.run(
                project,
                catalogue,
                self._plan("cross"),
                controller,
                generation_root / inputs["seed_generation"],
                operation_name=binding["work_name"],
            )
        if phase == "temporary-userspace":
            from . import temporary
            return temporary.run(
                project,
                catalogue,
                self._plan("temporary"),
                controller,
                generation_root / inputs["seed_generation"],
                generation_root / inputs["cross_generation"],
                operation_name=binding["work_name"],
            )
        if phase == "native-transition":
            from . import native
            return native.run(
                project,
                catalogue,
                controller,
                {
                    "compiler": generation_root
                    / inputs["compiler_generation"],
                    "runtime": generation_root / inputs["runtime_generation"],
                    "prior_attempt": attempts / inputs["prior_attempt_id"],
                },
                operation_name=binding["work_name"],
            )
        if phase == "native-environment":
            from . import build_environment
            return build_environment.run(
                project,
                catalogue,
                controller,
                generation_root / inputs["selection_generation"],
                operation_name=binding["work_name"],
            )
        if phase == "final-libc-build":
            from . import native_stage
            return native_stage.run(
                project=project,
                catalogue=catalogue,
                plan=self._plan("final-libc"),
                controller=controller,
                selection=generation_root / inputs["selection_generation"],
                work=work,
            )
        if phase == "final-libc-publish":
            from . import glibc_final
            return glibc_final.run(
                project,
                attempts / inputs["build_attempt_id"],
                inputs["base_generation"],
                attempts
                / inputs["previous_package_attempt_id"]
                / "packages"
                / "glibc-cross-initial"
                / "result.json",
                work,
            )
        if phase == "final-libc-recover":
            from . import glibc_publish
            previous_request, previous_binding = self._remote_submission(
                inputs["previous_operation_id"]
            )
            del previous_request
            source_controller = (
                attempts / inputs["source_attempt_id"] / "controller.json"
            )
            if not source_controller.is_file() or source_controller.is_symlink():
                raise ImageBuildError(
                    "retained final-libc controller configuration is unavailable"
                )
            return glibc_publish.run(
                project,
                self._work(previous_binding),
                work,
                source_controller,
            )
        if phase == "final-math":
            from . import final_math
            return final_math.run(
                project,
                catalogue,
                controller,
                generation_root / inputs["selection_generation"],
                work,
            )
        from . import final_compiler
        return final_compiler.run(
            project,
            catalogue,
            controller,
            generation_root / inputs["selection_generation"],
            generation_root / inputs["arithmetic_generation"],
            attempts / inputs["ownership_attempt_id"] / "packages",
            work,
        )

    def _pipeline_item(self, pipeline):
        pipeline_id = pipeline.get("pipeline_id")
        if (
            not isinstance(pipeline_id, str)
            or len(pipeline_id) != 32
            or any(c not in "0123456789abcdef" for c in pipeline_id)
        ):
            raise ImageBuildError("invalid retained toolchain pipeline identity")
        attempts = pipeline.get("attempts")
        if not isinstance(attempts, dict):
            raise ImageBuildError("invalid retained toolchain pipeline attempts")
        attempt_ids = list(attempts.values())
        if len(set(attempt_ids)) != len(attempt_ids):
            raise ImageBuildError("ambiguous retained toolchain pipeline attempts")
        for attempt_id in attempt_ids:
            names([attempt_id])
        return {
            "pipeline_id": pipeline_id,
            "status": pipeline.get("status"),
            "attempt_ids": sorted(attempt_ids)[:MAX_EVIDENCE],
        }

    def _pipeline_evidence(self, generation):
        try:
            pipeline = self._pipeline_for_generation(generation)
        except ImageBuildError:
            return None
        return self._pipeline_item(pipeline)

    def _bound_pipeline(self, binding, record):
        if not isinstance(record, dict) or "pipeline_id" not in record:
            return None
        if binding["phase"] != "cross-bootstrap":
            raise ImageBuildError(
                "retained toolchain phase has an unexpected pipeline association"
            )
        pipeline_id = record["pipeline_id"]
        try:
            pipeline = self.builder.inspect_pipeline(pipeline_id)
        except (OSError, ValueError, TypeError, ImageBuildError) as error:
            raise ImageBuildError(
                "retained toolchain pipeline association is unavailable"
            ) from error
        intent = record.get("intent")
        expected_owner = {
            "contract": "image-build-toolchain-phase-pipeline-v1",
            "work_name": binding["work_name"],
        }
        selection = (
            self.state
            / "image-build"
            / "generations"
            / binding["inputs"]["seed_generation"]
        ).resolve()
        if (
            not isinstance(intent, dict)
            or intent.get("seed") != binding["inputs"]["seed_generation"]
            or not isinstance(intent.get("plan"), dict)
            or pipeline.get("pipeline_id") != pipeline_id
            or pipeline.get("operation") != "seed-check"
            or pipeline.get("selection") != str(selection)
            or pipeline.get("arguments")
            != {"targets": intent["plan"].get("targets")}
            or pipeline.get("recipes") != intent.get("recipes")
            or pipeline.get("policy") != intent.get("policy")
            or pipeline.get("owner") not in (None, expected_owner)
        ):
            raise ImageBuildError(
                "retained toolchain pipeline association differs"
            )
        self._pipeline_item(pipeline)
        for attempt_id in pipeline["attempts"].values():
            status_path = (
                self.state
                / "image-build"
                / "attempts"
                / attempt_id
                / "status.json"
            )
            try:
                attempt = json.loads(status_path.read_text())
            except (OSError, ValueError, TypeError) as error:
                raise ImageBuildError(
                    "retained toolchain attempt association is unavailable"
                ) from error
            if attempt.get("pipeline_id") != pipeline_id:
                raise ImageBuildError(
                    "retained toolchain attempt association differs"
                )
        return pipeline

    def _controller_evidence(self, binding, outputs, bound_pipeline=None):
        roots = [self._work(binding)]
        pipelines = []
        if bound_pipeline is not None:
            pipelines.append(bound_pipeline)
        for value in outputs.values():
            if not isinstance(value, str) or len(value) != _GENERATION_LENGTH:
                continue
            try:
                pipeline = self._pipeline_for_generation(value)
            except ImageBuildError:
                continue
            if all(
                item.get("pipeline_id") != pipeline.get("pipeline_id")
                for item in pipelines
            ):
                pipelines.append(pipeline)
        for pipeline in pipelines:
            for attempt_id in set(pipeline.get("attempts", {}).values()):
                roots.append(
                    self.state / "image-build" / "attempts" / attempt_id
                )
        seen = set()
        result = []
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.controller.json")):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                try:
                    value = json.loads(path.read_text())
                except (OSError, ValueError, TypeError) as error:
                    raise ImageBuildError(
                        "invalid retained controller checkpoint"
                    ) from error
                if not isinstance(value, dict):
                    raise ImageBuildError(
                        "invalid retained controller checkpoint"
                    )
                item = {
                    k: value.get(k)
                    for k in (
                        "request_id",
                        "job_id",
                        "resource_id",
                    )
                    if k in value
                }
                observation = path.with_name(
                    path.name.removesuffix(".controller.json")
                    + ".observation.json"
                )
                if observation.exists():
                    try:
                        observed = json.loads(observation.read_text())
                    except (OSError, ValueError, TypeError) as error:
                        raise ImageBuildError(
                            "invalid retained controller observation"
                        ) from error
                    if (
                        not isinstance(observed, dict)
                        or observed.get("request_id") != value.get("request_id")
                        or observed.get("job_id") != value.get("job_id")
                    ):
                        raise ImageBuildError(
                            "retained controller observation identity differs"
                        )
                    for name in (
                        "state",
                        "outcome",
                        "exit_code",
                        "runtime_id",
                        "invocation_id",
                        "boot_id",
                        "unit_name",
                        "journal_reference",
                        "process_cleanup_complete",
                        "resources_released",
                        "cancel_requested",
                        "completed_at",
                    ):
                        if name in observed:
                            item[name] = observed[name]
                    try:
                        item["observation_locator"] = str(
                            observation.relative_to(self.state)
                        )
                    except ValueError:
                        raise ImageBuildError(
                            "retained controller observation escaped state"
                        )
                try:
                    item["locator"] = str(path.relative_to(self.state))
                except ValueError as error:
                    raise ImageBuildError(
                        "retained controller checkpoint escaped state"
                    ) from error
                result.append(item)
                if len(result) >= MAX_EVIDENCE:
                    return result
        return result

    def observe(self, binding):
        status, record, path = self._status(binding)
        outputs = self._outputs(binding, record)
        selected = None
        for key in (
            "generation",
            "runtime_generation",
            "native_generation",
            "stages_generation",
        ):
            if key in outputs:
                selected = outputs[key]
                break
        bound_pipeline = self._bound_pipeline(binding, record)
        artifact = {
            "contract": REMOTE_EXECUTION_CONTRACT,
            "phase": binding["phase"],
            "operation_id": binding["operation_id"],
            "specification": binding["specification"],
            "predecessor": binding["predecessor"],
            "lineage": dict(binding["lineage"]),
            "inputs": dict(binding["inputs"]),
            "outputs": outputs,
            "work_record": None,
            "pipelines": [],
            "controller_jobs": self._controller_evidence(
                binding, outputs, bound_pipeline
            ),
        }
        if bound_pipeline is not None:
            artifact["pipelines"].append(
                self._pipeline_item(bound_pipeline)
            )
        if path.exists():
            artifact["work_record"] = {
                "locator": str(path.relative_to(self.state)),
                "sha256": "sha256:" + _sha256(path),
            }
        for value in outputs.values():
            if isinstance(value, str) and len(value) == _GENERATION_LENGTH:
                evidence = self._pipeline_evidence(value)
                if evidence is not None and evidence not in artifact["pipelines"]:
                    artifact["pipelines"].append(evidence)
        artifact["pipelines"] = artifact["pipelines"][:MAX_EVIDENCE]
        failure = None
        if status == "failed":
            failure = {
                "type": "toolchain-phase-failed",
                "reason": str(record.get("error", "retained worker failure"))[
                    :4096
                ],
            }
        return {
            "status": status,
            "terminal_outcome": (
                "success"
                if status == "completed"
                else ("failure" if status == "failed" else None)
            ),
            "failure": failure,
            "selected_generation": selected,
            "artifact": artifact,
        }

"""Read-only integrity/reference report for immutable image-build objects.

This module is deliberately not a reclamation executor.  It verifies published
objects and reports local references/protections so another owner can combine them
with runtime/history policy before deciding whether anything may be removed.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re

from .application_software import read_artifact
from .application_views import read_view
from .engine import read_selection
from .errors import ImageBuildError
from .metadata import identity
from .recipe_snapshots import _read_snapshot

SCHEMA = 1
CONTRACT = "image-build-immutable-object-report-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_KINDS = (
    "generation",
    "recipe-snapshot",
    "application-view",
    "application-artifact",
)
_ACTIVE_PIPELINE = {"prepared", "running", "pending"}


def _copy(value):
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )


def _digest(value):
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha_id(value):
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and _SHA256.fullmatch(value[7:]) is not None
    )


def _generation_id(value):
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


@contextmanager
def _read_lock(state):
    """Share the existing image-build lock without creating read-side state."""
    lock = Path(state) / "image-build.lock"
    if not lock.exists():
        yield
        return
    if lock.is_symlink() or not lock.is_file():
        raise ImageBuildError("invalid image-build lock for immutable object report")
    with lock.open("r") as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class _ArtifactReader:
    def __init__(self, root):
        self.root = Path(root)

    def resolve(self, artifact):
        if not _sha_id(artifact):
            raise ImageBuildError(
                "invalid application artifact reference"
            )
        return read_artifact(
            self.root / "artifacts" / artifact[7:]
        )


class _Report:
    def __init__(self, state):
        self.state = Path(state).resolve()
        self.image = self.state / "image-build"
        self.objects = {}
        self.edges = []
        self.faults = []
        self.reference_complete = True
        self.integrity_complete = True

    def fault(self, scope, identity_value, error, *, reference=False):
        value = {
            "scope": scope,
            "identity": str(identity_value),
            "error_type": type(error).__name__,
            "reason": str(error),
        }
        self.faults.append(value)
        if reference:
            self.reference_complete = False
        else:
            self.integrity_complete = False

    def object(self, kind, object_id, *, metadata=None, error=None):
        key = (kind, object_id)
        value = {
            "kind": kind,
            "id": object_id,
            "integrity": "valid" if error is None else "fault",
            "metadata": _copy(metadata or {}),
            "protected_by": [],
            "referenced_by": [],
        }
        if error is not None:
            value["fault"] = {
                "error_type": type(error).__name__,
                "reason": str(error),
            }
            self.integrity_complete = False
        self.objects[key] = value

    def edge(
        self,
        *,
        source_kind,
        source_id,
        relation,
        target_kind,
        target_id,
        protects,
    ):
        if target_kind not in _KINDS:
            raise ImageBuildError("unknown immutable object reference kind")
        edge = {
            "source_kind": source_kind,
            "source_id": str(source_id),
            "relation": relation,
            "target_kind": target_kind,
            "target_id": target_id,
            "protects": bool(protects),
        }
        self.edges.append(edge)

    def _published_directories(self, root, kind):
        if not root.exists():
            return []
        if root.is_symlink() or not root.is_dir():
            self.fault(kind + "-store", root.name, ImageBuildError("invalid published object store"))
            return []
        values = []
        for path in sorted(root.iterdir(), key=lambda value: value.name):
            if path.is_dir() and not path.is_symlink() and _SHA256.fullmatch(path.name):
                values.append(path)
            else:
                self.fault(
                    kind + "-store-entry",
                    path.name,
                    ImageBuildError("invalid published immutable object entry"),
                )
        return values

    def scan_objects(self):
        generations = self.image / "generations"
        for path in self._published_directories(generations, "generation"):
            try:
                value = read_selection(path)
                self.object(
                    "generation",
                    value.generation,
                    metadata={"kind": value.manifest["kind"]},
                )
            except Exception as error:
                self.object("generation", path.name, error=error)

        snapshots_root = self.image / "recipe-snapshots"
        for path in self._published_directories(
            snapshots_root / "snapshots", "recipe-snapshot"
        ):
            snapshot_id = "sha256:" + path.name
            try:
                value = _read_snapshot(snapshots_root, snapshot_id)
                self.object(
                    "recipe-snapshot",
                    snapshot_id,
                    metadata={
                        "source": value.manifest["source"],
                        "pin_date": value.manifest["pin_date"],
                    },
                )
            except Exception as error:
                self.object("recipe-snapshot", snapshot_id, error=error)

        software = self.image / "application-software"
        artifacts_root = software / "artifacts"
        for path in self._published_directories(
            artifacts_root, "application-artifact"
        ):
            artifact_id = "sha256:" + path.name
            try:
                value = read_artifact(path)
                self.object(
                    "application-artifact",
                    artifact_id,
                    metadata={"application": value.manifest["application"]},
                )
            except Exception as error:
                self.object("application-artifact", artifact_id, error=error)

        reader = _ArtifactReader(software)
        for path in self._published_directories(
            software / "views", "application-view"
        ):
            view_id = "sha256:" + path.name
            try:
                value = read_view(reader, path)
                self.object(
                    "application-view",
                    view_id,
                    metadata={
                        "application": value.manifest["application"],
                        "profile": value.manifest["profile"],
                    },
                )
                for artifact in value.manifest["artifacts"]:
                    self.edge(
                        source_kind="application-view",
                        source_id=view_id,
                        relation="composes",
                        target_kind="application-artifact",
                        target_id=artifact,
                        protects=True,
                    )
            except Exception as error:
                self.object("application-view", view_id, error=error)
                # A corrupt view cannot be trusted for reclamation.  Recover
                # syntactically valid artifact IDs only to over-protect them.
                try:
                    manifest = json.loads((path / "manifest.json").read_text())
                    artifacts = manifest.get("artifacts", [])
                    if not isinstance(artifacts, list):
                        raise ValueError("view artifact list is invalid")
                    for artifact in artifacts:
                        if _sha_id(artifact):
                            self.edge(
                                source_kind="application-view-fault",
                                source_id=view_id,
                                relation="possibly-composes",
                                target_kind="application-artifact",
                                target_id=artifact,
                                protects=True,
                            )
                except Exception as reference_error:
                    self.fault(
                        "application-view-reference",
                        view_id,
                        reference_error,
                        reference=True,
                    )

    def _selection(self, name):
        path = self.image / name
        if not path.exists() and not path.is_symlink():
            return
        try:
            if not path.is_symlink():
                raise ImageBuildError("generation selection is not a symlink")
            target = path.resolve(strict=True)
            generation_root = (self.image / "generations").resolve()
            target.relative_to(generation_root)
            generation = target.name
            if not _generation_id(generation):
                raise ImageBuildError("generation selection target is invalid")
            self.edge(
                source_kind="selection",
                source_id=name,
                relation="selects",
                target_kind="generation",
                target_id=generation,
                protects=True,
            )
        except Exception as error:
            self.fault("selection", name, error, reference=True)

    def _pipeline_generation(self, value):
        try:
            path = Path(value).resolve()
            root = (self.image / "generations").resolve()
            path.relative_to(root)
            generation = path.name
            if not _generation_id(generation):
                raise ValueError
            return generation
        except Exception as error:
            raise ImageBuildError(
                "pipeline selection is outside the generation store"
            ) from error

    def scan_pipelines(self):
        root = self.image / "pipelines"
        if not root.exists():
            return
        if root.is_symlink() or not root.is_dir():
            self.fault("pipeline-store", root.name, ImageBuildError("invalid pipeline store"), reference=True)
            return
        for directory in sorted(root.iterdir(), key=lambda value: value.name):
            path = directory / "pipeline.json"
            try:
                record = json.loads(path.read_text())
                if (
                    not isinstance(record, dict)
                    or record.get("schema") != 1
                    or record.get("pipeline_id") != directory.name
                    or not isinstance(record.get("status"), str)
                ):
                    raise ImageBuildError("invalid pipeline reference record")
                active = record["status"] in _ACTIVE_PIPELINE
                generation = self._pipeline_generation(record["selection"])
                self.edge(
                    source_kind="pipeline",
                    source_id=directory.name,
                    relation="input-generation",
                    target_kind="generation",
                    target_id=generation,
                    protects=active,
                )
                output = record.get("generation")
                if output is not None:
                    if not _generation_id(output):
                        raise ImageBuildError("invalid pipeline output generation")
                    self.edge(
                        source_kind="pipeline",
                        source_id=directory.name,
                        relation="output-generation",
                        target_kind="generation",
                        target_id=output,
                        protects=False,
                    )
                owner = record.get("owner")
                if isinstance(owner, dict) and "recipe_snapshot" in owner:
                    snapshot = owner["recipe_snapshot"]
                    if not _sha_id(snapshot):
                        raise ImageBuildError("invalid pipeline recipe snapshot reference")
                    self.edge(
                        source_kind="pipeline",
                        source_id=directory.name,
                        relation="recipe-snapshot",
                        target_kind="recipe-snapshot",
                        target_id=snapshot,
                        protects=active,
                    )
            except Exception as error:
                self.fault("pipeline", directory.name, error, reference=True)

    def _remote_reference(self, operation_id, request, protects):
        arguments = request.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ImageBuildError("remote operation arguments are not an object")
        selection = arguments.get("selection")
        if selection is not None:
            if not _generation_id(selection):
                raise ImageBuildError("invalid remote selection generation")
            self.edge(
                source_kind="remote-operation",
                source_id=operation_id,
                relation="selection-generation",
                target_kind="generation",
                target_id=selection,
                protects=protects,
            )
        generation = arguments.get("generation")
        if generation is not None:
            if not _generation_id(generation):
                raise ImageBuildError("invalid remote generation reference")
            self.edge(
                source_kind="remote-operation",
                source_id=operation_id,
                relation="generation",
                target_kind="generation",
                target_id=generation,
                protects=protects,
            )
        snapshot = arguments.get("recipe_snapshot")
        if snapshot is not None:
            if not _sha_id(snapshot):
                raise ImageBuildError("invalid remote recipe snapshot reference")
            self.edge(
                source_kind="remote-operation",
                source_id=operation_id,
                relation="recipe-snapshot",
                target_kind="recipe-snapshot",
                target_id=snapshot,
                protects=protects,
            )

    def scan_remote_operations(self):
        root = self.image / "remote-operations"
        if not root.exists():
            return
        if root.is_symlink() or not root.is_dir():
            self.fault("remote-operation-store", root.name, ImageBuildError("invalid remote operation store"), reference=True)
            return
        for directory in sorted(root.iterdir(), key=lambda value: value.name):
            try:
                request = json.loads((directory / "request.json").read_text())
                result_path = directory / "result.json"
                complete = result_path.is_file() and not result_path.is_symlink()
                if result_path.exists() and not complete:
                    raise ImageBuildError("invalid remote operation result")
                if complete:
                    json.loads(result_path.read_text())
                self._remote_reference(directory.name, request, not complete)
                binding = directory / "binding.json"
                if binding.exists():
                    if binding.is_symlink() or not binding.is_file():
                        raise ImageBuildError("invalid remote operation binding")
                    value = json.loads(binding.read_text())
                    snapshot = value.get("recipe_snapshot") if isinstance(value, dict) else None
                    if snapshot is not None:
                        if not _sha_id(snapshot):
                            raise ImageBuildError("invalid remote binding recipe snapshot")
                        self.edge(
                            source_kind="remote-operation-binding",
                            source_id=directory.name,
                            relation="recipe-snapshot",
                            target_kind="recipe-snapshot",
                            target_id=snapshot,
                            protects=not complete,
                        )
            except Exception as error:
                self.fault("remote-operation", directory.name, error, reference=True)

    def _application_operation(
        self, directory, *, result_key, kind, frozen_key=None
    ):
        try:
            result_path = directory / "result.json"
            if result_path.exists():
                if result_path.is_symlink() or not result_path.is_file():
                    raise ImageBuildError("invalid application publication result")
                value = json.loads(result_path.read_text())
                object_id = value[result_key]
                if not _sha_id(object_id):
                    raise ImageBuildError("invalid application publication object identity")
                self.edge(
                    source_kind="application-operation",
                    source_id=directory.name,
                    relation="published",
                    target_kind=kind,
                    target_id=object_id,
                    protects=False,
                )
                return
            frozen = directory / "frozen.json"
            if frozen.exists():
                if frozen.is_symlink() or not frozen.is_file():
                    raise ImageBuildError("invalid frozen application publication")
                value = json.loads(frozen.read_text())
                if frozen_key is None:
                    object_id = value[result_key]
                else:
                    object_id = value[frozen_key][result_key]
                if not _sha_id(object_id):
                    raise ImageBuildError("invalid frozen application object identity")
                self.edge(
                    source_kind="application-operation",
                    source_id=directory.name,
                    relation="pending-publication",
                    target_kind=kind,
                    target_id=object_id,
                    protects=True,
                )
        except Exception as error:
            self.fault(
                "application-operation",
                directory.name,
                error,
                reference=True,
            )

    def scan_application_operations(self):
        root = self.image / "application-software"
        operations = root / "operations"
        if operations.exists():
            if operations.is_symlink() or not operations.is_dir():
                self.fault("application-operation-store", operations.name, ImageBuildError("invalid application operation store"), reference=True)
            else:
                for directory in sorted(operations.iterdir(), key=lambda value: value.name):
                    self._application_operation(
                        directory,
                        result_key="artifact",
                        kind="application-artifact",
                    )
        views = root / "view-operations"
        if views.exists():
            if views.is_symlink() or not views.is_dir():
                self.fault("application-view-operation-store", views.name, ImageBuildError("invalid application view operation store"), reference=True)
            else:
                for directory in sorted(views.iterdir(), key=lambda value: value.name):
                    self._application_operation(
                        directory,
                        result_key="view",
                        kind="application-view",
                        frozen_key="manifest",
                    )
                    result = directory / "result.json"
                    if not result.exists():
                        frozen = directory / "frozen.json"
                        try:
                            if frozen.exists():
                                value = json.loads(frozen.read_text())
                                artifacts = value["manifest"]["artifacts"]
                                if not isinstance(artifacts, list):
                                    raise ImageBuildError("invalid frozen view artifacts")
                                for artifact in artifacts:
                                    if not _sha_id(artifact):
                                        raise ImageBuildError("invalid frozen view artifact")
                                    self.edge(
                                        source_kind="application-view-operation",
                                        source_id=directory.name,
                                        relation="pending-artifact",
                                        target_kind="application-artifact",
                                        target_id=artifact,
                                        protects=True,
                                    )
                        except Exception as error:
                            self.fault(
                                "application-view-operation",
                                directory.name,
                                error,
                                reference=True,
                            )

    def finalize(self):
        by_target = {}
        for edge in sorted(
            self.edges,
            key=lambda value: (
                value["target_kind"],
                value["target_id"],
                value["source_kind"],
                value["source_id"],
                value["relation"],
                value["protects"],
            ),
        ):
            by_target.setdefault(
                (edge["target_kind"], edge["target_id"]), []
            ).append(edge)
            if (edge["target_kind"], edge["target_id"]) not in self.objects:
                self.reference_complete = False
                self.faults.append(
                    {
                        "scope": "missing-referenced-object",
                        "identity": (
                            edge["target_kind"] + ":" + edge["target_id"]
                        ),
                        "error_type": "ImageBuildError",
                        "reason": "reference targets an unavailable immutable object",
                    }
                )

        for key, value in self.objects.items():
            references = by_target.get(key, [])
            protected = [edge for edge in references if edge["protects"]]
            value["referenced_by"] = [
                {
                    "source_kind": edge["source_kind"],
                    "source_id": edge["source_id"],
                    "relation": edge["relation"],
                }
                for edge in references
            ]
            value["protected_by"] = [
                {
                    "source_kind": edge["source_kind"],
                    "source_id": edge["source_id"],
                    "relation": edge["relation"],
                }
                for edge in protected
            ]
            if value["integrity"] != "valid":
                value["classification"] = "integrity-fault"
                value["reclamation"] = "blocked-integrity-fault"
            elif protected:
                value["classification"] = "protected"
                value["reclamation"] = "blocked-local-protection"
            elif not self.reference_complete:
                value["classification"] = "unknown"
                value["reclamation"] = "blocked-reference-incomplete"
            elif references:
                value["classification"] = "referenced"
                value["reclamation"] = "requires-owner-policy"
            else:
                value["classification"] = "apparently-unreferenced"
                value["reclamation"] = "requires-owner-policy"

        object_values = sorted(
            self.objects.values(),
            key=lambda value: (value["kind"], value["id"]),
        )
        edges = sorted(
            self.edges,
            key=lambda value: (
                value["target_kind"],
                value["target_id"],
                value["source_kind"],
                value["source_id"],
                value["relation"],
                value["protects"],
            ),
        )
        faults = sorted(
            self.faults,
            key=lambda value: (
                value["scope"],
                value["identity"],
                value["error_type"],
                value["reason"],
            ),
        )

        def grouped(predicate):
            return {
                kind: [
                    value["id"]
                    for value in object_values
                    if value["kind"] == kind and predicate(value)
                ]
                for kind in _KINDS
            }

        report = {
            "schema": SCHEMA,
            "contract": CONTRACT,
            "reference_complete": self.reference_complete,
            "integrity_complete": self.integrity_complete,
            "reclamation_authorized": False,
            "objects": object_values,
            "edges": edges,
            "faults": faults,
            "protection_set": grouped(
                lambda value: value["classification"] == "protected"
            ),
            "apparent_candidates": grouped(
                lambda value: value["classification"]
                == "apparently-unreferenced"
            ),
        }
        report["report_digest"] = _digest(report)
        return report


def report(state_dir):
    state = Path(state_dir)
    if not state.is_absolute():
        state = state.resolve()
    if state.is_symlink() or not state.is_dir():
        raise ImageBuildError(
            "immutable object report requires an existing real state directory"
        )
    value = _Report(state)
    with _read_lock(state):
        value.scan_objects()
        value._selection("active")
        value._selection("toolchain-active")
        value.scan_pipelines()
        value.scan_remote_operations()
        value.scan_application_operations()
        return value.finalize()


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.state_dir), sort_keys=True))


if __name__ == "__main__":
    main()

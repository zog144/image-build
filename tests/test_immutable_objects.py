import ast
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from zog.image_build import ImageBuild
from zog.image_build.application_software import (
    ApplicationSoftwareStore,
    MOUNT_CONTRACT,
)
from zog.image_build.application_views import ApplicationSoftwareViewStore
from zog.image_build.immutable_objects import (
    CONTRACT,
    report,
)
from zog.image_build.recipe_snapshots import RecipeSnapshotStore


def _compatibility():
    return {
        "schema": 1,
        "mount_contract": MOUNT_CONTRACT,
        "architecture": "x86_64",
        "python": None,
        "libraries": [],
    }


def _application_artifact(store, operation, text):
    prepared = store.begin(
        operation,
        application="station-access",
        revision="git:" + operation[-1] * 40,
        sources=[],
        compatibility_requirements=_compatibility(),
        notices=(),
        provenance={},
    )
    (prepared.root / "bin").mkdir()
    (prepared.root / "bin/tool").write_text(text)
    return store.finalize(operation)


def _recipe_catalogue(root):
    catalogue = root / "project/package"
    package = catalogue / "fixture"
    package.mkdir(parents=True)
    payload = package / "payload.txt"
    payload.write_text("fixture")
    source = {
        "url": payload.resolve().as_uri(),
        "sha256": hashlib.sha256(b"fixture").hexdigest(),
        "destination": "payload.txt",
        "archive": False,
    }
    (package / "sources.py").write_text(repr([source]))
    (package / "dependencies.py").write_text(
        repr({"build": [], "runtime": [], "test": []})
    )
    (package / "build.py").write_text(
        repr({"build": [["true"]], "install": [["true"]]})
    )
    (package / "produce-manifest.py").write_text(repr(["usr/share/fixture"]))
    (package / "license.py").write_text(
        repr(
            {
                "schema": 1,
                "package": "fixture",
                "version": "fixture",
                "source": {
                    "url": source["url"],
                    "sha256": source["sha256"],
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
    (catalogue / "commit-pin.py").write_text(
        repr(
            {
                "schema": 1,
                "date": "2026-10-01",
                "packages": {"fixture": {"sources": [source]}},
            }
        )
    )
    monthly = root / "project/pins/2026-10-01/commit-pin.py"
    monthly.parent.mkdir(parents=True)
    monthly.write_text(
        repr(
            {
                "schema": 1,
                "date": "2026-10-01",
                "packages": {
                    "fixture": {
                        "recipes": {"fixture": [source]}
                    }
                },
            }
        )
    )
    return catalogue


def _snapshot(state, repository):
    catalogue = _recipe_catalogue(repository)
    store = RecipeSnapshotStore(state, catalogue)
    return store.prepare(
        "snapshot-fixture",
        entries=[
            {
                "id": "fixture",
                "project": "fixture",
                "recipe": "fixture",
            }
        ],
        pin_date="2026-10-01",
        source_repository="zog144/image-build",
        source_revision="a" * 40,
    )


def _builder(state, tmp_path):
    packages = tmp_path / "empty-packages"
    packages.mkdir(exist_ok=True)
    return ImageBuild(
        package_dir=packages,
        state_dir=state,
        runner=object(),
    )


def _generation(builder, root, label):
    path = root / label
    path.mkdir()
    (path / "payload").write_text(label)
    return builder.import_bootstrap(path, {"fixture": label})


def _object(result, kind, object_id):
    return next(
        value
        for value in result["objects"]
        if value["kind"] == kind and value["id"] == object_id
    )


def _fingerprint(root):
    values = []
    for path in sorted(Path(root).rglob("*")):
        stat = path.lstat()
        if path.is_symlink():
            payload = ("symlink", os.readlink(path))
        elif path.is_file():
            payload = (
                "file",
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        elif path.is_dir():
            payload = ("directory", None)
        else:
            payload = ("other", None)
        values.append(
            (
                path.relative_to(root).as_posix(),
                stat.st_mode,
                stat.st_size,
                stat.st_mtime_ns,
                payload,
            )
        )
    return values


def test_report_verifies_objects_and_exposes_local_protection_graph(tmp_path):
    state = tmp_path / "state"
    builder = _builder(state, tmp_path)
    active = _generation(builder, tmp_path, "active-generation")
    pipeline_input = _generation(
        builder, tmp_path, "pipeline-generation"
    )
    unused = _generation(builder, tmp_path, "unused-generation")
    builder._activate(active, "active")

    repository = tmp_path / "repository"
    snapshot = _snapshot(state, repository)

    pipeline_id = "1" * 32
    pipeline = (
        state
        / "image-build/pipelines"
        / pipeline_id
    )
    pipeline.mkdir(parents=True)
    (pipeline / "pipeline.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "pipeline_id": pipeline_id,
                "operation": "image",
                "selection": str(
                    pipeline_input.root.resolve().parent
                ),
                "arguments": {"targets": ["fixture"]},
                "recipes": [],
                "policy": None,
                "source_pins": "fixture",
                "attempts": {},
                "status": "pending",
                "owner": {
                    "recipe_snapshot": snapshot.snapshot
                },
            }
        )
    )

    artifacts = ApplicationSoftwareStore(state)
    used_artifact = _application_artifact(
        artifacts, "artifact-a", "used"
    )
    unused_artifact = _application_artifact(
        artifacts, "artifact-b", "unused"
    )
    views = ApplicationSoftwareViewStore(state)
    view = views.publish(
        "view-a",
        application="station-access",
        artifacts=[used_artifact.artifact],
    )
    # Simulate an owner having pruned historical operation receipts.  The
    # immutable object itself remains and should become only locally unreferenced.
    shutil.rmtree(
        artifacts.root / "operations/artifact-b"
    )

    before = _fingerprint(state)
    first = report(state)
    second = report(state)
    after = _fingerprint(state)

    assert first == second
    assert before == after
    assert first["contract"] == CONTRACT
    assert first["reference_complete"] is True
    assert first["integrity_complete"] is True
    assert first["reclamation_authorized"] is False
    assert first["report_digest"].startswith("sha256:")

    assert _object(
        first, "generation", active.generation
    )["classification"] == "protected"
    assert _object(
        first, "generation", pipeline_input.generation
    )["classification"] == "protected"
    assert _object(
        first, "generation", unused.generation
    )["classification"] == "apparently-unreferenced"
    assert _object(
        first, "recipe-snapshot", snapshot.snapshot
    )["classification"] == "protected"
    assert _object(
        first, "application-artifact", used_artifact.artifact
    )["classification"] == "protected"
    assert _object(
        first, "application-artifact", unused_artifact.artifact
    )["classification"] == "apparently-unreferenced"
    assert _object(
        first, "application-view", view.view
    )["classification"] == "referenced"

    assert active.generation in first["protection_set"]["generation"]
    assert (
        unused.generation
        in first["apparent_candidates"]["generation"]
    )
    assert (
        unused_artifact.artifact
        in first["apparent_candidates"]["application-artifact"]
    )


def test_corrupt_published_object_is_never_a_reclamation_candidate(
    tmp_path,
):
    state = tmp_path / "state"
    builder = _builder(state, tmp_path)
    generation = _generation(builder, tmp_path, "corrupt-generation")
    (generation.root / "payload").write_text("tampered")

    result = report(state)
    value = _object(
        result, "generation", generation.generation
    )
    assert value["classification"] == "integrity-fault"
    assert value["reclamation"] == "blocked-integrity-fault"
    assert result["integrity_complete"] is False
    assert (
        generation.generation
        not in result["apparent_candidates"]["generation"]
    )


def test_unreadable_reference_metadata_fails_closed_for_unprotected_objects(
    tmp_path,
):
    state = tmp_path / "state"
    builder = _builder(state, tmp_path)
    generation = _generation(builder, tmp_path, "candidate-generation")
    pipeline = state / "image-build/pipelines" / ("2" * 32)
    pipeline.mkdir(parents=True)
    (pipeline / "pipeline.json").write_text("{not-json")

    result = report(state)
    value = _object(
        result, "generation", generation.generation
    )
    assert result["reference_complete"] is False
    assert value["classification"] == "unknown"
    assert value["reclamation"] == "blocked-reference-incomplete"
    assert result["apparent_candidates"]["generation"] == []


def test_missing_referenced_object_is_reported_and_fails_closed(
    tmp_path,
):
    state = tmp_path / "state"
    builder = _builder(state, tmp_path)
    existing = _generation(builder, tmp_path, "existing-generation")
    pipeline_id = "3" * 32
    pipeline = state / "image-build/pipelines" / pipeline_id
    pipeline.mkdir(parents=True)
    missing = "4" * 64
    (pipeline / "pipeline.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "pipeline_id": pipeline_id,
                "selection": str(
                    state
                    / "image-build/generations"
                    / missing
                ),
                "status": "pending",
            }
        )
    )

    result = report(state)
    assert result["reference_complete"] is False
    assert any(
        fault["scope"] == "missing-referenced-object"
        and missing in fault["identity"]
        for fault in result["faults"]
    )
    assert _object(
        result, "generation", existing.generation
    )["classification"] == "unknown"


def test_pending_application_publication_protects_frozen_identity(
    tmp_path,
):
    state = tmp_path / "state"
    store = ApplicationSoftwareStore(state)
    prepared = store.begin(
        "pending-a",
        application="station-access",
        revision="git:" + "a" * 40,
        sources=[],
        compatibility_requirements=_compatibility(),
        notices=(),
        provenance={},
    )
    (prepared.root / "bin").mkdir()
    (prepared.root / "bin/tool").write_text("pending")
    operation = store.root / "operations/pending-a"
    intent = json.loads((operation / "intent.json").read_text())
    frozen = store._freeze(operation, intent)
    # Publish the immutable object but intentionally omit the result receipt,
    # modelling response loss after publication.
    candidate = store._candidate(
        "pending-a", operation, frozen
    )
    target = (
        store.root
        / "artifacts"
        / frozen["artifact"][7:]
    )
    os.replace(candidate, target)

    result = report(state)
    value = _object(
        result,
        "application-artifact",
        frozen["artifact"],
    )
    assert value["classification"] == "protected"
    assert any(
        item["relation"] == "pending-publication"
        for item in value["protected_by"]
    )

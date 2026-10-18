import hashlib
import json
import os
import platform
from pathlib import Path

import pytest

from zog.image_build import ImageBuild
from zog.image_build.application_software import (
    ApplicationSoftwareStore,
    MOUNT_CONTRACT,
)
from zog.image_build.application_views import ApplicationSoftwareViewStore
from zog.image_build.filesystem import inventory
from zog.image_build.metadata import identity
from zog.image_build.recipe_snapshots import RecipeSnapshotStore


def _builder(tmp_path):
    packages = tmp_path / "packages"
    packages.mkdir()
    return ImageBuild(
        package_dir=packages,
        state_dir=tmp_path / "state",
        runner=object(),
    )


def _root(tmp_path, name="root"):
    root = tmp_path / name
    root.mkdir()
    (root / "payload").write_text(name)
    return root


def _compatibility():
    return {
        "schema": 1,
        "mount_contract": MOUNT_CONTRACT,
        "architecture": "x86_64",
        "python": None,
        "libraries": [],
    }


def _artifact(store, operation="artifact-a", content="fixture"):
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
    (prepared.root / "bin/tool").write_text(content)
    return prepared


def _catalogue(tmp_path):
    root = tmp_path / "repository"
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
        repr(
            {
                "build": [["true"]],
                "install": [["true"]],
            }
        )
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
                "packages": {
                    "fixture": {"sources": [source]}
                },
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
    return root, catalogue


def _snapshot(store):
    return store.prepare(
        "snapshot-op",
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


def test_generation_lost_publish_response_recovers_exact_published_object(
    tmp_path, monkeypatch
):
    import zog.image_build.engine as module

    builder = _builder(tmp_path)
    root = _root(tmp_path)
    original = module._publish_generation_candidate
    published = []

    def lose(candidate, target):
        original(candidate, target)
        published.append(target.name)
        raise OSError("lost generation publication response")

    monkeypatch.setattr(
        module, "_publish_generation_candidate", lose
    )
    with pytest.raises(
        OSError, match="lost generation publication response"
    ):
        builder.import_bootstrap(root, {"fixture": True})

    generations = list(
        (builder.state / "image-build/generations").iterdir()
    )
    assert [path.name for path in generations] == published
    assert not (
        builder.state
        / "image-build/publication"
        / published[0]
    ).exists()

    monkeypatch.setattr(
        module, "_publish_generation_candidate", original
    )
    recovered = builder.import_bootstrap(
        root, {"fixture": True}
    )
    assert recovered.generation == published[0]
    assert recovered.reused
    assert len(
        list(
            (builder.state / "image-build/generations").iterdir()
        )
    ) == 1


def test_generation_partial_staging_is_rebuilt_from_exact_source(
    tmp_path,
):
    builder = _builder(tmp_path)
    root = _root(tmp_path)
    outputs = inventory(root)
    inputs = {
        "schema": 2,
        "kind": "host-bootstrap",
        "host": {"fixture": True},
        "files": outputs,
        "architecture": platform.machine(),
    }
    generation = identity(inputs)
    pending = (
        builder.state
        / "image-build/publication"
        / generation
    )
    pending.mkdir(parents=True)
    (pending / "partial").write_text("interrupted copy")

    published = builder.import_bootstrap(
        root, {"fixture": True}
    )
    assert published.generation == generation
    assert not pending.exists()
    assert inventory(published.root) == outputs


def test_generation_valid_staging_with_changed_manifest_fails_closed(
    tmp_path,
):
    builder = _builder(tmp_path)
    root = _root(tmp_path)
    outputs = inventory(root)
    inputs = {
        "schema": 2,
        "kind": "host-bootstrap",
        "host": {"fixture": True},
        "files": outputs,
        "architecture": platform.machine(),
    }
    generation = identity(inputs)
    pending = (
        builder.state
        / "image-build/publication"
        / generation
    )
    (pending / "root").mkdir(parents=True)
    (pending / "root/payload").write_text("root")
    manifest = {
        "schema": 2,
        "generation": generation,
        "kind": "host-bootstrap",
        "inputs": inputs,
        "outputs": inventory(pending / "root"),
        "host": {"different-detail": True},
    }
    (pending / "manifest.json").write_text(
        json.dumps(manifest)
    )

    with pytest.raises(
        Exception,
        match="retained generation publication candidate differs",
    ):
        builder.import_bootstrap(root, {"fixture": True})
    assert pending.exists()
    assert not (
        builder.state
        / "image-build/generations"
        / generation
    ).exists()


def test_recipe_snapshot_lost_publish_response_recovers_same_identity(
    tmp_path, monkeypatch
):
    import zog.image_build.recipe_snapshots as module

    _, catalogue = _catalogue(tmp_path)
    store = RecipeSnapshotStore(
        tmp_path / "state", catalogue
    )
    original = module._publish_snapshot_candidate
    published = []

    def lose(candidate, target):
        original(candidate, target)
        published.append("sha256:" + target.name)
        raise OSError("lost snapshot publication response")

    monkeypatch.setattr(
        module, "_publish_snapshot_candidate", lose
    )
    with pytest.raises(
        OSError, match="lost snapshot publication response"
    ):
        _snapshot(store)

    monkeypatch.setattr(
        module, "_publish_snapshot_candidate", original
    )
    recovered = _snapshot(store)
    assert recovered.snapshot == published[0]
    assert recovered.reused
    assert store.resolve(recovered.snapshot).manifest == (
        recovered.manifest
    )


def test_recipe_snapshot_stale_candidate_is_rebuilt(
    tmp_path,
):
    _, catalogue = _catalogue(tmp_path)
    store = RecipeSnapshotStore(
        tmp_path / "state", catalogue
    )
    candidate = (
        store.root / "candidates/snapshot-op"
    )
    candidate.mkdir(parents=True)
    (candidate / "stale").write_text("stale")

    published = _snapshot(store)
    assert published.snapshot.startswith("sha256:")
    assert not candidate.exists()
    assert store.resolve(published.snapshot).snapshot == (
        published.snapshot
    )


def test_application_artifact_lost_publish_response_recovers_same_identity(
    tmp_path, monkeypatch
):
    import zog.image_build.application_software as module

    store = ApplicationSoftwareStore(tmp_path / "state")
    operation = _artifact(store)
    original = module._publish_artifact_candidate
    published = []

    def lose(candidate, target):
        original(candidate, target)
        published.append("sha256:" + target.name)
        raise OSError("lost artifact publication response")

    monkeypatch.setattr(
        module, "_publish_artifact_candidate", lose
    )
    with pytest.raises(
        OSError, match="lost artifact publication response"
    ):
        store.finalize(operation.operation)

    result = (
        store.root
        / "operations"
        / operation.operation
        / "result.json"
    )
    assert not result.exists()

    monkeypatch.setattr(
        module, "_publish_artifact_candidate", original
    )
    recovered = store.finalize(operation.operation)
    assert recovered.artifact == published[0]
    assert recovered.reused
    assert store.resolve(recovered.artifact).manifest == (
        recovered.manifest
    )


def test_application_artifact_corrupt_candidate_fails_closed(
    tmp_path,
):
    store = ApplicationSoftwareStore(tmp_path / "state")
    operation = _artifact(store)
    operation_path = (
        store.root / "operations" / operation.operation
    )
    intent = json.loads(
        (operation_path / "intent.json").read_text()
    )
    frozen = store._freeze(operation_path, intent)
    candidate = store._candidate(
        operation.operation, operation_path, frozen
    )
    (candidate / "root/bin/tool").write_text("tampered")

    with pytest.raises(
        Exception,
        match="candidate differs from frozen inventory",
    ):
        store.finalize(operation.operation)
    assert not (
        store.root / "artifacts" / frozen["artifact"][7:]
    ).exists()


def test_application_view_stale_candidate_is_recomposed(
    tmp_path,
):
    state = tmp_path / "state"
    artifacts = ApplicationSoftwareStore(state)
    prepared = _artifact(artifacts)
    artifact = artifacts.finalize(prepared.operation)
    views = ApplicationSoftwareViewStore(state)
    intent = views._intent(
        "view-op",
        "station-access",
        "application",
        [artifact.artifact],
    )
    operation = views._operation_path("view-op")
    operation.mkdir(parents=True)
    (operation / "intent.json").write_text(
        json.dumps(intent)
    )
    frozen = views._frozen(operation, intent)
    candidate = views._compose_candidate(
        "view-op", frozen["manifest"]
    )
    (candidate / "manifest.json").write_text("{}")

    published = views.publish(
        "view-op",
        application="station-access",
        artifacts=[artifact.artifact],
    )
    assert views.resolve(published.view).manifest == (
        frozen["manifest"]
    )
    assert not candidate.exists()

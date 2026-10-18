"""Immutable remotely selected recipe snapshots.

The repository monthly provenance pin and the materialized recipe snapshot are
separate immutable objects. This module owns the latter: exact selected recipe
directories plus the pins.snapshot() record that binds them to one reviewed monthly
source set.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from .errors import ImageBuildError
from .filesystem import (
    digest,
    discard_staging,
    ensure_directory,
    inventory,
    sync_directory,
    sync_tree,
    write_json,
)
from .metadata import (
    identity,
    literal,
    load_packages,
    names,
    order,
    relative,
)

CONTRACT = "image-build-recipe-snapshot-v1"
SCHEMA = 1


@dataclass(frozen=True)
class RecipeSnapshot:
    snapshot: str
    package_dir: Path
    manifest: dict
    reused: bool = False


def normalize_entries(entries, *, allow_extra=False):
    if not isinstance(entries, list) or not entries:
        raise ImageBuildError("recipe snapshot requires selected recipe entries")
    normalized = []
    ids = []
    for entry in entries:
        required = {"id", "project", "recipe"}
        if (
            not isinstance(entry, dict)
            or not required <= set(entry)
            or (not allow_extra and set(entry) != required)
        ):
            raise ImageBuildError(
                "recipe snapshot entry requires id, project and recipe"
            )
        package_id = entry["id"]
        project = entry["project"]
        recipe = entry["recipe"]
        names([package_id])
        names([project])
        recipe = relative(recipe)
        ids.append(package_id)
        normalized.append(
            {
                "id": package_id,
                "project": project,
                "recipe": recipe,
            }
        )
    names(ids)
    return sorted(normalized, key=lambda item: item["id"])


def _materialize_one(catalogue, destination, entry):
    source = catalogue / relative(entry["recipe"])
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(catalogue)
    except (OSError, ValueError) as error:
        raise ImageBuildError(
            "recipe snapshot source escapes catalogue"
        ) from error
    if source.is_symlink() or not source.is_dir():
        raise ImageBuildError(
            "recipe snapshot source must be a real directory"
        )

    selected_sources = literal(source / "sources.py")
    license_path = source / "license.py"
    if not license_path.exists():
        license_path = catalogue / entry["project"] / "license.py"
    from .licensing import load as load_license

    load_license(license_path, selected_sources)

    from .source_provenance import (
        NAME as SOURCE_PROVENANCE,
        load as load_source_provenance,
    )

    provenance_path = source / SOURCE_PROVENANCE
    if not provenance_path.exists() and not provenance_path.is_symlink():
        provenance_path = (
            catalogue / entry["project"] / SOURCE_PROVENANCE
        )
    has_provenance = (
        provenance_path.exists() or provenance_path.is_symlink()
    )
    if has_provenance:
        load_source_provenance(
            provenance_path, selected_sources
        )

    expected = [
        record
        for record in inventory(source)
        if record["path"] not in ("license.py", SOURCE_PROVENANCE)
    ]
    expected.append(
        {
            "kind": "file",
            "mode": 0o644,
            "path": "license.py",
            "sha256": digest(license_path),
        }
    )
    if has_provenance:
        expected.append(
            {
                "kind": "file",
                "mode": 0o644,
                "path": SOURCE_PROVENANCE,
                "sha256": digest(provenance_path),
            }
        )
    expected.sort(key=lambda record: record["path"])

    target = destination / entry["id"]
    if target.exists():
        if target.is_symlink() or inventory(target) != expected:
            raise ImageBuildError(
                "recorded recipe snapshot package changed"
            )
        return

    import shutil

    shutil.copytree(source, target, symlinks=False)
    shutil.copyfile(license_path, target / "license.py")
    (target / "license.py").chmod(0o644)
    if has_provenance:
        shutil.copyfile(
            provenance_path, target / SOURCE_PROVENANCE
        )
        (target / SOURCE_PROVENANCE).chmod(0o644)


def materialize(catalogue, entries, destination, *, pin_date=None):
    """Create/recover a self-contained selected recipe directory."""
    catalogue = Path(catalogue).resolve()
    destination = Path(destination)
    if catalogue.is_symlink() or not catalogue.is_dir():
        raise ImageBuildError("recipe catalogue must be a real directory")
    entries = normalize_entries(entries, allow_extra=True)
    ensure_directory(destination)

    from .pins import snapshot as snapshot_pin, validate as validate_pin

    pin = snapshot_pin(
        catalogue, entries, destination, pin_date=pin_date
    )
    for entry in entries:
        _materialize_one(catalogue, destination, entry)

    packages = load_packages(destination)
    validate_pin(destination, packages)
    if set(packages) != {entry["id"] for entry in entries}:
        raise ImageBuildError(
            "recipe snapshot has unexpected package definitions"
        )
    sync_tree(destination)
    return pin, packages


def _manifest_identity(manifest):
    payload = {
        key: value
        for key, value in manifest.items()
        if key != "snapshot"
    }
    return "sha256:" + identity(payload)


def _snapshot_hex(snapshot):
    if (
        not isinstance(snapshot, str)
        or not snapshot.startswith("sha256:")
        or len(snapshot) != 71
        or any(c not in "0123456789abcdef" for c in snapshot[7:])
    ):
        raise ImageBuildError("invalid recipe snapshot identity")
    return snapshot[7:]


def _read_snapshot(root, snapshot):
    directory = Path(root) / "snapshots" / _snapshot_hex(snapshot)
    manifest_path = directory / "manifest.json"
    package_dir = directory / "package"
    if (
        directory.is_symlink()
        or package_dir.is_symlink()
        or manifest_path.is_symlink()
        or not directory.is_dir()
        or not package_dir.is_dir()
        or not manifest_path.is_file()
    ):
        raise ImageBuildError(
            "invalid or unavailable recipe snapshot"
        )
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError, TypeError) as error:
        raise ImageBuildError(
            "invalid recipe snapshot manifest"
        ) from error
    required = {
        "schema",
        "contract",
        "snapshot",
        "source",
        "pin_date",
        "monthly_identity",
        "entries",
        "packages",
        "inventory",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != required
        or manifest.get("schema") != SCHEMA
        or manifest.get("contract") != CONTRACT
        or manifest.get("snapshot") != snapshot
        or _manifest_identity(manifest) != snapshot
    ):
        raise ImageBuildError(
            "recipe snapshot manifest identity changed"
        )
    if normalize_entries(manifest["entries"]) != manifest["entries"]:
        raise ImageBuildError(
            "recipe snapshot entries are not canonical"
        )
    if inventory(package_dir) != manifest["inventory"]:
        raise ImageBuildError(
            "recipe snapshot package inventory changed"
        )
    from .pins import validate as validate_pin

    packages = load_packages(package_dir)
    pin = validate_pin(package_dir, packages)
    if (
        set(packages) != set(manifest["packages"])
        or {
            name: packages[name].fingerprint
            for name in sorted(packages)
        }
        != manifest["packages"]
        or pin.get("date") != manifest["pin_date"]
        or "monthly_identity" not in pin
        or "sha256:" + pin["monthly_identity"]
        != manifest["monthly_identity"]
    ):
        raise ImageBuildError(
            "recipe snapshot package/pin binding changed"
        )
    return RecipeSnapshot(
        snapshot=snapshot,
        package_dir=package_dir,
        manifest=manifest,
        reused=True,
    )


def _publish_snapshot_candidate(candidate, target):
    """Atomically publish one fully synced immutable recipe snapshot."""
    os.replace(candidate, target)
    sync_directory(target.parent)


class RecipeSnapshotStore:
    """Content-addressed selected recipe snapshots below image-build state."""

    def __init__(self, state_dir, catalogue):
        self.state = Path(state_dir).resolve()
        self.catalogue = Path(catalogue).resolve()
        self.root = self.state / "image-build" / "recipe-snapshots"
        ensure_directory(self.root / "candidates")
        ensure_directory(self.root / "snapshots")

    def resolve(self, snapshot):
        return _read_snapshot(self.root, snapshot)

    def prepare(
        self,
        operation_id,
        *,
        entries,
        pin_date,
        source_repository,
        source_revision,
        expected_monthly_identity=None,
    ):
        entries = normalize_entries(entries)
        if not isinstance(operation_id, str) or not operation_id:
            raise ImageBuildError(
                "recipe snapshot requires operation identity"
            )
        candidate = self.root / "candidates" / operation_id
        if candidate.is_symlink():
            raise ImageBuildError(
                "recipe snapshot candidate must not be a symlink"
            )
        package_dir = candidate / "package"

        def build_candidate():
            if candidate.exists():
                discard_staging(candidate)
            ensure_directory(candidate)
            ensure_directory(package_dir)
            pin, packages = materialize(
                self.catalogue,
                entries,
                package_dir,
                pin_date=pin_date,
            )
            # A remotely submitted snapshot must be closed over all build,
            # runtime and test dependencies. Stage workers may materialize a
            # broader plan and validate only its targets separately.
            order(packages, sorted(packages))
            monthly_identity = "sha256:" + pin["monthly_identity"]
            if (
                expected_monthly_identity is not None
                and monthly_identity != expected_monthly_identity
            ):
                raise ImageBuildError(
                    "recipe snapshot monthly identity differs from bound provenance pin"
                )
            manifest = {
                "schema": SCHEMA,
                "contract": CONTRACT,
                "snapshot": "",
                "source": {
                    "repository": source_repository,
                    "revision": source_revision,
                },
                "pin_date": pin["date"],
                "monthly_identity": monthly_identity,
                "entries": entries,
                "packages": {
                    name: packages[name].fingerprint
                    for name in sorted(packages)
                },
                "inventory": inventory(package_dir),
            }
            manifest["snapshot"] = _manifest_identity(manifest)
            write_json(candidate / "manifest.json", manifest)
            sync_tree(candidate)
            return manifest

        # Candidates are not authoritative recovery evidence. A lost response
        # may rebuild this unpublished staging tree from the exact deployed
        # source/request; only the content-addressed published target is reused.
        manifest = build_candidate()

        snapshot = manifest["snapshot"]
        target = self.root / "snapshots" / _snapshot_hex(snapshot)
        if target.exists():
            existing = self.resolve(snapshot)
            if existing.manifest != manifest:
                raise ImageBuildError(
                    "recipe snapshot identity collision"
                )
            if candidate.exists():
                discard_staging(candidate)
            return existing

        _publish_snapshot_candidate(candidate, target)
        published = self.resolve(snapshot)
        if published.manifest != manifest:
            raise ImageBuildError(
                "published recipe snapshot differs"
            )
        return RecipeSnapshot(
            snapshot=published.snapshot,
            package_dir=published.package_dir,
            manifest=published.manifest,
            reused=False,
        )

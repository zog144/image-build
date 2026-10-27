"""Targeted Boot A package build and bounded retained-image overlay derivation.

This operation is intentionally narrower than a rootfs rebuild.  It binds one exact
retained parent image, builds only the reviewed targeted package plan, overlays only
the named runtime outputs, records every collision/addition, permits no implicit
removals, requires fresh installed verification, and publishes a canonical generation
whose historical parent remains explicitly legacy/incomplete.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import re
import shutil
import stat
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from . import ImageBuild, read_selection
from .configuration import configured_runner
from .developer.seed_build import verify as verify_installed
from .errors import ImageBuildError
from .filesystem import discard_staging, ensure_directory, inventory, write_json
from .staging_durability import (
    copy as copy_staging_tree,
    inventory as staging_inventory,
    set_directory_modes,
    sync as sync_staging_tree,
)
from .final_compiler import successful_execution
from .generation_provenance import prepare, finish, verify as verify_generation
from .metadata import Package, identity, load_packages
from .provenance import Provenance
from .rootfs_compatibility import FIELD as COMPATIBILITY_FIELD, derive as derive_compatibility
from .stages import stage_recipes
from . import installed_verification
from . import engine as engine_module

CONTRACT = "image-build-resident-boot-targeted-derivation-v1"
FIELD = "resident_boot_targeted_derivation"
GAP_CONTRACT = "image-build-resident-boot-parent-gap-v1"
PARENT = {
    "generation": "45a81ec3ea473bfa397e546b5c0ec1ae306bf00cb864eaa9a86d94c13c623f2e",
    "manifest_sha256": "a58645f5d53b3810aae6641b0f2eac4df1c97265151e8b63770e6700e1ec9f58",
    "output_count": 40948,
    "outputs_identity": "sha256:687aa0e46aaafc660aa1fcd8f9f7492dc62a382dff0d7556746e3df195b4aa77",
}
ALLOWED_MODE_REPLACEMENTS = {
    "applications": (0o755, 0o000),
}
OVERLAY_TARGETS = ("systemd-final", "shadow-login")
BUILD_ONLY_DEPENDENCIES = {
    # Both inputs are intentionally disposable build-root material.  The static
    # os-release fixture is required by upstream systemd tests and must not be
    # confused with installed-host identity; pyelftools is required by elf2efi.
    "systemd-final": ("systemd-test-environment", "pyelftools-build"),
    "shadow-login": (),
}


@contextmanager
def _targeted_staging_sync():
    """Scope restrictive-directory durability to this targeted producer only.

    engine.py/filesystem.py remain byte-identical to the accepted image-progress
    observer source.  The targeted coordinator is single-threaded under the owner
    operation lock, so replacing the imported sync callback is bounded to this
    call and restored even on failure.
    """
    original = engine_module.sync_tree
    engine_module.sync_tree = sync_staging_tree
    try:
        yield
    finally:
        engine_module.sync_tree = original


def _prepare_publication_candidate(builder, root, inputs, kind, details):
    """Pre-stage a generation candidate using restrictive-directory-safe copy/sync."""
    root = Path(root)
    outputs = staging_inventory(root)
    fingerprint = identity(inputs)
    store = builder.state / "image-build" / "generations"
    target = store / fingerprint
    if target.exists():
        return
    publication = store.parent / "publication"
    ensure_directory(publication)
    pending = publication / fingerprint
    manifest = {
        "schema": engine_module.SCHEMA,
        "generation": fingerprint,
        "kind": kind,
        "inputs": inputs,
        "outputs": outputs,
        **details,
    }
    if pending.exists() or pending.is_symlink():
        if pending.is_symlink():
            raise ImageBuildError("generation publication candidate is a symlink")
        manifest_path = pending / "manifest.json"
        root_path = pending / "root"
        if not manifest_path.is_file() or not root_path.is_dir():
            discard_staging(pending)
        else:
            try:
                retained_manifest = json.loads(manifest_path.read_text())
                retained_outputs = staging_inventory(root_path)
            except (OSError, ValueError, TypeError):
                discard_staging(pending)
            else:
                if retained_manifest != manifest or retained_outputs != outputs:
                    raise ImageBuildError("retained generation publication candidate differs")
                sync_staging_tree(pending)
                return
    ensure_directory(pending)
    copy_staging_tree(root, pending / "root", expected=outputs)
    write_json(pending / "manifest.json", manifest)
    sync_staging_tree(pending)
    if staging_inventory(pending / "root") != outputs:
        raise ImageBuildError("generation publication staging changed")


def _targeted_build_definitions(definitions):
    """Preserve only reviewed build-only inputs required by targeted outputs."""
    result = dict(definitions)
    for name in OVERLAY_TARGETS:
        if name not in definitions:
            raise ImageBuildError("targeted Boot A definition missing: " + name)
        package = definitions[name]
        allowed = BUILD_ONLY_DEPENDENCIES[name]
        if any(dependency not in definitions for dependency in allowed):
            raise ImageBuildError("targeted Boot A build-only dependency missing")
        if any(dependency not in package.build_dependencies for dependency in allowed):
            raise ImageBuildError("targeted Boot A package lost required build-only dependency")
        result[name] = replace(
            package,
            build_dependencies=allowed,
            runtime_dependencies=(),
            test_dependencies=(),
        )
    return result


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parent_binding(parent):
    path = parent.root.parent / "manifest.json"
    if (
        parent.generation != PARENT["generation"]
        or _sha256(path) != PARENT["manifest_sha256"]
        or len(parent.manifest.get("outputs", [])) != PARENT["output_count"]
        or "sha256:" + identity(parent.manifest["outputs"]) != PARENT["outputs_identity"]
        or parent.manifest.get("kind") != "image"
        or parent.manifest.get("historical_provenance_complete") is not False
    ):
        raise ImageBuildError("retained Boot A parent differs from reviewed preflight")
    return dict(PARENT)


def _record_map(records):
    return {record["path"]: record for record in records}


def overlay_plan(parent, overlays):
    """Freeze all ownership/collision decisions before changing staging bytes."""
    base = _record_map(parent.manifest["outputs"])
    selected = {}
    owners = {}
    overlay_bindings = {}
    for name in OVERLAY_TARGETS:
        record = overlays.get(name)
        if not isinstance(record, dict) or staging_inventory(record["root"]) != record.get("outputs"):
            raise ImageBuildError("targeted overlay output changed: " + name)
        if not record.get("provenance"):
            raise ImageBuildError("targeted overlay lacks provenance: " + name)
        overlay_bindings[name] = {
            "identity": record["identity"],
            "provenance": record["provenance"],
            "outputs_identity": "sha256:" + identity(record["outputs"]),
        }
        for entry in record["outputs"]:
            path = entry["path"]
            prior = selected.get(path)
            if prior is not None and prior != entry:
                raise ImageBuildError("targeted overlays disagree on output: " + path)
            if prior is not None and entry["kind"] != "directory":
                raise ImageBuildError("targeted overlays share non-directory output: " + path)
            selected[path] = entry
            owners.setdefault(path, []).append(name)

    collisions = []
    additions = []
    for path in sorted(selected, key=Path):
        new = selected[path]
        old = base.get(path)
        if old is None:
            additions.append({"path": path, "owners": sorted(owners[path]), "new": new})
            continue
        if old["kind"] == "directory" and new["kind"] == "directory":
            modes = (old["mode"], new["mode"])
            if modes[0] != modes[1] and ALLOWED_MODE_REPLACEMENTS.get(path) != modes:
                raise ImageBuildError("unreviewed directory mode replacement: " + path)
        elif old["kind"] != new["kind"]:
            raise ImageBuildError("targeted overlay changes output kind: " + path)
        collisions.append({
            "path": path,
            "owners": sorted(owners[path]),
            "old": old,
            "new": new,
        })

    # /state must be newly supplied as an empty mode-0000 directory by systemd-final;
    # /applications must be the single reviewed 0755 -> 0000 mode replacement.
    state = selected.get("state")
    applications = selected.get("applications")
    if (
        base.get("state") is not None
        or state != {"path": "state", "mode": 0, "kind": "directory"}
        or applications != {"path": "applications", "mode": 0, "kind": "directory"}
        or base.get("applications") != {
            "path": "applications", "mode": 0o755, "kind": "directory"
        }
    ):
        raise ImageBuildError("resident mountpoint overlay differs from reviewed contract")

    expected = dict(base)
    expected.update(selected)
    return {
        "schema": 1,
        "contract": CONTRACT,
        "parent": _parent_binding(parent),
        "overlays": overlay_bindings,
        "collisions": collisions,
        "additions": additions,
        "removals": [],
        "expected_outputs": [expected[name] for name in sorted(expected, key=Path)],
    }


def _safe_target(root, name):
    target = root / name
    for parent in target.relative_to(root).parents:
        if parent != Path(".") and (root / parent).is_symlink():
            raise ImageBuildError("overlay target parent is a symlink: " + name)
    return target


def _replace_entry(source_root, root, entry):
    name = entry["path"]
    source = Path(source_root) / name
    target = _safe_target(root, name)
    if entry["kind"] == "directory":
        if target.exists():
            if target.is_symlink() or not target.is_dir():
                raise ImageBuildError("overlay directory target differs: " + name)
        else:
            target.mkdir(parents=True)
        # Keep mode-0000 fail-closed mountpoints traversable until all staging
        # durability barriers have completed. Their final mode is set below.
        target.chmod(0o700 if entry["mode"] == 0 else entry["mode"])
        return
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            raise ImageBuildError("overlay cannot replace directory with file: " + name)
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    if entry["kind"] == "symlink":
        target.symlink_to(entry["target"])
    elif entry["kind"] == "file":
        shutil.copy2(source, target)
        target.chmod(entry["mode"])
    else:
        raise ImageBuildError("unsupported overlay entry kind")


def compose(parent, overlays, plan, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        discard_staging(destination)
    shutil.copytree(parent.root, destination, symlinks=True)
    for name in OVERLAY_TARGETS:
        root = Path(overlays[name]["root"])
        for entry in overlays[name]["outputs"]:
            _replace_entry(root, destination, entry)
    # The package output requires final mode 0000.  Keep these two empty
    # mountpoints owner-traversable while overlay bytes are copied, then apply the
    # exact final modes and use the caller-owned staging durability barrier.
    set_directory_modes(destination, {"state": 0, "applications": 0})
    sync_staging_tree(destination)
    actual = staging_inventory(destination)
    if actual != plan["expected_outputs"]:
        raise ImageBuildError("targeted Boot A composition differs from frozen overlay plan")
    return actual


def _parent_package(parent, provenance):
    inputs = {
        "schema": 1,
        "kind": "retained-parent-image",
        "generation": parent.generation,
        "manifest_sha256": PARENT["manifest_sha256"],
        "historical_provenance_complete": False,
    }
    result = {
        "identity": identity({"inputs": inputs, "outputs": parent.manifest["outputs"]}),
        "inputs": inputs,
        "outputs": parent.manifest["outputs"],
        "integration": {"project": "retained-parent", "stage_id": "legacy-image"},
        "root": str(parent.root),
    }
    result["provenance"] = provenance.legacy_output("retained-parent", result)
    provenance.verify_output(result["provenance"], "retained-parent", result)
    return result


def _assembly_definitions(definitions):
    empty = lambda name: Package(name, (), (), (), {}, {}, (), {})
    return {
        "retained-parent": empty("retained-parent"),
        **{
            name: replace(
                definitions[name],
                build_dependencies=(),
                runtime_dependencies=(),
                test_dependencies=(),
            )
            for name in OVERLAY_TARGETS
        },
    }


def validate_manifest(inputs, details):
    value = inputs.get(FIELD) if isinstance(inputs, dict) else None
    if value is None and (not isinstance(details, dict) or FIELD not in details):
        return False
    if (
        not isinstance(value, dict)
        or details.get(FIELD) != value
        or value.get("contract") != CONTRACT
        or value.get("parent") != PARENT
        or value.get("historical_provenance", {}).get("contract") != GAP_CONTRACT
        or value["historical_provenance"].get("status") != "incomplete"
        or details.get("historical_provenance_complete") is not False
        or details.get("host_boot_ready") is not False
        or "build_record" not in details
        or details.get("verification_execution", {}).get("exit_code") != 0
        or details.get("verification_execution", {}).get("cleanup_complete") is not True
    ):
        raise ImageBuildError("invalid targeted resident-boot derivation publication")
    return True


def run(project, catalogue, controller, selection, work, source_revision, host_id, project_id,
        plan_file, check_file, retry_of=None, pin_revision=None):
    project, catalogue, controller, selection, work = map(
        lambda value: Path(value).resolve(),
        (project, catalogue, controller, selection, work),
    )
    if re.fullmatch(r"[0-9a-f]{40}", source_revision or "") is None:
        raise ImageBuildError("exact producer source revision required")
    state = project / "state"
    ensure_directory(work)
    with (work / "operation.lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        parent = read_selection(selection)
        parent_binding = _parent_binding(parent)
        plan = stage_recipes(Path(plan_file), catalogue, work / "recipes")
        if tuple(plan.get("overlay_targets", ())) != OVERLAY_TARGETS:
            raise ImageBuildError("targeted Boot A overlay target set differs")
        definitions = load_packages(work / "recipes")
        pin = Provenance.capture_pin(
            state,
            catalogue.parent / "pins/2026-10-01/commit-pin.py",
            repository="https://github.com/zog144/image-build",
            revision=pin_revision or source_revision,
            repository_path="project/pins/2026-10-01/commit-pin.py",
        )
        provenance = Provenance(
            state,
            host_id=host_id,
            project_id=project_id,
            pin=pin,
            generation_contract="rootfs-v1",
            retry_of=json.loads(Path(retry_of).read_text()) if retry_of else None,
        )
        builder = ImageBuild(
            package_dir=work / "recipes",
            state_dir=state,
            runner=configured_runner(controller, state),
            maximum_generations=32,
            provenance=provenance,
        )
        check = Path(check_file).read_text()
        if not check.strip():
            raise ImageBuildError("targeted Boot A installed check is empty")
        intent = {
            "schema": 1,
            "contract": CONTRACT,
            "source_revision": source_revision,
            "parent": parent_binding,
            "recipes": inventory(work / "recipes"),
            "plan": plan,
            "policy": builder._policy(),
            "check": check,
            "provenance": provenance.configuration(),
        }
        intent_path = work / "intent.json"
        if intent_path.exists():
            if json.loads(intent_path.read_text()) != intent:
                raise ImageBuildError("frozen targeted Boot A operation changed")
        else:
            write_json(intent_path, intent)

        package_attempt = state / "image-build/attempts" / (work.name + "-packages")
        ensure_directory(package_attempt)
        # The exact retained parent is the build environment. Materialized support
        # recipes remain source-review evidence, but their already-installed bytes
        # are not rebuilt or overlaid into that parent. Only the two requested
        # package outputs execute in this targeted operation.
        build_definitions = _targeted_build_definitions(definitions)
        with builder.locked(), _targeted_staging_sync():
            built = builder._build_set(
                build_definitions, plan["targets"], parent, package_attempt
            )
        overlays = {name: built[name] for name in OVERLAY_TARGETS}
        for name, record in overlays.items():
            provenance.verify_output(record["provenance"], name, record)

        composition = overlay_plan(parent, overlays)
        plan_path = work / "composition-plan.json"
        if plan_path.exists():
            if json.loads(plan_path.read_text()) != composition:
                raise ImageBuildError("targeted Boot A collision plan changed")
        else:
            write_json(plan_path, composition)

        root = work / "derived-root"
        marker = work / "composition.json"
        if marker.exists():
            saved = json.loads(marker.read_text())
            if (
                saved.get("plan_identity") != "sha256:" + identity(composition)
                or not root.is_dir()
                or staging_inventory(root) != composition["expected_outputs"]
            ):
                raise ImageBuildError("retained targeted Boot A composition changed")
        else:
            outputs = compose(parent, overlays, composition, root)
            write_json(marker, {
                "schema": 1,
                "plan_identity": "sha256:" + identity(composition),
                "outputs_identity": "sha256:" + identity(outputs),
            })

        compatibility = derive_compatibility(
            {"resident-root": {"root": str(root), "outputs": staging_inventory(root)}},
            platform.machine(),
        )
        parent_record = _parent_package(parent, provenance)
        assembled = {"retained-parent": parent_record, **overlays}
        assembly_defs = _assembly_definitions(definitions)
        targets = ["retained-parent", *OVERLAY_TARGETS]

        parent_manifest = provenance._file(
            "resident-boot-parent-manifest.json",
            parent.root.parent / "manifest.json",
            "sha256:" + PARENT["manifest_sha256"],
        )
        composition_material = provenance._bytes(
            "resident-boot-overlay-plan.json", composition
        )
        gap = {
            "contract": GAP_CONTRACT,
            "status": "incomplete",
            "parent_generation": parent.generation,
            "legacy_parent_output": parent_record["provenance"],
            "claims_forbidden": [
                "historical-package-output-closure-complete",
                "deleted-parent-component-roots-recovered",
                "parent-is-provenance-complete",
            ],
        }
        gap_material = provenance._bytes("resident-boot-parent-gap.json", gap)
        derivation = {
            "contract": CONTRACT,
            "source_revision": source_revision,
            "parent": parent_binding,
            "overlays": {
                name: {
                    "identity": overlays[name]["identity"],
                    "provenance": overlays[name]["provenance"],
                }
                for name in OVERLAY_TARGETS
            },
            "composition_plan": composition_material,
            "historical_provenance": gap,
        }
        inputs = {
            "schema": 2,
            "kind": "image",
            "architecture": platform.machine(),
            "source_revision": source_revision,
            "verification_command": check,
            "verification_report_contract": installed_verification.CONTRACT,
            "verification_check": "resident-boot-a-targeted",
            "execution_policy": builder._policy(),
            "provenance": provenance.configuration(),
            COMPATIBILITY_FIELD: compatibility,
            FIELD: derivation,
        }
        for field in ("application_data_targets",):
            if field in parent.manifest.get("inputs", {}):
                inputs[field] = parent.manifest["inputs"][field]

        assembly_attempt = state / "image-build/attempts" / (work.name + "-assembly")
        with builder.locked():
            binding = prepare(
                provenance,
                assembly_attempt,
                assembly_defs,
                targets,
                assembled,
                inputs,
                composition_materials=[parent_manifest, composition_material, gap_material],
                composition_actions=[
                    "Treat retained-parent as an exact legacy package inventory with an explicit provenance gap.",
                    "Overlay only systemd-final and shadow-login exact verified package outputs.",
                    "Freeze every collision/addition before mutation; permit no implicit removals.",
                    "Permit only the reviewed /applications 0755 to 0000 directory-mode replacement.",
                ],
            )

        verification = state / "image-build/attempts" / (work.name + "-installed")
        verify_installed(
            builder,
            verification,
            root,
            [["/bin/bash", "-eu", "-o", "pipefail", "-c", check]],
            inputs,
        )
        execution = successful_execution(verification)

        with builder.locked():
            report = installed_verification.capture(
                provenance, binding, root, inputs, verification, execution
            )
            pointer = finish(
                provenance, assembly_attempt, binding, root, verification=[report]
            )
            details = {
                COMPATIBILITY_FIELD: compatibility,
                FIELD: derivation,
                "historical_provenance_complete": False,
                "host_boot_ready": False,
                "purpose": "resident-boot-a-targeted-candidate",
                "packages": {
                    name: {k:v for k,v in record.items() if k != "root"}
                    for name, record in assembled.items()
                },
                "build_record": pointer,
                "verification_execution": execution,
            }
            if "application_data_targets" in inputs:
                details["application_data_targets"] = inputs["application_data_targets"]
            _prepare_publication_candidate(builder, root, inputs, "image", details)
            with _targeted_staging_sync():
                accepted = builder._publish(root, inputs, "image", details)
            validate_manifest(accepted.manifest["inputs"], accepted.manifest)
            bundle = verify_generation(provenance, accepted)
        from zog.build_record.model import canonical
        canonical_path = work / "canonical-generation.json"
        canonical_path.write_bytes(canonical(bundle))
        result = {
            "schema": 1,
            "phase": "complete",
            "generation": accepted.generation,
            "parent_generation": parent.generation,
            "canonical_record": pointer["record"],
            "canonical_export": str(canonical_path),
            "verification_execution": execution,
            "historical_provenance_complete": False,
        }
        write_json(work / "result.json", result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "project", "catalogue", "controller", "selection", "work", "source-revision",
        "host-id", "project-id", "plan-file", "check-file"
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--retry-of")
    parser.add_argument("--pin-revision")
    print(json.dumps(run(**vars(parser.parse_args())), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

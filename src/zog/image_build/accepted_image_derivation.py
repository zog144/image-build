"""Durably derive an accepted image when its historical build closure is incomplete.

This is intentionally not runtime_image.publish.  It never relabels an image as a
toolchain and never fabricates the missing package/base provenance.  It binds and
rehashes an already accepted immutable image, permits only the current reviewed
empty application-data target additions, preserves the ABI descriptor, and records
the historical provenance gap as part of the new generation identity.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
from pathlib import Path

from .application_data_targets import (
    FIELD as DATA_TARGET_FIELD,
    bind as bind_application_data_targets,
    definition as data_target_definition,
    directories as data_target_directories,
    validate_root as validate_application_data_root,
)
from .errors import ImageBuildError
from .filesystem import discard_staging, inventory, merge, write_json
from .metadata import identity
from .rootfs_compatibility import FIELD as COMPATIBILITY_FIELD
from .runtime_facilities import FIELD as FACILITY_FIELD

CONTRACT = "image-build-accepted-image-derivation-v1"
ACCEPTANCE_CONTRACT = "image-build-accepted-image-derivation-acceptance-v1"
GAP_CONTRACT = "image-build-historical-provenance-gap-v1"
OPERATION_CONTRACT = "image-build-accepted-image-derivation-operation-v1"
FIELD = "accepted_image_derivation"
OPERATION_ROOT = "accepted-image-derivations"

CERTIFY_MANAGE_RECOVERY = {
    "profile": "certify-manage-runtime-generation-recovery-2026-10-22",
    "parent_generation":
        "3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc",
    "parent_manifest_sha256":
        "ebc8b392d9faf628f4264c64b011cf4f25ce1efb6f1dae74876635bff4bc2132",
    "parent_output_count": 40945,
    "missing_base_generation":
        "f07ee7f1422c04af4f1d5c5c5685bea9efc9cf046214737e6fb82e46ed063513",
    "missing_component_output_count": 54,
    "required_new_target": "/var/lib/zog-certify-manage",
    "evidence": {
        "source": "retained-review-record",
        "revision": "1347dbf3021de2cdcd07cd0ae7b69ea5362f853f",
        "path": (
            "image-build/verification/certbot-offline-wheels-2026-10-22/"
            "runtime-generation-recovery.md"
        ),
    },
}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _profile(value):
    required = {
        "profile",
        "parent_generation",
        "parent_manifest_sha256",
        "parent_output_count",
        "missing_base_generation",
        "missing_component_output_count",
        "required_new_target",
        "evidence",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ImageBuildError("invalid accepted-image recovery profile")
    for key in ("parent_generation", "missing_base_generation"):
        if (
            not isinstance(value[key], str)
            or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None
        ):
            raise ImageBuildError("invalid accepted-image recovery generation")
    if (
        not isinstance(value["parent_manifest_sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", value["parent_manifest_sha256"]) is None
        or type(value["parent_output_count"]) is not int
        or value["parent_output_count"] < 1
        or type(value["missing_component_output_count"]) is not int
        or value["missing_component_output_count"] < 1
        or value["required_new_target"] != "/var/lib/zog-certify-manage"
        or not isinstance(value["profile"], str)
        or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,119}", value["profile"])
    ):
        raise ImageBuildError("invalid accepted-image recovery profile values")
    evidence = value["evidence"]
    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"source", "revision", "path"}
        or evidence.get("source") != "retained-review-record"
        or re.fullmatch(r"[0-9a-f]{40}", evidence.get("revision", "")) is None
        or not isinstance(evidence["path"], str)
        or evidence["path"].startswith("/")
        or ".." in Path(evidence["path"]).parts
    ):
        raise ImageBuildError("invalid accepted-image recovery evidence")
    return json.loads(json.dumps(value))


def _operation_name(value):
    if not isinstance(value, str) or re.fullmatch(
        r"[a-z0-9][a-z0-9-]{0,79}", value
    ) is None:
        raise ImageBuildError("invalid accepted-image derivation operation name")
    return value


def operation_directory(state_dir, operation_name):
    return (
        Path(state_dir)
        / "image-build"
        / OPERATION_ROOT
        / _operation_name(operation_name)
    )


def _parent_binding(parent, profile, state_dir):
    manifest_path = parent.root.parent / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ImageBuildError("accepted parent manifest is unavailable")
    manifest = parent.manifest
    if parent.generation != profile["parent_generation"]:
        raise ImageBuildError("accepted parent generation differs from recovery profile")
    if _sha256(manifest_path) != profile["parent_manifest_sha256"]:
        raise ImageBuildError("accepted parent manifest digest differs")
    if manifest.get("kind") != "image":
        raise ImageBuildError("accepted-image derivation requires kind=image parent")
    if len(manifest.get("outputs", [])) != profile["parent_output_count"]:
        raise ImageBuildError("accepted parent inventory count differs")
    compatibility = manifest.get(COMPATIBILITY_FIELD)
    if not isinstance(compatibility, dict):
        raise ImageBuildError("accepted parent lacks rootfs compatibility descriptor")
    publication = manifest.get("inputs", {}).get("publication")
    if not isinstance(publication, dict):
        raise ImageBuildError("accepted parent lacks historical publication binding")
    if publication.get("base") != profile["missing_base_generation"]:
        raise ImageBuildError("accepted parent historical base differs")
    components = publication.get("components")
    if (
        not isinstance(components, dict)
        or len(components) != profile["missing_component_output_count"]
        or any(
            not isinstance(name, str)
            or not isinstance(path, str)
            or not Path(path).is_absolute()
            for name, path in components.items()
        )
    ):
        raise ImageBuildError("accepted parent component-output inventory differs")
    historical_base = (
        Path(state_dir)
        / "image-build"
        / "generations"
        / profile["missing_base_generation"]
    )
    if historical_base.exists() or historical_base.is_symlink():
        raise ImageBuildError(
            "historical base generation is available; provenance-complete publisher required"
        )
    available_components = sorted(
        path
        for path in components.values()
        if Path(path).exists() or Path(path).is_symlink()
    )
    if available_components:
        raise ImageBuildError(
            "historical component outputs are available; provenance-complete publisher required"
        )

    by_path = {record["path"]: record for record in manifest["outputs"]}
    target = profile["required_new_target"].lstrip("/")
    if target in by_path or any(name.startswith(target + "/") for name in by_path):
        raise ImageBuildError("required recovery target is already present in parent")
    return {
        "generation": parent.generation,
        "manifest_sha256": profile["parent_manifest_sha256"],
        "outputs_identity": "sha256:" + identity(manifest["outputs"]),
        "output_count": len(manifest["outputs"]),
        "compatibility_identity": "sha256:" + identity(compatibility),
        "historical_base_generation": publication["base"],
        "historical_component_outputs": {
            name: components[name] for name in sorted(components)
        },
    }


def _gap(parent_binding, profile):
    return {
        "contract": GAP_CONTRACT,
        "status": "incomplete",
        "parent_generation": parent_binding["generation"],
        "missing": {
            "inherited_base_generation": profile["missing_base_generation"],
            "component_output_roots": parent_binding["historical_component_outputs"],
        },
        "missing_component_output_count": profile["missing_component_output_count"],
        "evidence": profile["evidence"],
        "claims_forbidden": [
            "historical-package-output-closure-complete",
            "historical-base-generation-available",
            "fresh-runtime-verification",
            "parent-is-toolchain",
        ],
    }


def _expected_outputs(parent_outputs, added):
    records = {record["path"]: record for record in parent_outputs}
    for path, mode in added.items():
        if path in records:
            raise ImageBuildError("derivation addition collides with parent output")
        records[path] = {"path": path, "kind": "directory", "mode": mode}
    return [records[name] for name in sorted(records)]


def _materialize_targets(root, parent_outputs):
    root = Path(root)
    by_path = {record["path"]: record for record in parent_outputs}
    var = by_path.get("var")
    if var is None or var.get("kind") != "directory":
        raise ImageBuildError("accepted parent must retain a real /var directory")
    added = {}
    for name, mode in sorted(
        data_target_directories().items(),
        key=lambda item: (len(Path(item[0]).parts), item[0]),
    ):
        path = root / name
        if name in by_path:
            continue
        parent = path.parent
        if parent.is_symlink() or not parent.is_dir():
            raise ImageBuildError("application data target parent is unavailable: /" + name)
        path.mkdir(mode=mode)
        path.chmod(mode)
        added[name] = mode
    return added


def _acceptance(parent, profile, binding, candidate_outputs, added):
    compatibility = parent.manifest[COMPATIBILITY_FIELD]
    expected = _expected_outputs(parent.manifest["outputs"], added)
    if candidate_outputs != expected:
        raise ImageBuildError(
            "accepted-image derivation changed payload beyond reviewed empty targets"
        )
    required = profile["required_new_target"].lstrip("/")
    if required not in added:
        raise ImageBuildError("certify-manage recovery target was not newly materialized")
    preserved = {
        record["path"]: record for record in parent.manifest["outputs"]
    }
    current = {record["path"]: record for record in candidate_outputs}
    if any(current.get(name) != record for name, record in preserved.items()):
        raise ImageBuildError("accepted parent payload bytes or modes changed")
    return {
        "contract": ACCEPTANCE_CONTRACT,
        "parent_generation": parent.generation,
        "parent_manifest_sha256": binding["manifest_sha256"],
        "parent_outputs_identity": binding["outputs_identity"],
        "parent_output_count": binding["output_count"],
        "derived_outputs_identity": "sha256:" + identity(candidate_outputs),
        "derived_output_count": len(candidate_outputs),
        "preserved_parent_entries": len(parent.manifest["outputs"]),
        "added_directories": [
            {"path": "/" + name, "mode": added[name]}
            for name in sorted(added)
        ],
        "compatibility_identity": "sha256:" + identity(compatibility),
        "checks": [
            "parent-manifest-sha256",
            "parent-complete-inventory-readback",
            "parent-payload-record-equality",
            "derived-complete-inventory-readback",
            "application-data-target-empty-directory-validation",
            "rootfs-compatibility-exact-equality",
        ],
    }


def _manifest_contract(source_revision, profile, parent_binding, gap, acceptance):
    if re.fullmatch(r"[0-9a-f]{40}", source_revision or "") is None:
        raise ImageBuildError("exact producer source revision required")
    return {
        "contract": CONTRACT,
        "profile": profile["profile"],
        "source_revision": source_revision,
        "parent": parent_binding,
        "historical_provenance": gap,
        "transformation": {
            "kind": "add-reviewed-empty-application-data-targets",
            "application_data_targets": data_target_definition(),
        },
        "acceptance": acceptance,
    }


def validate_manifest(inputs, details):
    """Validate opted-in derived-image manifests on every read/publication."""
    value = inputs.get(FIELD) if isinstance(inputs, dict) else None
    if value is None and (not isinstance(details, dict) or FIELD not in details):
        return False
    if (
        not isinstance(value, dict)
        or details.get(FIELD) != value
        or value.get("contract") != CONTRACT
        or set(value) != {
            "contract",
            "profile",
            "source_revision",
            "parent",
            "historical_provenance",
            "transformation",
            "acceptance",
        }
        or re.fullmatch(r"[0-9a-f]{40}", value.get("source_revision", "")) is None
    ):
        raise ImageBuildError("invalid accepted-image derivation contract")
    parent = value["parent"]
    acceptance = value["acceptance"]
    gap = value["historical_provenance"]
    if (
        not isinstance(parent, dict)
        or re.fullmatch(r"[0-9a-f]{64}", parent.get("generation", "")) is None
        or re.fullmatch(r"[0-9a-f]{64}", parent.get("manifest_sha256", "")) is None
        or not isinstance(acceptance, dict)
        or acceptance.get("contract") != ACCEPTANCE_CONTRACT
        or acceptance.get("parent_generation") != parent["generation"]
        or acceptance.get("parent_manifest_sha256") != parent["manifest_sha256"]
        or acceptance.get("parent_outputs_identity") != parent.get("outputs_identity")
        or acceptance.get("compatibility_identity")
        != parent.get("compatibility_identity")
        or not isinstance(gap, dict)
        or gap.get("contract") != GAP_CONTRACT
        or gap.get("status") != "incomplete"
        or gap.get("parent_generation") != parent["generation"]
    ):
        raise ImageBuildError("accepted-image derivation evidence is inconsistent")
    if value["transformation"] != {
        "kind": "add-reviewed-empty-application-data-targets",
        "application_data_targets": data_target_definition(),
    }:
        raise ImageBuildError("accepted-image derivation transformation changed")
    if (
        inputs.get("kind") != "image"
        or inputs.get(DATA_TARGET_FIELD) != data_target_definition()
        or details.get(DATA_TARGET_FIELD) != data_target_definition()
        or details.get("verification_inherited_from") != parent["generation"]
        or details.get("historical_provenance_complete") is not False
        or details.get("derivation_acceptance") != acceptance
        or "build_record" in details
    ):
        raise ImageBuildError("accepted-image derivation publication claims changed")
    compatibility = inputs.get(COMPATIBILITY_FIELD)
    if (
        not isinstance(compatibility, dict)
        or details.get(COMPATIBILITY_FIELD) != compatibility
        or "sha256:" + identity(compatibility)
        != acceptance["compatibility_identity"]
    ):
        raise ImageBuildError("accepted-image derivation ABI binding changed")
    return True


def derive(builder, operation_name, source_revision, profile=CERTIFY_MANAGE_RECOVERY):
    """Publish or recover the deterministic derivation; never activates it."""
    profile = _profile(profile)
    name = _operation_name(operation_name)
    if builder.provenance and builder.provenance.generation_contract:
        raise ImageBuildError(
            "incomplete-history derivation must not claim canonical package provenance"
        )
    work = operation_directory(builder.state, name)
    work.mkdir(parents=True, exist_ok=True)
    with (work / "operation.lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with builder.locked():
            from .engine import read_selection

            parent_path = (
                builder.state
                / "image-build"
                / "generations"
                / profile["parent_generation"]
            )
            parent = read_selection(parent_path)
            parent_binding = _parent_binding(parent, profile, builder.state)
            gap = _gap(parent_binding, profile)
            intent = {
                "schema": 1,
                "contract": OPERATION_CONTRACT,
                "operation_name": name,
                "source_revision": source_revision,
                "profile": profile,
                "parent": parent_binding,
                "historical_provenance": gap,
            }
            intent_path = work / "intent.json"
            if intent_path.exists():
                if json.loads(intent_path.read_text()) != intent:
                    raise ImageBuildError("frozen accepted-image derivation changed")
            else:
                write_json(intent_path, intent)
            write_json(work / "status.json", {
                "schema": 1,
                "phase": "prepared",
                "parent_generation": parent.generation,
            })

            result_path = work / "result.json"
            if result_path.exists():
                result = json.loads(result_path.read_text())
                generation = result.get("generation")
                selected = read_selection(
                    builder.state / "image-build" / "generations" / str(generation)
                )
                validate_manifest(selected.manifest["inputs"], selected.manifest)
                if (
                    selected.manifest[FIELD].get("source_revision") != source_revision
                    or selected.manifest[FIELD].get("parent") != parent_binding
                    or result.get("phase") != "complete"
                    or result.get("parent_generation") != parent.generation
                ):
                    raise ImageBuildError("retained derivation result differs")
                return result

            # Validate the parent target state before copying any bytes.
            data_targets = bind_application_data_targets(parent.manifest["outputs"])
            staging = work / "derived-root"
            if staging.exists() or staging.is_symlink():
                discard_staging(staging)
            staging.mkdir()
            merge(parent.root, staging)
            added = _materialize_targets(staging, parent.manifest["outputs"])
            validate_application_data_root(staging, data_targets)
            candidate_outputs = inventory(staging)
            acceptance = _acceptance(
                parent, profile, parent_binding, candidate_outputs, added
            )
            write_json(work / "acceptance.json", acceptance)
            write_json(work / "status.json", {
                "schema": 1,
                "phase": "assembled",
                "parent_generation": parent.generation,
                "acceptance_identity": "sha256:" + identity(acceptance),
            })

            derivation = _manifest_contract(
                source_revision, profile, parent_binding, gap, acceptance
            )
            compatibility = parent.manifest[COMPATIBILITY_FIELD]
            inputs = {
                "schema": 2,
                "kind": "image",
                "architecture": compatibility["architecture"],
                COMPATIBILITY_FIELD: compatibility,
                DATA_TARGET_FIELD: data_targets,
                FIELD: derivation,
            }
            if FACILITY_FIELD in parent.manifest.get("inputs", {}):
                inputs[FACILITY_FIELD] = parent.manifest["inputs"][FACILITY_FIELD]
            details = {
                COMPATIBILITY_FIELD: compatibility,
                DATA_TARGET_FIELD: data_targets,
                FIELD: derivation,
                "derivation_acceptance": acceptance,
                "historical_provenance_complete": False,
                "verification_inherited_from": parent.generation,
                "purpose": "certify-manage-runtime-recovery",
                "host_boot_ready": bool(parent.manifest.get("host_boot_ready", False)),
            }
            if FACILITY_FIELD in inputs:
                details[FACILITY_FIELD] = inputs[FACILITY_FIELD]
            selected = builder._publish(staging, inputs, "image", details)
            # _publish independently recopies/reinventories the staging tree.
            selected = read_selection(selected.root.parent)
            if selected.manifest["outputs"] != candidate_outputs:
                raise ImageBuildError("published accepted-image derivation differs")
            validate_manifest(selected.manifest["inputs"], selected.manifest)
            result = {
                "schema": 1,
                "phase": "complete",
                "generation": selected.generation,
                "root": str(selected.root),
                "parent_generation": parent.generation,
                "parent_manifest_sha256": parent_binding["manifest_sha256"],
                "acceptance_identity": "sha256:" + identity(acceptance),
                "historical_provenance_complete": False,
                "source_revision": source_revision,
            }
            write_json(result_path, result)
            write_json(work / "status.json", {
                "schema": 1,
                "phase": "complete",
                "generation": selected.generation,
                "parent_generation": parent.generation,
            })
            return result


def run(project, operation_name, source_revision):
    from . import ImageBuild

    project = Path(project).resolve()
    builder = ImageBuild(
        package_dir=project / "project" / "package",
        state_dir=project / "state",
        maximum_generations=32,
        provenance=None,
    )
    return derive(builder, operation_name, source_revision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--operation-name", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

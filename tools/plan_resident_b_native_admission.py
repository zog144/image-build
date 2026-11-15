#!/usr/bin/env python3
"""Read-only Resident B accepted-compiler and exact-output stage admission.

No package builds, Host mutation, service activation or compiler authority is
derived here. The original signed compiler-base receipt MUST be reopened with
the separately installed protected issuer authority, using image-build's
original compiler_base_acceptance.resolve verifier. Source selection remains
held until the *new* corrected Boot A generation and receipts are pinned.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re

from zog.image_build import ImageBuild, read_selection
from zog.image_build.configuration import configured_runner
from zog.image_build.errors import ImageBuildError
from zog.image_build.generation_provenance import verify as verify_generation
from zog.image_build.metadata import load_packages
from zog.image_build.provenance import Provenance
from verify_resident_b_native_input_closure import (
    SELECTION, GENERATION, FAILED, closure, validate_native_admission,
)

HEX = re.compile(r"sha256:[0-9a-f]{64}\Z")
COMPILER_READER_BLOB = "3eb562bbf2460fb95af0780a079cb2b058650f80"


def deny(message):
    raise ValueError("Resident B native receipt and package admission HOLD: " + message)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _read_file(path, *, limit=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        deny("required original evidence file is absent or linked: " + str(path))
    if limit is not None and path.stat().st_size > limit:
        deny("original evidence file exceeds bounded size")
    return path.read_bytes()


def _selected_generation(project, generation):
    if (not isinstance(generation, str) or not re.fullmatch(r"[0-9a-f]{64}", generation)
            or Path(project).is_symlink()):
        deny("original generation/source selector is invalid")
    state = Path(project).resolve() / "state"
    path = state / "image-build/generations" / generation
    if path.is_symlink() or not path.is_dir():
        deny("selected original generation is not retained")
    selection = read_selection(path)
    if selection.generation != generation:
        deny("reopened original generation changed")
    return state, selection


def _provenance(state, selection):
    inputs = selection.manifest.get("inputs", {})
    if "provenance" not in inputs:
        deny("canonical predecessor lacks original provenance configuration")
    return Provenance.from_configuration(state, inputs["provenance"])


def _canonical_predecessor(state, selection, pinned):
    """Trust only the original Build Record and actual root/archive/readback."""
    if (selection.generation != pinned["generation"]
            or selection.generation in (GENERATION, FAILED)
            or selection.manifest["kind"] != "image"
            or selection.manifest["inputs"].get("source_revision") != pinned["source_revision"]):
        deny("corrected Boot A source and generation selection differs")
    p = _provenance(state, selection)
    bundle = verify_generation(p, selection)
    pointer = selection.manifest["build_record"]
    generation_record = bundle["records"][pointer["record"]]["data"]
    archive = generation_record["artifact"]
    if not isinstance(archive, dict) or not HEX.fullmatch(archive.get("digest", "")):
        deny("canonical predecessor archive lacks a Build Record artifact digest")
    archive_path = p.root / "artifacts" / archive["digest"][7:]
    raw = _read_file(archive_path)
    manifest_bytes = _read_file(selection.root.parent / "manifest.json", limit=50 * 1024 * 1024)
    receipts = selection.manifest.get("packages")
    if not isinstance(receipts, dict) or not receipts:
        deny("canonical predecessor package receipts missing")
    receipt_digest = digest(canonical(receipts))
    if (digest(raw) != archive["digest"]
            or digest(raw) != pinned["canonical_archive_sha256"]
            or digest(manifest_bytes) != pinned["canonical_manifest_sha256"]
            or receipt_digest != pinned["installed_package_receipts_sha256"]):
        deny("selected canonical archive, manifest or installed receipts differ")
    if (selection.root.parent / "manifest.json").read_bytes() != manifest_bytes
            or archive_path.read_bytes() != raw):
        deny("canonical predecessor changed during readback")
    return {
        "generation": selection.generation,
        "generation_record": pointer["record"],
        "manifest_sha256": digest(manifest_bytes),
        "archive_sha256": digest(raw),
        "package_receipts_sha256": receipt_digest,
        "packages": receipts,
        "root_outputs": selection.manifest["outputs"],
    }


def _original_compiler(compiler_project, authority_file, controller, required):
    """Reuse the installed signed Ed25519 compiler-purpose reader, no substitutes."""
    try:
        verifier = importlib.import_module("zog.image_build.compiler_base_acceptance")
    except ImportError as exc:
        deny("original reviewed compiler-base reader not installed; integrate PR20 source")
    path = Path(verifier.__file__).resolve(strict=True)
    raw = _read_file(path, limit=100000)
    expected_blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()
    if expected_blob != required["reader_source_blob_sha1"]:
        deny("original compiler reader installed source differs from reviewed selection")
    state, selected = _selected_generation(compiler_project, required["generation"])
    config = selected.manifest.get("inputs", {}).get("provenance")
    p = Provenance.from_configuration(state, config) if config else None
    builder = ImageBuild(
        package_dir=Path(compiler_project).resolve() / "package",
        state_dir=state, runner=configured_runner(controller, state),
        provenance=p,
    )
    # native_authority requires a separately authenticated installed Host policy.
    builder.compiler_base_authority = verifier.native_authority(str(authority_file))
    original = verifier.resolve(builder, selected, required["original_receipt_sha256"])
    if (original.get("schema") != required["binding_contract"]
            or original.get("generation_id") != required["generation"]
            or original.get("generation_kind") not in ("image", "toolchain")
            or original.get("project_id") != builder.compiler_base_authority["project_id"]):
        deny("accepted signed original compiler receipt has a different scope")
    return original, selected


def _stage_files_match(receipt, root_map):
    """An installed path alone never proves a compiled package exists."""
    if (not isinstance(receipt, dict)
            or not isinstance(receipt.get("outputs"), list)
            or not receipt["outputs"]
            or not isinstance(receipt.get("provenance"), dict)):
        return False
    for item in receipt["outputs"]:
        if (not isinstance(item, dict)
                or root_map.get(item.get("path")) != item):
            return False
    return True


def classify(graph, recipes, predecessors):
    """Per-stage present/missing using source fingerprint and verified byte maps.

    predecessors must originate solely from independently authenticated original
    compiler and canonical predecessor readbacks. A missing/legacy/foreign
    receipt is always a rebuild candidate, not an inferred installed package.
    """
    if type(graph) is not dict or not graph or set(recipes) != set(graph):
        deny("selected source package graph/recipe set incomplete")
    result = {}
    for stage in sorted(graph):
        package = recipes[stage]
        for source_name, predecessor in predecessors:
            receipt = predecessor["packages"].get(stage)
            if not isinstance(receipt, dict):
                continue
            if (receipt.get("inputs", {}).get("package") != package.fingerprint
                    or receipt.get("integration") != package.integration
                    or not _stage_files_match(receipt, {
                        row["path"]: row for row in predecessor["root_outputs"]
                    })):
                continue
            if any(required not in {item["path"] for item in receipt["outputs"]}
                   for required in package.outputs):
                continue
            result[stage] = {
                "state": "present-exact-reviewed-receipt",
                "source": source_name,
                "recipe_fingerprint": package.fingerprint,
            }
            break
        else:
            result[stage] = {
                "state": "missing-or-source-mismatch",
                "source": None,
                "recipe_fingerprint": package.fingerprint,
            }
    return result


def admit(*, selection, compiler_project, predecessor_project,
          authority_file, controller, recipes_directory):
    """Read-only actual native readback, never permission to run a build."""
    requirements = validate_native_admission(selection.get("native_admission"))
    pinned = requirements["corrected_predecessor"]
    if pinned["generation"] is None:
        deny("corrected Boot A successor is unpublished/unselected; do not reuse 273de2a0")
    from verify_resident_b_native_input_closure import verify as source_verify
    source_verify(selection=selection)
    compiler_binding, compiler = _original_compiler(
        compiler_project, authority_file, controller, requirements["compiler"]
    )
    predecessor_state, predecessor = _selected_generation(
        predecessor_project, pinned["generation"]
    )
    output = _canonical_predecessor(predecessor_state, predecessor, pinned)
    recipes = load_packages(Path(recipes_directory))
    graph = closure(selection["package_closure"]["source_roots"])
    if set(recipes) != set(graph):
        deny("admission requires exact 29-stage reviewed recipe set, no extras")
    original = {
        "packages": compiler.manifest.get("packages", {}),
        "root_outputs": compiler.manifest["outputs"],
    }
    decisions = classify(graph, recipes, [
        ("accepted-original-compiler", original),
        ("corrected-Boot-A", output),
    ])
    missing = [name for name, item in decisions.items()
               if item["state"] == "missing-or-source-mismatch"]
    present = [name for name, item in decisions.items()
               if item["state"] == "present-exact-reviewed-receipt"]
    return {
        "schema": "zog-resident-b-read-only-native-admission-observation-v1",
        "compiler": compiler_binding,
        "predecessor": {key: output[key] for key in (
            "generation", "generation_record", "manifest_sha256",
            "archive_sha256", "package_receipts_sha256",
        )},
        "source_stage_count": len(graph),
        "present": present,
        "missing": missing,
        "stage_decisions": decisions,
        "package_binary_closure_verified": False,
        "native_compilation_permitted": False,
        "service_activation_permitted": False,
        "boot_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=SELECTION)
    parser.add_argument("--compiler-project", type=Path, required=True)
    parser.add_argument("--predecessor-project", type=Path, required=True)
    parser.add_argument("--compiler-authority", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--recipes-directory", type=Path, required=True)
    args = parser.parse_args()
    result = admit(
        selection=json.loads(args.selection.read_text()),
        compiler_project=args.compiler_project,
        predecessor_project=args.predecessor_project,
        authority_file=args.compiler_authority,
        controller=args.controller, recipes_directory=args.recipes_directory,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

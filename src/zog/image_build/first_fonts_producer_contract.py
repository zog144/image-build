"""Read-only producer-side first Fonts base and output evidence contract.

Do not use this from request JSON. A protected native owner must independently
select the Host, installation, source, lane, accepted base and installed reader.
This adapter observes canonical producer bytes; it does NOT authorize SQS/SSM,
admit a compiler request, install a task catalogue or accept a generation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re

from .engine import read_selection
from .errors import ImageBuildError
from .generation_provenance import verify as verify_generation
from .graphical_generation_acceptance import (
    EVIDENCE as OUTPUT_EVIDENCE,
    verify as verify_graphical_output,
)
from .metadata import identity, literal

SCHEMA = "image-build-first-fonts-base-observation-v1"
TASK = "graphics-fonts-image-v1"
REPOSITORY = "zog144/image-build"
SOURCE_REVISION = "1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
MONTH = "2026-10-01"
PIN_PATH = "project/pins/2026-10-01/commit-pin.py"
PIN_SHA256 = "sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36"
PLAN_PATH = "project/bootstrap/graphics-fonts.py"
ENTRIES = (
    ("libpng-final", "libpng", "libpng/stages/final"),
    ("freetype-final", "freetype", "freetype/stages/final"),
    ("fontconfig-final", "fontconfig", "fontconfig/stages/final"),
)
TARGETS = ("libpng-final", "freetype-final", "fontconfig-final")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SHA = re.compile(r"sha256:[0-9a-f]{64}\Z")

def _deny(reason):
    raise ImageBuildError("first Fonts producer not admitted: " + reason)

def _sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def source_plan(repository_root):
    """Pin original source bytes/recipe order; no mutable recipe selection."""
    root = Path(repository_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        _deny("installed immutable producer source is not a real absolute directory")
    root = root.resolve()
    pin = root / PIN_PATH
    plan_path = root / PLAN_PATH
    if pin.is_symlink() or plan_path.is_symlink() or not pin.is_file() or not plan_path.is_file():
        _deny("original October pin or Fonts source plan unavailable")
    if _sha(pin.read_bytes()) != PIN_SHA256:
        _deny("selected original October pin bytes differ")
    try:
        parsed = literal(plan_path)
        pin_value = literal(pin)
    except (OSError, SyntaxError, ValueError, TypeError) as exc:
        raise ImageBuildError("first Fonts producer not admitted: invalid original source literals") from exc
    if pin_value.get("date") != MONTH or parsed != {
        "schema": 1,
        "architecture": "x86_64",
        "stages": [
            {"id": name, "project": project, "stage": "final", "recipe": path}
            for name, project, path in ENTRIES
        ],
        "targets": list(TARGETS),
    }:
        _deny("Fonts recipe stage or target selection changed")
    return {
        "task": TASK, "source_repository": REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "monthly_pin_identity": PIN_SHA256,
        "source_plan_path": PLAN_PATH,
        "stage_order": [name for name, _, _ in ENTRIES],
        "targets": list(TARGETS),
        "source_only": True,
        "native_compiler_authorized": False,
    }

def observe_base(builder, *, repository_root, selected_generation_id):
    """Reopen and verify a canonical stage-two toolchain without modifying it.

    The selected_generation_id is a *native owner* selection. This read-only
    function checks producer authenticity, but does not authenticate the caller
    or its Host/installation/STATE selection; that is independently installed.
    """
    source_plan(repository_root)
    if type(selected_generation_id) is not str or HEX64.fullmatch(selected_generation_id) is None:
        _deny("accepted toolchain generation must have canonical identity")
    if builder is None or getattr(builder, "provenance", None) is None:
        _deny("canonical producer provenance is unavailable")
    provenance = builder.provenance
    if getattr(provenance, "generation_contract", None) != "rootfs-v1":
        _deny("protected generation provenance contract is not selected")
    expected_pin = {
        "month": MONTH, "repository": REPOSITORY,
        "revision": SOURCE_REVISION, "path": PIN_PATH,
        "digest": PIN_SHA256,
    }
    if getattr(provenance, "pin", None) != expected_pin:
        _deny("producer native provenance source/month differs")
    if (type(getattr(provenance, "host_id", None)) is not str
        or not provenance.host_id
        or type(getattr(provenance, "project_id", None)) is not str
        or not provenance.project_id):
        _deny("producer Host/Project identity absent")
    state = Path(builder.state)
    if not state.is_absolute() or state.is_symlink() or not state.is_dir():
        _deny("selected native state is not an existing protected directory")
    path = state / "image-build" / "generations" / selected_generation_id
    manifest_path = path / "manifest.json"
    if path.is_symlink() or not path.is_dir() or manifest_path.is_symlink():
        _deny("selected immutable toolchain generation is unavailable or linked")
    from .graphical_generation_acceptance import _read_json
    initial, original = _read_json(manifest_path)
    selection = read_selection(path)
    if selection.generation != selected_generation_id or initial != selection.manifest:
        _deny("canonical selected input manifest changed")
    if (initial.get("kind") != "toolchain"
        or initial.get("stage") != 2
        or initial.get("self_hosted") is not True
        or initial.get("inputs", {}).get("kind") != "toolchain"
        or initial.get("inputs", {}).get("stage") != 2):
        _deny("selected base is not an accepted second-stage compiler toolchain")
    pointer = initial.get("build_record")
    if (type(pointer) is not dict or
        pointer.get("generation") != selected_generation_id or
        type(pointer.get("record")) is not str or
        SHA.fullmatch(pointer["record"]) is None):
        _deny("selected base has no canonical generation root record")
    verify_generation(provenance, selection)
    final, final_raw = _read_json(manifest_path)
    if final != initial or final_raw != original:
        _deny("selected generation changed during read-only verification")
    return {
        "schema": SCHEMA,
        "task": TASK, "source_repository": REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "monthly_pin_identity": PIN_SHA256,
        "host_id": provenance.host_id,
        "project_id": provenance.project_id,
        "base_generation_id": selected_generation_id,
        "base_generation_kind": "toolchain",
        "base_generation_stage": 2,
        "base_manifest_sha256": _sha(original),
        "base_inventory_sha256": "sha256:" + identity(initial["outputs"]),
        "base_generation_record_sha256": pointer["record"],
        "status": "canonical-base-observed-not-native-admission",
        "catalogue_installed": False,
        "native_compiler_authorized": False,
    }

def verify_fonts_output(builder, *, repository_root, trusted_context, observed_base):
    """Use the EXISTING canonical output attester, never a substitute receipt."""
    if type(trusted_context) is not dict or trusted_context.get("task") != TASK:
        _deny("not the selected original Fonts output task")
    if (trusted_context.get("source_repository") != REPOSITORY
        or trusted_context.get("source_revision") != SOURCE_REVISION
        or trusted_context.get("monthly_pin_identity") != PIN_SHA256):
        _deny("Fonts output is not bound to selected original source/pin")
    native_base = observe_base(
        builder, repository_root=repository_root,
        selected_generation_id=trusted_context.get("input_generation_id"),
    )
    if observed_base != native_base:
        _deny("untrusted or stale base observation substituted")
    evidence = verify_graphical_output(
        builder, repository_root=repository_root,
        trusted_context=trusted_context,
    )
    if (evidence.get("schema") != OUTPUT_EVIDENCE
        or evidence.get("task") != TASK
        or evidence.get("input_generation_id") != native_base["base_generation_id"]
        or evidence.get("output_kind") != "image"
        or evidence.get("status") != "accepted"
        or evidence.get("terminal_outcome") != "success"
        or evidence.get("uncertainty") is not False
        or evidence.get("missing_evidence_count") != 0):
        _deny("existing producer output acceptance differs")
    return evidence

def observe_base_native(builder, *, repository_root, selected_generation_id):
    """Only a root-installed native owner may call the local base observer."""
    if os.geteuid() != 0:
        raise PermissionError("first Fonts producer reader requires native protected owner")
    return observe_base(builder, repository_root=repository_root,
                        selected_generation_id=selected_generation_id)

def verify_fonts_output_native(builder, *, repository_root, trusted_context, observed_base):
    if os.geteuid() != 0:
        raise PermissionError("first Fonts output reader requires native protected owner")
    return verify_fonts_output(builder, repository_root=repository_root,
                               trusted_context=trusted_context,
                               observed_base=observed_base)

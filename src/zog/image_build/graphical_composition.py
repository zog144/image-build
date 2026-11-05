"""Finite immutable composition: accepted toolchain + verified graphical image.

Graphical images are never recast as toolchains. A separately accepted
compiler-bearing image can supply compiler files; Fonts/XCB/X11 predecessor
images remain separately verified package-generation inputs.
The original rootfs generations remain immutable.
"""
import hashlib
import json
from pathlib import Path
import platform
import re

from .engine import read_selection
from .errors import ImageBuildError
from .metadata import identity

CONTRACT = "image-build-graphical-predecessor-composition-v1"
# Immutable graphical stage target ordering from reviewed source.
FONTS = ("libpng-final", "freetype-final", "fontconfig-final")
XCB = (
    "check-final", "libevdev-final", "python-libevdev-final",
    "xorgproto-final", "libXau-final", "libXdmcp-final",
    "xcb-proto-final", "libxcb-final",
)
X11 = (
    "xtrans-final", "libX11-final", "libXext-final", "libXfixes-final",
    "libXi-final", "libXtst-final", "libXv-final", "libxkbfile-final",
    "libfontenc-final", "libXfont2-final",
)
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _reject(reason):
    raise ImageBuildError("graphical predecessor composition rejected: " + reason)


def _canonical_selection(builder, generation):
    if not isinstance(generation, str) or not _HEX.fullmatch(generation):
        _reject("predecessor generation identity must be exact")
    directory = Path(builder.state) / "image-build" / "generations" / generation
    if directory.is_symlink() or (directory / "manifest.json").is_symlink():
        _reject("predecessor generation may not follow a symlink")
    selection = read_selection(directory)
    if selection.generation != generation:
        _reject("predecessor canonical generation identity differs")
    return selection


def _verified(builder, selection, base, expected_targets):
    manifest = selection.manifest
    inputs = manifest.get("inputs")
    if (
        manifest.get("kind") != "image"
        or not isinstance(inputs, dict)
        or inputs.get("kind") != "image"
        or inputs.get("toolchain") != base.generation
        or inputs.get("architecture") != platform.machine()
        or inputs.get("targets") != list(expected_targets)
        or not isinstance(manifest.get("verification_execution"), dict)
        or manifest["verification_execution"].get("exit_code") != 0
        or manifest["verification_execution"].get("cleanup_complete") is not True
    ):
        _reject("predecessor kind, toolchain ancestry, stage or verification differs")
    provenance = builder.provenance
    if provenance is None or provenance.generation_contract != "rootfs-v1":
        _reject("canonical provenance is required")
    from .generation_provenance import verify
    bundle = verify(provenance, selection)
    root_id = manifest.get("build_record", {}).get("record")
    root = bundle["records"].get(root_id)
    if (
        not isinstance(root, dict)
        or root.get("kind") != "generation"
        or not isinstance(root.get("data", {}).get("verification"), list)
        or len(root["data"]["verification"]) != 1
    ):
        _reject("predecessor does not have one completed installed verification")
    return manifest


def validate(builder, base, predecessor, targets, *, compiler_base=None):
    """Return immutable input binding or refuse before any executable build."""
    if predecessor is None:
        return None
    stage_two=(base.manifest.get("kind") == "toolchain"
               and base.manifest.get("stage") == 2
               and base.manifest.get("self_hosted") is True)
    accepted_image=(base.manifest.get("kind") == "image" and
                    isinstance(compiler_base,dict) and
                    compiler_base.get("generation_kind") == "image" and
                    compiler_base.get("generation_id") == base.generation and
                    compiler_base.get("status") ==
                    "independent-compiler-capability-observed-not-job-authorization")
    if not (stage_two or accepted_image) or targets not in (list(XCB),list(X11)):
        _reject("only XCB/X11 may layer a verified graphical image over a separately accepted compiler base")
    stage = "fonts" if targets == list(XCB) else "xcb"
    expected_targets = FONTS if stage == "fonts" else XCB
    if hasattr(predecessor, "generation"):
        predecessor = predecessor.generation
    if predecessor == base.generation:
        _reject("predecessor is the toolchain, not an accepted graphical image")
    selection = _canonical_selection(builder, predecessor)
    manifest = _verified(builder, selection, base, expected_targets)
    ancestor = manifest["inputs"].get("graphical_predecessor")
    if stage == "fonts":
        if ancestor is not None:
            _reject("fonts image cannot have a graphical predecessor")
    else:
        if (
            not isinstance(ancestor, str)
            or not _HEX.fullmatch(ancestor)
            or ancestor in {base.generation, selection.generation}
        ):
            _reject("XCB image lacks distinct fonts ancestry")
        fonts = _canonical_selection(builder, ancestor)
        _verified(builder, fonts, base, FONTS)
        if fonts.manifest["inputs"].get("graphical_predecessor") is not None:
            _reject("graphical ancestry exceeds finite three-stage sequence")
    raw = (Path(selection.root).parent / "manifest.json").read_bytes()
    if len(raw) > 1024 * 1024:
        _reject("predecessor manifest is oversized")
    return {
        "contract": CONTRACT,
        "generation": selection.generation,
        "manifest_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "build_record": manifest["build_record"]["record"],
        "stage": stage,
        "selection": selection,
    }


def input_fields(binding):
    if binding is None:
        return {}
    return {
        "graphical_predecessor": binding["generation"],
        "graphical_predecessor_manifest_sha256": binding["manifest_sha256"],
        "graphical_predecessor_record": binding["build_record"],
        "graphical_composition_contract": CONTRACT,
    }

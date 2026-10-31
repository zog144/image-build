"""Finite, immutable graphical predecessor composition for ordinary image builds.

The promoted self-hosted toolchain is *always* the compiler base.  Only the
accepted Fonts and XCB image outputs can be overlaid into a disposable image
build environment. A protected host-deploy catalogue must select the exact
predecessor generation; this source validation is not the native owner grant.
"""
from __future__ import annotations

import re
from pathlib import Path

from .errors import ImageBuildError
from .engine import read_selection

CONTRACT = "image-build-graphical-predecessor-composition-v1"
HEX = re.compile(r"[a-f0-9]{64}\Z")
# Ordered, reviewed producer targets; arbitrary image stacking is not a mode.
FONTS = ("libpng-final", "freetype-final", "fontconfig-final")
XCB = ("check-final", "libevdev-final", "python-libevdev-final",
       "xorgproto-final", "libXau-final", "libXdmcp-final",
       "xcb-proto-final", "libxcb-final")
X11 = ("xtrans-final", "libX11-final", "libXext-final", "libXfixes-final",
       "libXi-final", "libXtst-final", "libXv-final", "libxkbfile-final",
       "libfontenc-final", "libXfont2-final")


def select(builder, base, generation, targets):
    """Reopen canonical on-disk generations; return verified immutable input.

    Never reinterpret an image as a toolchain. Require exact producer ancestry,
    reviewed next task and canonical generation provenance verification.
    """
    if type(generation) is not str or not HEX.fullmatch(generation):
        raise ImageBuildError("graphical predecessor generation invalid")
    if (base.manifest.get("kind") != "toolchain"
            or base.manifest.get("stage") != 2
            or base.manifest.get("self_hosted") is not True
            or generation == base.generation):
        raise ImageBuildError("graphical composition requires original self-hosted base")
    if (type(targets) is not list or tuple(targets) not in (XCB, X11)):
        raise ImageBuildError("graphical composition only permits XCB then X11")
    root = Path(builder.state) / "image-build" / "generations" / generation
    if (root.is_symlink() or not root.is_dir()
            or (root / "manifest.json").is_symlink()
            or (root / "root").is_symlink()):
        raise ImageBuildError("canonical graphical predecessor unavailable")
    selected = read_selection(root)
    inputs = selected.manifest.get("inputs")
    expected_previous = FONTS if tuple(targets) == XCB else XCB
    if (selected.manifest.get("kind") != "image"
            or type(inputs) is not dict
            or inputs.get("kind") != "image"
            or inputs.get("toolchain") != base.generation
            or inputs.get("targets") != list(expected_previous)
            or not isinstance(inputs.get("recipes"), dict)
            or not inputs["recipes"]):
        raise ImageBuildError("graphical predecessor kind, base or stage differs")
    if tuple(targets) == XCB:
        if "graphical_predecessor" in inputs or "graphical_composition" in inputs:
            raise ImageBuildError("fonts output is not a first graphical generation")
    else:
        inherited = inputs.get("graphical_predecessor")
        if (type(inherited) is not str or not HEX.fullmatch(inherited)
                or inherited == generation or inherited == base.generation
                or inputs.get("graphical_composition") != CONTRACT):
            raise ImageBuildError("XCB output lacks immutable fonts ancestry")
        # Reopen the original fonts generation, not merely a claimed identifier.
        prior = Path(builder.state) / "image-build" / "generations" / inherited
        if prior.is_symlink() or not prior.is_dir():
            raise ImageBuildError("fonts predecessor is no longer accepted")
        fonts = read_selection(prior)
        source = fonts.manifest.get("inputs")
        if (fonts.manifest.get("kind") != "image"
                or type(source) is not dict
                or source.get("toolchain") != base.generation
                or source.get("targets") != list(FONTS)
                or "graphical_predecessor" in source):
            raise ImageBuildError("XCB output lost original fonts ancestry")
        builder._verify_generation(fonts)
    # The canonical provenance / completed verification is mandatory.
    if not (builder.provenance and builder.provenance.generation_contract):
        raise ImageBuildError("graphical composition requires canonical build-record")
    builder._verify_generation(selected)
    return selected

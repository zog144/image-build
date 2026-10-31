"""Finite immutable graphical composition and strict non-overwrite regressions."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zog.image_build import graphical_composition as gc
from zog.image_build.engine import ImageBuild
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory
from zog.image_build.metadata import identity


def _base():
    return SimpleNamespace(
        generation="a" * 64,
        manifest={"kind": "toolchain", "stage": 2, "self_hosted": True},
    )


def test_rejects_unreviewed_targets_or_image_as_toolchain(tmp_path):
    builder = SimpleNamespace(state=tmp_path, provenance=None)
    for targets in (list(gc.FONTS), ["other-final"], list(gc.XCB) + ["extra"]):
        with pytest.raises(ImageBuildError, match="only XCB/X11"):
            gc.validate(builder, _base(), "b" * 64, targets)
    forged = SimpleNamespace(
        generation="a" * 64,
        manifest={"kind": "image", "stage": 2, "self_hosted": True},
    )
    with pytest.raises(ImageBuildError, match="only XCB/X11"):
        gc.validate(builder, forged, "b" * 64, list(gc.XCB))


def test_predecessor_id_must_be_separate_and_canonical(tmp_path):
    builder = SimpleNamespace(state=tmp_path, provenance=None)
    for bad in ("a" * 64, "BAD", "../outside", "c" * 64):
        with pytest.raises(ImageBuildError):
            gc.validate(builder, _base(), bad, list(gc.XCB))


def test_pure_merge_carries_predecessor_files_and_refuses_collision(tmp_path):
    package = tmp_path / "packages"
    package.mkdir()
    predecessor_root = tmp_path / "predecessor"
    (predecessor_root / "usr/share/fonts").mkdir(parents=True)
    (predecessor_root / "usr/share/fonts/font.ttf").write_text("font")
    image = SimpleNamespace(generation="b" * 64, root=predecessor_root)
    binding = {
        "generation": "b" * 64,
        "manifest_sha256": "sha256:" + "c" * 64,
        "build_record": "sha256:" + "d" * 64,
        "selection": image,
        "stage": "fonts",
    }
    second = tmp_path / "xcb"
    (second / "usr/lib").mkdir(parents=True)
    (second / "usr/lib/libxcb.so").write_text("xcb")
    built = {
        "libxcb-final": {
            "root": second,
            "identity": "sha256:" + "e" * 64,
        },
    }
    # _compose's package order is a readonly dependency-graph query.
    import zog.image_build.engine as engine
    from unittest.mock import patch
    with patch.object(engine, "order", return_value=["libxcb-final"]):
        dummy = ImageBuild.__new__(ImageBuild)
        root = tmp_path / "composed"
        dummy._compose(
            {"libxcb-final": object()}, ["libxcb-final"], built, root,
            graphical_predecessor=binding,
        )
        assert (root / "usr/share/fonts/font.ttf").read_text() == "font"
        assert (root / "usr/lib/libxcb.so").read_text() == "xcb"
        frozen = (root.with_suffix(".composition.json")).read_bytes()
        # No mutation on an idempotent replay.
        dummy._compose(
            {"libxcb-final": object()}, ["libxcb-final"], built, root,
            graphical_predecessor=binding,
        )
        assert (root.with_suffix(".composition.json")).read_bytes() == frozen
        (second / "usr/share/fonts").mkdir(parents=True)
        (second / "usr/share/fonts/font.ttf").write_text("replacement")
        with pytest.raises(ImageBuildError, match="conflict"):
            dummy._compose(
                {"libxcb-final": object()}, ["libxcb-final"], built,
                tmp_path / "conflicting",
                graphical_predecessor=binding,
            )


def test_predecessor_binding_is_hash_bound():
    binding = {
        "generation": "b" * 64, "manifest_sha256": "sha256:" + "c" * 64,
        "build_record": "sha256:" + "d" * 64, "stage": "fonts",
    }
    assert gc.input_fields(binding) == {
        "graphical_predecessor": "b" * 64,
        "graphical_predecessor_manifest_sha256": "sha256:" + "c" * 64,
        "graphical_predecessor_record": "sha256:" + "d" * 64,
        "graphical_composition_contract": gc.CONTRACT,
    }
    assert gc.input_fields(None) == {}


def test_image_mode_type_guard_preserved():
    from inspect import getsource
    source = getsource(ImageBuild._ensure)
    assert 'toolchain.manifest["kind"] != "toolchain"' in source
    assert 'ordinary builds require a promoted second-stage toolchain' in source


def test_accepts_real_verified_fonts_generation_as_overlay(tmp_path):
    pytest.importorskip("zog.build_record")
    from test_graphical_generation_acceptance import _fixture
    data = _fixture(tmp_path)
    base = SimpleNamespace(
        generation=data["context"]["input_generation_id"],
        manifest={"kind": "toolchain", "stage": 2, "self_hosted": True},
    )
    verified = gc.validate(
        data["builder"], base, data["output"].generation, list(gc.XCB)
    )
    assert verified["generation"] == data["output"].generation
    assert verified["build_record"] == data["pointer"]["record"]
    assert verified["stage"] == "fonts"
    assert verified["manifest_sha256"].startswith("sha256:")


def test_rejects_broken_canonical_predecessor_provenance(tmp_path):
    pytest.importorskip("zog.build_record")
    from test_graphical_generation_acceptance import _fixture
    from zog.image_build.filesystem import write_json
    data = _fixture(tmp_path)
    base = SimpleNamespace(
        generation=data["context"]["input_generation_id"],
        manifest={"kind": "toolchain", "stage": 2, "self_hosted": True},
    )
    path = (
        data["state"] / "image-build/generations"
        / data["output"].generation / "manifest.json"
    )
    manifest = json.loads(path.read_text())
    manifest["verification_execution"]["cleanup_complete"] = False
    write_json(path, manifest)
    with pytest.raises(ImageBuildError, match="verification"):
        gc.validate(
            data["builder"], base, data["output"].generation, list(gc.XCB)
        )

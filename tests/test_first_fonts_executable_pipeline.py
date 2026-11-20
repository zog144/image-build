"""Real Fonts final-stage selection through PR26's normal pipeline scheduler.

This is deliberately a prepare-only test: it must never call BoxControlRunner,
start a compiler, acquire an upstream source, create a generation, or replay a
failed native Fonts operation.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil

import pytest

from zog.image_build import first_fonts
from zog.image_build.errors import ImageBuildError
from zog.image_build.metadata import load_packages, order, literal


ROOT = Path(__file__).parents[1]


def fixture_project(tmp_path):
    # The accepted normal Project has a catalogue, not an already flattened
    # package graph. Keep an unrelated catalogue-only ACL deliberately present.
    repo = tmp_path / "selected-Project" / "source"
    catalogue = repo / "project" / "package"
    catalogue.mkdir(parents=True)
    bootstrap = repo / "project" / "bootstrap"
    bootstrap.mkdir(parents=True)
    for name in ("libpng", "freetype", "fontconfig"):
        shutil.copytree(ROOT / "project" / "package" / name, catalogue / name)
    shutil.copytree(ROOT / "project" / "package" / "acl", catalogue / "acl")
    for name in ("graphics-fonts.py", "graphics-fonts-executable-pin.py"):
        shutil.copyfile(ROOT / "project" / "bootstrap" / name, bootstrap / name)
    return repo, catalogue


def prepare_fonts(tmp_path, *, change=None):
    from zog.image_build.engine import ImageBuild
    from zog.image_build.remote_operations import RemoteOperations, REQUEST_SCHEMA
    from zog.image_build.runner import BoxControlRunner

    repo, catalogue = fixture_project(tmp_path)
    if change is not None:
        change(repo, catalogue)
    state = tmp_path / "selected-Project" / "state"
    builder = ImageBuild(
        package_dir=catalogue, state_dir=state,
        runner=BoxControlRunner(
            execute=lambda request: (_ for _ in ()).throw(
                AssertionError("source-only Fonts test attempted a compiler command")
            )
        ),
    )
    from zog.image_build.engine import ImageSelection
    from zog.image_build.filesystem import inventory
    from zog.image_build.metadata import identity
    import platform

    # A synthetic, immutable *kind=image* compiler selection. We verify
    # selection mechanics, not claim the real signed certbot-seed receipt.
    from zog.image_build.engine import SCHEMA
    inputs = {"schema": SCHEMA, "kind": "image", "architecture": platform.machine()}
    generation = identity(inputs)
    directory = state / "image-build" / "generations" / generation
    (directory / "root").mkdir(parents=True)
    (directory / "root" / "usr").mkdir()
    outputs = inventory(directory / "root")
    (directory / "manifest.json").write_text(json.dumps({
        "schema": SCHEMA, "generation": generation, "kind": "image",
        "inputs": inputs, "outputs": outputs,
    }, sort_keys=True))
    link = state / "image-build" / "active"
    link.symlink_to(Path("generations") / generation)
    remote = RemoteOperations(
        builder,
        repository_root=repo,
        source_repository="zog144/image-build",
        source_revision="a" * 40,
    )
    request = {
        "schema": REQUEST_SCHEMA,
        "operation_id": "source-only-first-fonts",
        "operation": "pipeline.submit",
        "source": {"repository": "zog144/image-build", "revision": "a" * 40},
        "arguments": {"mode": "image", "targets": list(first_fonts.TARGETS)},
    }
    operation = remote._directory(request["operation_id"])
    operation.mkdir(parents=True)
    return remote, request, operation, builder, repo, catalogue


def test_fonts_normal_producer_prepares_actual_closed_executable_stages(tmp_path):
    remote, request, operation, builder, repo, catalogue = prepare_fonts(tmp_path)
    # The unrelated catalog still fails the old immutable admission gate.
    with pytest.raises(ImageBuildError, match="acl: catalogue-only"):
        load_packages(catalogue)
    before = [(p.relative_to(catalogue), p.read_bytes()) for p in
              sorted(catalogue.rglob("*")) if p.is_file()]
    pipeline_id = remote._prepare_pipeline(request, operation)
    pipeline = builder.inspect_pipeline(pipeline_id)
    snap = builder.state / "image-build" / "pipelines" / pipeline_id / "package"
    packages = load_packages(snap)
    assert pipeline["status"] == "prepared"
    assert pipeline["operation"] == "image"
    assert pipeline["arguments"]["targets"] == list(first_fonts.TARGETS)
    assert list(order(packages, pipeline["arguments"]["targets"])) == list(first_fonts.TARGETS)
    assert set(packages) == set(first_fonts.TARGETS)
    assert "acl" not in packages
    assert "recipe_snapshot" not in pipeline.get("owner", {})
    assert pipeline["source_pins"]
    assert (snap / "commit-pin.py").is_file()
    source_pin = literal(snap / "commit-pin.py")
    assert source_pin["schema"] == 1
    assert source_pin["date"] == first_fonts.PIN_DATE
    assert source_pin["monthly_identity"]
    assert set(source_pin["packages"]) == set(first_fonts.TARGETS)
    for name in first_fonts.TARGETS:
        pkg = packages[name]
        for phase in ("configure", "build", "test", "install"):
            assert pkg.steps[phase], (name, phase)
            assert pkg.steps[phase][0][0] == "/bin/bash"
        assert pkg.sources[0]["url"].startswith("https://")
        assert len(pkg.sources[0]["sha256"]) == 64
        assert set(first_fonts.OUTPUTS[name]) <= set(pkg.outputs)
        assert pkg.licensing["evidence"]
        assert pkg.licensing["status"] == "declared"
    assert [p for p in builder.state.rglob("*.controller.json")] == []
    assert list((builder.state / "image-build" / "attempts").glob("*")) == [] if (
        builder.state / "image-build" / "attempts").exists() else True
    assert before == [(p.relative_to(catalogue), p.read_bytes()) for p in
                      sorted(catalogue.rglob("*")) if p.is_file()]
    assert not (builder.state / "image-build" / "generations" / "new-fonts-generation").exists()
    # Same operation must recover the exact immutable prepared pipeline.
    assert remote._prepare_pipeline(request, operation) == pipeline_id
    assert builder.inspect_pipeline(pipeline_id) == pipeline


@pytest.mark.parametrize("changed, expected", [
    ("missing_build", "invalid literal metadata"),
    ("missing_install", "invalid literal metadata"),
    ("empty_build", "build and install steps must be explicit"),
    ("missing_source", "invalid literal metadata"),
    ("wrong_source_sha", "first Fonts stage source URL/SHA256 differs"),
    ("missing_manifest", "invalid literal metadata"),
    ("missing_required_output", "required binary/header/config/notice output missing"),
    ("missing_notice", "invalid literal metadata"),
    ("changed_notice_sha", "license source identity differs"),
])
def test_fonts_rejects_nonexecutable_unpinned_or_unnoticed_stage(tmp_path, changed, expected):
    def damage(repo, catalogue):
        stage = catalogue / "freetype" / "stages" / "final"
        if changed.startswith("missing_") and changed in {
            "missing_build", "missing_install", "missing_source",
            "missing_manifest", "missing_notice"
        }:
            names = {
                "missing_build": "build.py", "missing_install": "build.py",
                "missing_source": "sources.py",
                "missing_manifest": "produce-manifest.py",
                "missing_notice": None,
            }
            if changed == "missing_notice":
                (catalogue / "freetype" / "license.py").unlink()
            else:
                (stage / names[changed]).unlink()
        elif changed == "empty_build":
            value = literal(stage / "build.py")
            value["build"] = []
            (stage / "build.py").write_text(repr(value))
        elif changed == "wrong_source_sha":
            value = literal(stage / "sources.py")
            value[0]["sha256"] = "f" * 64
            (stage / "sources.py").write_text(repr(value))
        elif changed == "missing_required_output":
            path = stage / "produce-manifest.py"
            value = literal(path)
            value["required"].remove("usr/share/licenses/freetype/LICENSE.TXT")
            path.write_text(repr(value))
        elif changed == "changed_notice_sha":
            path = catalogue / "freetype" / "license.py"
            value = literal(path)
            value["source"]["sha256"] = "0" * 64
            path.write_text(repr(value))
    remote, request, operation, builder, _, _ = prepare_fonts(
        tmp_path, change=damage)
    with pytest.raises(ImageBuildError, match=expected):
        remote._prepare_pipeline(request, operation)
    assert not list((builder.state / "image-build/pipelines").glob("*/pipeline.json"))
    assert not list(builder.state.rglob("*.controller.json"))


def test_generic_unrelated_catalogue_only_request_still_fails(tmp_path):
    remote, request, operation, builder, _, _ = prepare_fonts(tmp_path)
    request["arguments"]["targets"] = ["acl"]
    with pytest.raises(ImageBuildError, match="acl: catalogue-only"):
        remote._prepare_pipeline(request, operation)
    assert not list((builder.state / "image-build/pipelines").glob("*/pipeline.json"))


def test_stage_deps_and_notices_cannot_be_swapped(tmp_path):
    def damage(repo, catalogue):
        stage = catalogue / "fontconfig" / "stages" / "final"
        path = stage / "dependencies.py"
        value = literal(path)
        value["runtime"] = []
        path.write_text(repr(value))
    remote, request, operation, builder, _, _ = prepare_fonts(
        tmp_path, change=damage)
    with pytest.raises(ImageBuildError, match="unreviewed Fonts dependency"):
        remote._prepare_pipeline(request, operation)
    assert not list((builder.state / "image-build/pipelines").glob("*/pipeline.json"))

import json
from pathlib import Path

import pytest

from zog.image_build.application_data_targets import (
    CONTRACT,
    FIELD,
    bind,
    definition,
    directories,
    validate,
    validate_manifest,
    validate_root,
)
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory


EXPECTED_MODES = {
    "/var/lib/archive-mirror": 0o755,
    "/var/lib/station-access": 0o755,
    "/var/lib/zog-certify-manage": 0o700,
}
EXPECTED_PATHS = list(EXPECTED_MODES)


def _root(tmp_path):
    root = tmp_path / "root"
    (root / "var/lib").mkdir(parents=True)
    return root


def test_production_target_contract_is_exact_and_manifest_bound():
    value = definition()
    assert value["contract"] == CONTRACT
    assert [item["path"] for item in value["targets"]] == EXPECTED_PATHS
    assert {item["path"]: item["mode"] for item in value["targets"]} == EXPECTED_MODES
    assert all(
        item["materialization"] == "immutable-empty-mount-target"
        for item in value["targets"]
    )
    assert directories() == {
        "var/lib": 0o755,
        "var/lib/archive-mirror": 0o755,
        "var/lib/station-access": 0o755,
        "var/lib/zog-certify-manage": 0o700,
    }
    assert validate(value) == value
    validate_manifest({FIELD: value}, {FIELD: value})
    with pytest.raises(ImageBuildError, match="not frozen"):
        validate_manifest({FIELD: value}, {})


@pytest.mark.parametrize("target", EXPECTED_PATHS)
def test_existing_empty_target_is_allowed_but_content_is_rejected(tmp_path, target):
    root = _root(tmp_path)
    path = root / target.lstrip("/")
    path.mkdir()
    path.chmod(EXPECTED_MODES[target])
    assert bind(inventory(root)) == definition()
    (path / "payload").write_text("must not be hidden by the writable mount")
    with pytest.raises(ImageBuildError, match="not empty"):
        bind(inventory(root))


@pytest.mark.parametrize("target", EXPECTED_PATHS)
def test_target_file_symlink_or_mode_conflict_fails_closed(tmp_path, target):
    root = _root(tmp_path)
    path = root / target.lstrip("/")
    path.write_text("not a directory")
    with pytest.raises(ImageBuildError, match="conflicts"):
        bind(inventory(root))

    path.unlink()
    path.symlink_to("/tmp")
    with pytest.raises(ImageBuildError, match="conflicts"):
        bind(inventory(root))

    path.unlink()
    path.mkdir()
    path.chmod(0o755 if EXPECTED_MODES[target] == 0o700 else 0o700)
    with pytest.raises(ImageBuildError, match="conflicts"):
        bind(inventory(root))


def test_target_parent_symlink_is_rejected(tmp_path):
    root = tmp_path / "root"
    (root / "var").mkdir(parents=True)
    (root / "var/lib").symlink_to("/tmp")
    with pytest.raises(ImageBuildError, match="parent is redirected"):
        bind(inventory(root))


def test_composed_root_requires_empty_real_targets(tmp_path):
    root = _root(tmp_path)
    value = definition()
    for item in value["targets"]:
        path = root / item["path"].lstrip("/")
        path.mkdir()
        path.chmod(item["mode"])
    assert validate_root(root, value) == value

    blocked = root / "var/lib/station-access/payload"
    blocked.write_text("unexpected immutable data")
    with pytest.raises(ImageBuildError, match="not empty"):
        validate_root(root, value)


def test_exact_box_control_consumer_contract_is_pinned():
    fixture = json.loads(
        (
            Path(__file__).with_name("fixtures")
            / "application-data-target-controller-contract.json"
        ).read_text()
    )
    assert fixture == {
        "schema": 1,
        "box_control": {
            "repository": "zog144/box-control",
            "revision": "644170fc441863307092f329bf7e23cb64eb33e2",
            "path": "box-control/src/zog/box_control/mounts.py",
            "blob_sha": "5fa552b5c58e97aa5a3fac1a2bfb85bd54221602",
            "mount_contract": "zog-mounts-v1",
        },
        "require_targets": True,
        "targets": EXPECTED_PATHS,
    }

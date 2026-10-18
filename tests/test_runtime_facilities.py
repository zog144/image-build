import json
from pathlib import Path

import pytest

from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory, merge
from zog.image_build.host_labels import compose, snapshot
from zog.image_build.runtime_facilities import (
    CONTRACT,
    FIELD,
    ROOT_MODES,
    ROOTS,
    derive,
    validate_manifest,
)
from zog.image_build.runtime_image import MOUNTPOINTS, _same_contents


def _record(tmp_path, name, *, mode=0o755, payload=False):
    root = tmp_path / name
    (root / "usr/bin").mkdir(parents=True)
    (root / "usr/bin/probe").write_text(name)
    (root / "run/dbus").mkdir(parents=True)
    (root / "run/dbus").chmod(mode)
    if payload:
        (root / "run/dbus/payload").write_text("immutable")
    return {
        "identity": name,
        "root": str(root),
        "outputs": inventory(root),
    }


def test_directory_only_facility_intent_is_canonical_and_manifest_bound(tmp_path):
    built = {"dbus": _record(tmp_path, "dbus")}
    value = derive(built)
    assert value["contract"] == CONTRACT
    assert [item["path"] for item in value["roots"]] == [
        "/" + name for name in ROOTS
    ]
    assert value["directories"] == [
        {
            "path": "/run/dbus",
            "mode": 0o755,
            "packages": ["dbus"],
            "materialization": "runtime-owner",
        }
    ]
    validate_manifest({FIELD: value}, {FIELD: value})
    with pytest.raises(ImageBuildError, match="not frozen"):
        validate_manifest({FIELD: value}, {})


@pytest.mark.parametrize("facility", ROOTS)
def test_facility_files_are_never_silently_stripped(tmp_path, facility):
    root = tmp_path / facility
    (root / facility).mkdir(parents=True)
    (root / facility / "payload").write_text("immutable")
    built = {
        "bad": {
            "identity": "bad",
            "root": str(root),
            "outputs": inventory(root),
        }
    }
    with pytest.raises(ImageBuildError, match="immutable package content"):
        derive(built)


def test_facility_symlink_and_root_mode_are_rejected(tmp_path):
    root = tmp_path / "symlink"
    root.mkdir()
    (root / "run").symlink_to("/tmp")
    built = {"bad": {"identity": "bad", "root": str(root), "outputs": inventory(root)}}
    with pytest.raises(ImageBuildError, match="immutable package content"):
        derive(built)

    record = _record(tmp_path, "mode")
    run = Path(record["root"]) / "run"
    run.chmod(0o700)
    record["outputs"] = inventory(record["root"])
    with pytest.raises(ImageBuildError, match="root mode differs"):
        derive({"bad": record})


def test_composition_omits_only_directory_trees_and_materializes_empty_roots(tmp_path):
    built = {"dbus": _record(tmp_path, "dbus")}
    intent = derive(built)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    root = compose(
        attempt,
        built,
        ["dbus"],
        snapshot(built),
        directories=MOUNTPOINTS,
        omit_empty_directory_trees=ROOTS,
    )
    assert (root / "usr/bin/probe").read_text() == "dbus"
    for name in ROOTS:
        facility = root / name
        assert facility.is_dir() and not facility.is_symlink()
        assert list(facility.iterdir()) == []
        assert facility.stat().st_mode & 0o7777 == ROOT_MODES[name]
    assert not (root / "run/dbus").exists()

    base = inventory(Path(built["dbus"]["root"]))
    _same_contents(base, inventory(root), intent)


def test_low_level_merge_refuses_non_directory_content_in_omitted_tree(tmp_path):
    source = tmp_path / "source"
    (source / "run/dbus").mkdir(parents=True)
    (source / "run/dbus/payload").write_text("immutable")
    with pytest.raises(ImageBuildError, match="immutable content"):
        merge(source, tmp_path / "target", omit_empty_directory_trees=("run",))


def test_unattributed_nested_facility_directory_cannot_be_removed(tmp_path):
    built = {"dbus": _record(tmp_path, "dbus")}
    intent = derive(built)
    base = inventory(Path(built["dbus"]["root"]))
    base.append({"path": "run/unattributed", "kind": "directory", "mode": 0o755})
    candidate = [
        entry for entry in base
        if not entry["path"].startswith("run/")
        and entry["path"] != "run"
    ] + [
        {"path": name, "kind": "directory", "mode": mode}
        for name, mode in MOUNTPOINTS.items()
        if name not in {entry["path"] for entry in base}
    ]
    with pytest.raises(ImageBuildError, match="lacks package intent"):
        _same_contents(base, candidate, intent)


def test_pinned_controller_contract_matches_producer_facilities():
    fixture = json.loads(
        (Path(__file__).with_name("fixtures")
         / "runtime-facility-controller-contract.json").read_text()
    )
    assert fixture["schema"] == 1
    assert fixture["box_control"] == {
        "repository": "zog144/box-control",
        "revision": "b61f0f1c3f697db33e1edf61c84bfae85d7a7e16",
        "path": "box-control/src/zog/box_control/runtime/scaffold.py",
        "blob_sha": "35e2ae4aea3a03496d385d8338a4644528049669",
    }
    assert fixture["root_control"] == {
        "repository": "zog144/root-control",
        "revision": "39ece63e33e6ec71463216eb6eea908ba81a244c",
        "path": "src/zog/root_control/systemd.py",
        "blob_sha": "430885d4899cff70f140a36122481e3229c0cda5",
    }
    assert tuple(fixture["runtime_facility_roots"]) == ROOTS
    assert fixture["admission"] == "absent-or-empty-real-directory"
    assert fixture["materialization"] == "private-runtime-scaffold"

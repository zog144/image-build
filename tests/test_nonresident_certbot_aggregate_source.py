"""Nonresident Certbot aggregate source selection and no-native-authority tests."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location(
    "nonresident_certbot_aggregate",
    ROOT / "tools/build_nonresident_certbot_aggregate.py",
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_explicit_distinct_aggregate_source_and_interpreter():
    selection = builder._selection()
    assert selection["base"]["repository"] == "zog144/zog"
    assert selection["version"] == "0.1.1.dev20261116"
    assert selection["interpreter"]["canonical_host_executable"] == "/usr/bin/python3.12"
    assert selection["controllers"]["box-control"]["selected_files"] == 52
    assert selection["controllers"]["root-control"]["selected_files"] == 26
    assert selection["native"]["installed_on_host"] is False
    assert selection["native"]["station_assignment_approved"] is False
    assert selection["native"]["certificate_issuer_ready"] is False


@pytest.mark.parametrize("change", [
    lambda d: d.update(version="0.1.0"),
    lambda d: d["interpreter"].update(canonical_host_executable="/usr/bin/python3"),
    lambda d: d["interpreter"].update(minor=15),
    lambda d: d["base"].update(revision="f" * 40),
    lambda d: d["base"]["files"].update({"pyproject.toml": "f" * 40}),
    lambda d: d["controllers"]["root-control"].update(revision="f" * 40),
    lambda d: d["controllers"]["box-control"].update(selected_files=1),
    lambda d: d["operations"].update(no_pypi_publish=False),
    lambda d: d["native"].update(installed_on_host=True),
    lambda d: d["native"].update(station_assignment_approved=True),
    lambda d: d["native"].update(approved_installer_receipt="fake"),
])
def test_fake_source_selection_or_native_approval_fails_closed(monkeypatch, change):
    record = json.loads(builder.SELECTION.read_text())
    change(record)
    monkeypatch.setattr(builder, "SELECTION", Path("/invalid/not-present"))
    original = builder.json.loads

    def controlled(content):
        if isinstance(content, str) and '"zog-nonresident-certbot-aggregate-build-v1"' in content:
            return record
        return original(content)
    monkeypatch.setattr(builder.json, "loads", controlled)
    # Return synthetic modified selection without trusting unchecked input.
    monkeypatch.setattr(builder.SELECTION.__class__, "read_text", lambda _self: json.dumps(record))
    with pytest.raises(builder.BuildHeld, match="selection or native HOLD changed|controller aggregate source pins disagree"):
        builder._selection()


def test_reject_wrong_baseline_without_creating_output(tmp_path):
    if os.environ.get("REQUIRE_RESIDENT_AGGREGATE_SOURCES") != "1":
        pytest.skip("exact companion source checkout belongs to aggregate CI")
    base = ROOT / "companions/zog-aggregate-base"
    box = ROOT / "companions/box-control"
    root = ROOT / "companions/root-control"
    target = tmp_path / "should-remain-absent"
    with pytest.raises(builder.BuildHeld, match="source checkout|unreviewed|wrong original"):
        builder.prepare(tmp_path / "unrelated-base", box, root, target)
    assert not target.exists()


def test_actual_prepared_source_composes_selected_14_component_manifest(tmp_path):
    if os.environ.get("REQUIRE_RESIDENT_AGGREGATE_SOURCES") != "1":
        pytest.skip("exact companion source checkout belongs to aggregate CI")
    base = ROOT / "companions/zog-aggregate-base"
    box = ROOT / "companions/box-control"
    root = ROOT / "companions/root-control"
    if not base.is_dir():
        pytest.fail("original pinned aggregate baseline checkout is required")
    dest = tmp_path / "aggregate-source"
    stage, selection = builder.prepare(base, box, root, dest)
    component_manifest = json.loads((stage/"src/zog/_release_manifest.json").read_text())
    assert component_manifest["distribution"] == "zog"
    assert component_manifest["version"] == selection["version"]
    assert len(component_manifest["components"]) == 14
    controllers = {item["program"]:item for item in component_manifest["components"]
                   if item["program"] in ("box-control", "root-control")}
    for name, info in controllers.items():
        assert info["revision"] == selection["controllers"][name]["revision"]
    assert not any((stage / "src/zog" / name).is_symlink()
                   for name in ("box_control","root_control"))
    assert (stage/"src/zog/box_control/issuer_lifecycle_broker.py").is_file()
    assert (stage/"src/zog/root_control/task_c_trusted_host.py").is_file()
    with pytest.raises(builder.BuildHeld, match="refuse to overwrite"):
        builder.prepare(base, box, root, dest)

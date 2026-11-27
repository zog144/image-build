"""Resident B's *new* 78-file controller selection; old Certbot wheel stays historical."""
import base64
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import pytest
from tools import verify_resident_b_aggregate_installed as aggregate

ROOT = Path(__file__).resolve().parents[1]
BOX = ROOT / "companions/resident-b-selected-box"
DAEMON = ROOT / "companions/resident-b-selected-root"


def selected():
    return json.loads(aggregate.SELECTED_PIN.read_text())


def sources():
    if not BOX.is_dir() or not DAEMON.is_dir():
        if os.environ.get("REQUIRE_RESIDENT_AGGREGATE_SOURCES") == "1":
            pytest.fail("exact R5-corrected box/root source checkouts required")
        pytest.skip("selected Resident B controller source checkouts are CI inputs")
    return BOX, DAEMON


def test_historical_wheel_cannot_be_substituted_for_corrected_pair():
    current = aggregate._check_selection(selected())
    historical = aggregate._check_selection(json.loads(aggregate.PIN.read_text()))
    assert current["distribution"]["version"] == "0.1.1.dev20261127"
    assert historical["distribution"]["version"] == "0.1.1.dev20261117"
    assert current["native"]["aggregate_wheel_sha256"] is None
    assert current["native"]["installed_accepted"] is False
    assert sum(len(row["files"]) for row in current["controllers"].values()) == 78
    assert all(current["controllers"][name]["revision"] != historical["controllers"][name]["revision"]
               for name in current["controllers"])
    forged = copy.deepcopy(current)
    forged["distribution"]["version"] = historical["distribution"]["version"]
    with pytest.raises(aggregate.AggregateHeld, match="pins/authority changed"):
        aggregate._check_selection(forged)


def test_selected_real_controller_trees_and_all_modules_are_verified():
    result = aggregate.verify_sources(*sources(), pins=selected())
    assert result["controllers"]["box-control"]["files"] == 52
    assert result["controllers"]["root-control"]["files"] == 26
    assert result["native_accepted"] is False


def stage(tmp_path):
    checkouts = sources()
    pins = selected()
    root = tmp_path / "resident-b-unpublished-synthetic-root"
    prefix = pins["distribution"]["install_prefix"]
    dist = pins["distribution"]["dist_info"]
    version = pins["distribution"]["version"]
    members = {}

    def put(name, raw, mode=0o644):
        rel = ("usr/bin/" + name.rsplit("/", 1)[-1]
               if name.startswith("../../../bin/") else prefix + "/" + name)
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(mode)
        members[name] = raw
        return target

    for name, source in pins["controllers"].items():
        checkout = checkouts[0] if name == "box-control" else checkouts[1]
        for rel, entry in source["files"].items():
            raw = (checkout / source["source_prefix"] / rel.split("/", 2)[-1]).read_bytes()
            put(rel, raw, int(entry["mode"][-3:], 8))

    put(dist + "/METADATA",
        ("Metadata-Version: 2.3\nName: zog\nVersion: " + version + "\n").encode())
    put(dist + "/WHEEL", b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
    put(dist + "/entry_points.txt",
        b"[console_scripts]\nbox-control = zog.box_control.cli:main\n"
        b"root-control = zog.root_control.daemon:main\n")
    for name in ("box-control", "root-control"):
        put("../../../bin/" + name, b"#!/usr/bin/python3.12\n# synthetic launcher\n", 0o755)
    rows = [(name, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
            .decode().rstrip("="), str(len(raw))) for name, raw in sorted(members.items())]
    rows.append((dist + "/RECORD", "", ""))
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    put(dist + "/RECORD", buffer.getvalue().encode())
    return root, pins


def test_corrected_module_bytes_wheel_record_and_no_native_promotion(tmp_path):
    root, pins = stage(tmp_path)
    report = aggregate.inspect_installed(root, pins=pins)
    assert report["status"] == "INSTALLED_BYTES_AND_RECORD_COHERENT_UNACCEPTED"
    assert report["distribution"]["version"] == "0.1.1.dev20261127"
    assert len(report["controller_modules"]) == 78
    assert len(report["installed_members"]) == 84
    assert not report["source_authorized"]
    assert not report["generation_accepted"]
    assert not report["issuer_activation_authorized"]


def test_rehashed_record_cannot_authorize_changed_selected_source(tmp_path):
    root, pins = stage(tmp_path)
    prefix = root / pins["distribution"]["install_prefix"]
    code = prefix / "zog/root_control/daemon.py"
    code.write_bytes(code.read_bytes() + b"\n# unreviewed change\n")
    record = prefix / pins["distribution"]["dist_info"] / "RECORD"
    items = list(csv.reader(io.StringIO(record.read_text())))
    for row in items:
        if row[0] == "zog/root_control/daemon.py":
            raw = code.read_bytes()
            row[1] = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
            row[2] = str(len(raw))
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(items)
    record.write_text(buffer.getvalue())
    with pytest.raises(aggregate.AggregateHeld, match="different pinned controller source"):
        aggregate.inspect_installed(root, pins=pins)


def test_wrong_revision_or_archive_refused_in_new_selection():
    pins = selected()
    pins["controllers"]["box-control"]["revision"] = "f" * 40
    with pytest.raises(aggregate.AggregateHeld, match="unreviewed controller revision"):
        aggregate._check_selection(pins)
    pins = selected()
    pins["controllers"]["root-control"]["archive_sha256"] = "a" * 64
    with pytest.raises(aggregate.AggregateHeld, match="unreviewed controller revision"):
        aggregate._check_selection(pins)

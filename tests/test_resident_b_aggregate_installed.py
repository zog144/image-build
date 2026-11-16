"""Synthetic aggregate layout; actual PR21/PR51 source bytes, never native acceptance."""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat

import pytest
from tools import verify_resident_b_aggregate_installed as aggregate

ROOT = Path(__file__).resolve().parents[1]
BOX = ROOT / "companions/box-control"
ROOT_CONTROL = ROOT / "companions/root-control"


def _sources():
    if not BOX.is_dir() or not ROOT_CONTROL.is_dir():
        if os.environ.get("REQUIRE_RESIDENT_AGGREGATE_SOURCES") == "1":
            pytest.fail("selected PR21/PR51 source checkouts required")
        pytest.skip("exact PR21/PR51 companion source checkouts are CI inputs")
    return BOX, ROOT_CONTROL


def _create(tmp_path):
    sources = _sources()
    assert aggregate.verify_sources(*sources)["native_accepted"] is False
    pins = json.loads(aggregate.PIN.read_text())
    dist = pins["distribution"]
    prefix = dist["install_prefix"]
    root = tmp_path / "unpublished-synthetic-root"
    members = {}

    def put(record_name, data, mode=0o644):
        actual = ("usr/bin/" + record_name.rsplit("/", 1)[1]
                  if record_name.startswith("../../../bin/")
                  else prefix + "/" + record_name)
        dest = root / actual
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod(mode)
        members[record_name] = data
        return dest

    for name, component in pins["controllers"].items():
        origin = sources[0] if name == "box-control" else sources[1]
        for output, entry in component["files"].items():
            relative = output.split("/", 2)[-1]
            raw = (origin / component["source_prefix"] / relative).read_bytes()
            put(output, raw, int(entry["mode"][-3:], 8))

    put("zog-0.1.0.dist-info/METADATA", b"Metadata-Version: 2.3\nName: zog\nVersion: 0.1.0\n")
    put("zog-0.1.0.dist-info/WHEEL", b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
    put("zog-0.1.0.dist-info/entry_points.txt",
        b"[console_scripts]\nbox-control = zog.box_control.cli:main\n"
        b"root-control = zog.root_control.daemon:main\n")
    for command in ("box-control", "root-control"):
        put("../../../bin/" + command, b"#!/usr/bin/python3.12\n# synthetic launcher\n", 0o755)

    rows = []
    for name, raw in sorted(members.items()):
        encoded = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
        rows.append((name, "sha256=" + encoded, str(len(raw))))
    rows.append(("zog-0.1.0.dist-info/RECORD", "", ""))
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    put("zog-0.1.0.dist-info/RECORD", buf.getvalue().encode())
    return root


def test_all_selected_controller_sources_are_exact_and_native_hold():
    box, root = _sources()
    result = aggregate.verify_sources(box, root)
    assert result["controllers"]["box-control"]["files"] == 52
    assert result["controllers"]["root-control"]["files"] == 26
    assert result["native_accepted"] is False


def test_synthetic_aggregate_with_real_controller_bytes_observes_only(tmp_path):
    root = _create(tmp_path)
    result = aggregate.inspect_installed(root)
    assert result["status"] == "INSTALLED_BYTES_AND_RECORD_COHERENT_UNACCEPTED"
    assert len(result["controller_modules"]) == 78
    assert len(result["installed_members"]) == 84
    assert result["source_authorized"] is False
    assert result["generation_accepted"] is False
    assert result["root_owned_bytes_verified"] is False
    assert result["issuer_activation_authorized"] is False


def test_record_and_installed_code_substitutions_refused(tmp_path):
    root = _create(tmp_path)
    code = root / "usr/lib/python3.12/site-packages/zog/root_control/build.py"
    code.write_bytes(code.read_bytes() + b"\n# code substitution\n")
    with pytest.raises(aggregate.AggregateHeld, match="RECORD does not match"):
        aggregate.inspect_installed(root)


def test_updated_record_does_not_authorize_changed_pinned_source(tmp_path):
    root = _create(tmp_path)
    prefix = root / "usr/lib/python3.12/site-packages"
    code = prefix / "zog/box_control/build_protocol.py"
    code.write_bytes(code.read_bytes() + b"\n# changed but wheel rehashed\n")
    record = prefix / "zog-0.1.0.dist-info/RECORD"
    rows = list(csv.reader(io.StringIO(record.read_text())))
    new = []
    for item in rows:
        if item[0] == "zog/box_control/build_protocol.py":
            content = code.read_bytes()
            item[1] = "sha256=" + base64.urlsafe_b64encode(
                hashlib.sha256(content).digest()
            ).decode().rstrip("=")
            item[2] = str(len(content))
        new.append(item)
    text = io.StringIO()
    csv.writer(text, lineterminator="\n").writerows(new)
    record.write_text(text.getvalue())
    with pytest.raises(aggregate.AggregateHeld, match="different pinned controller source"):
        aggregate.inspect_installed(root)


def test_missing_or_symlinked_aggregate_wheel_and_bad_entrypoint_refused(tmp_path):
    root = _create(tmp_path)
    record = root / "usr/lib/python3.12/site-packages/zog-0.1.0.dist-info/RECORD"
    record.rename(record.with_suffix(".bak"))
    with pytest.raises(aggregate.AggregateHeld, match="missing installed file"):
        aggregate.inspect_installed(root)
    record.with_suffix(".bak").rename(record)
    code = root / "usr/lib/python3.12/site-packages/zog/root_control/daemon.py"
    code.unlink()
    code.symlink_to("/etc/passwd")
    with pytest.raises(aggregate.AggregateHeld, match="linked installed file"):
        aggregate.inspect_installed(root)


def test_fake_native_promotion_and_wrong_pin_rejected():
    pins = json.loads(aggregate.PIN.read_text())
    pins["native"]["installed_accepted"] = True
    with pytest.raises(aggregate.AggregateHeld, match="pins/authority changed"):
        aggregate._check_selection(pins)
    pins = json.loads(aggregate.PIN.read_text())
    pins["controllers"]["root-control"]["revision"] = "f" * 40
    with pytest.raises(aggregate.AggregateHeld, match="unreviewed controller revision"):
        aggregate._check_selection(pins)


def test_aggregate_record_cannot_claim_extra_script_outside_installed_prefix(tmp_path):
    root = _create(tmp_path)
    record = root / "usr/lib/python3.12/site-packages/zog-0.1.0.dist-info/RECORD"
    with record.open("a") as stream:
        stream.write("../../../../etc/passwd,sha256=abcd,7\n")
    with pytest.raises(aggregate.AggregateHeld, match="noncanonical installed member"):
        aggregate.inspect_installed(root)

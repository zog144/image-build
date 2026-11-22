#!/usr/bin/env python3
"""Read-only exact reviewed source/installed-byte verifier for Boot A v2.

No mutable root, Host application, controller operation, compiler command, or
historical checkpoint is changed. This CANNOT authorize native execution:
root-control PR55's 0:0-compatible source is selected but native child evidence is pending.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

PIN = Path(__file__).resolve().parents[1] / "project/host/boot-a-inherited-peer-v2-source-selection.json"
CONTRACT = "zog-build-inherited-peer-v2"
IDENTITY = "inherit"
REVISIONS = {
    "box_control": "ad61fa6a4e9c3176149720868cb008e0512dbec9",
    "root_control": "a672f007b33f83bf70970e3a571fd443366bd93f",
    "host_install_resident_accounts": "4fcccb441fec851530c412f619bc02699b8a87b1",
}
COUNTS = {"box_control": 52, "root_control": 26,
          "host_install_resident_accounts": 1}
HEX = re.compile(r"[0-9a-f]{40}\Z")


class AdmissionHold(ValueError):
    pass


def hold(reason):
    raise AdmissionHold("Boot A inherited-peer source selection HOLD: " + reason)


def _read(path):
    path = Path(path)
    if path.is_symlink():
        hold("refuse symlinked selected source or installed byte: " + str(path))
    try:
        info = path.lstat()
    except OSError as exc:
        raise AdmissionHold("missing selected byte: " + str(path)) from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        hold("selected byte is not independent regular file: " + str(path))
    if info.st_size > 20 * 1024 * 1024:
        hold("selected source entry exceeds 20 MiB")
    return path.read_bytes(), ("100755" if info.st_mode & 0o111 else "100644")


def _blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()


def _git(repo, *args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL,
            text=True, timeout=15,
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise AdmissionHold("cannot verify original clean Git revision") from exc


def selection():
    obj = json.loads(PIN.read_text())
    if (obj.get("schema") != "zog-boot-a-inherited-peer-v2-candidate-selection-v1"
        or obj.get("execution_identity") != IDENTITY
        or obj.get("execution_contract") != CONTRACT
        or obj.get("status") != "COMPOSED_V2_PRODUCER_CONTROLLER_SOURCE_NATIVE_ACCEPTANCE_PENDING"
        or obj.get("native_dispatch_enabled") is not False
        or obj.get("legacy_operations_replayable") is not False
        or obj.get("existing_source_pins_and_receipts_mutated") is not False
        or obj.get("required_root_successor", {}).get("revision") != REVISIONS["root_control"]
        or obj.get("root_control_predecessor_rejected", {}).get("eligible_for_native_dispatch") is not False
        or obj.get("root_control_predecessor_rejected", {}).get("revision") != "119c50c11a73663a446ad07551fa662936856913"
        or obj.get("root_control", {}).get("review_status") != "SOURCE_CI_PASS_NATIVE_WORK_PENDING"
        or obj.get("producer", {}).get("predecessor_revision")
            != "cb73951000a3e7774ab798f58240c2a8f24d82bb"):
        hold("reviewed predecessor/native safety contract differs")
    old_files = obj.get("retained_boot_a_files")
    if (type(old_files) is not dict
        or obj.get("retained_boot_a_file_count") != 11
        or len(old_files) != 11):
        hold("reviewed PR25 Boot A source closure missing")
    for name, pin in old_files.items():
        if (not isinstance(name, str) or not name
            or name.startswith("/") or "\\" in name
            or any(part in ("", ".", "..") for part in name.split("/"))
            or type(pin) is not dict or set(pin) != {"git_blob", "mode"}
            or not HEX.fullmatch(pin["git_blob"])
            or pin["mode"] not in ("100644", "100755")):
            hold("invalid retained PR25 source pin")
    for component, revision in REVISIONS.items():
        entry = obj.get(component)
        if (type(entry) is not dict or entry.get("revision") != revision
            or type(entry.get("files")) is not dict
            or len(entry["files"]) != COUNTS[component]):
            hold("source revision/pinned file count changed: " + component)
        for name, meta in entry["files"].items():
            if (not isinstance(name, str) or not name or name.startswith("/")
                or "\\" in name or any(x in ("", ".", "..") for x in name.split("/"))
                or set(meta) != {"git_blob", "mode"}
                or not HEX.fullmatch(meta["git_blob"])
                or meta["mode"] not in ("100644", "100755")):
                hold("noncanonical source pin entry: " + component)
    return obj


def _file_selection(base, entry, *, source):
    path = Path(base)
    if path.is_symlink() or not path.is_dir():
        hold("unavailable selected component directory")
    prefix = entry["source_prefix"] if source else ""
    root = path / prefix
    observed = {}
    for file in root.rglob("*"):
        if file.is_symlink():
            hold("linked source/installed module in selected tree")
        if not file.is_file():
            continue
        rel = file.relative_to(root).as_posix()
        if rel.endswith((".py", ".c", ".h")):
            observed[rel] = file
    selected = set(entry["files"])
    if selected != set(observed) and len(selected) != 1:
        missing = selected - set(observed)
        extra = set(observed) - selected
        hold("selected source/installed file set differs: missing=" +
             repr(sorted(missing)[:4]) + ", extra=" + repr(sorted(extra)[:4]))
    if not selected <= set(observed):
        hold("selected immutable account materializer file is absent")
    observed = {name: observed[name] for name in selected}
    output = {}
    for name in sorted(observed):
        data, mode = _read(observed[name])
        expected = entry["files"][name]
        if _blob(data) != expected["git_blob"] or mode != expected["mode"]:
            hold("selected installed/source blob differs: " + name)
        output[name] = {"git_blob": expected["git_blob"],
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data)}
    return output


def verify_source(source, component, entry):
    source = Path(source)
    if (_git(source, "rev-parse", "HEAD") != entry["revision"]
        or _git(source, "status", "--porcelain", "--untracked-files=all")):
        hold("source checkout is not the pinned clean " + component + " revision")
    return _file_selection(source, entry, source=True)


def verify_installed(root, component, entry):
    # root is the package directory itself (e.g. .../zog/box_control),
    # not an arbitrary tree that can accidentally select another package.
    return _file_selection(root, entry, source=False)


def verify_producer(checkout):
    commit = _git(checkout, "rev-parse", "HEAD")
    if (not HEX.fullmatch(commit)
        or _git(checkout, "status", "--porcelain", "--untracked-files=no")):
        hold("producer is not a clean immutable checked-out source revision")
    try:
        _git(checkout, "merge-base", "--is-ancestor",
             "cb73951000a3e7774ab798f58240c2a8f24d82bb", "HEAD")
    except AdmissionHold:
        hold("producer does not retain PR25 source lineage")
    for name, pin in selection()["retained_boot_a_files"].items():
        data, mode = _read(Path(checkout) / name)
        if _blob(data) != pin["git_blob"] or mode != pin["mode"]:
            hold("PR25 getty/account/materialization/recovery source changed: " + name)
    return commit


def verify(*, producer_source, box_source, root_source, host_source,
           box_installed=None, root_installed=None, host_installed=None,
           request_native=False):
    obj = selection()
    selected = {
        "box_control": box_source,
        "root_control": root_source,
        "host_install_resident_accounts": host_source,
    }
    result = {
        "schema": "zog-boot-a-inherited-source-byte-readback-v1",
        "producer_revision": verify_producer(producer_source),
        "execution_contract": CONTRACT,
        "components": {},
        "original_predecessor_preserved": True,
        "native_dispatch_accepted": False,
    }
    for key, checkout in selected.items():
        entry = obj[key]
        sources = verify_source(checkout, key, entry)
        result["components"][key] = {
            "revision": entry["revision"], "source": sources,
            "source_verified": True, "native_accepted": False,
        }
    installs = {
        "box_control": box_installed,
        "root_control": root_installed,
        "host_install_resident_accounts": host_installed,
    }
    for key, directory in installs.items():
        if directory is not None:
            installed = verify_installed(directory, key, obj[key])
            if installed != result["components"][key]["source"]:
                hold("installed and original source bytes differ: " + key)
            result["components"][key]["installed_bytes"] = installed
    if request_native:
        hold("root-control PR55 source selected; native installed-byte and actual systemd252 authenticated-peer child acceptance still required")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--producer-source", type=Path, required=True)
    p.add_argument("--box-source", type=Path, required=True)
    p.add_argument("--root-source", type=Path, required=True)
    p.add_argument("--host-source", type=Path, required=True)
    p.add_argument("--box-installed", type=Path)
    p.add_argument("--root-installed", type=Path)
    p.add_argument("--host-installed", type=Path)
    p.add_argument("--native-admission", action="store_true")
    args = p.parse_args()
    report = verify(
        producer_source=args.producer_source, box_source=args.box_source,
        root_source=args.root_source, host_source=args.host_source,
        box_installed=args.box_installed, root_installed=args.root_installed,
        host_installed=args.host_installed, request_native=args.native_admission,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

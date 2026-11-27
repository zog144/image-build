#!/usr/bin/env python3
"""Verify the exact host-install 9ad4 importer in a real installed zog aggregate.

This independently checks all 74 selected source files, complete installed
RECORD, and actual installed source byte hashes. It is non-activating and
does not impersonate the root-owned native host-install attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess

import verify_resident_b_aggregate_installed as controller

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "project/host/nonresident-certbot-host-install-source-pins-v1.json"
REVISION = "9ad4e951ef0a14cc6a735af47ffb31734d854816"
PREFIX = "src/zog/host_install/"
EXPECTED_COUNT = 74


def refuse(message):
    raise controller.AggregateHeld(
        "Nonresident host-install importer verification HOLD: " + message
    )


def pins():
    selection = json.loads(PIN.read_text())
    if (set(selection) != {
        "schema", "status", "repository", "revision", "source_prefix",
        "files", "required_attestation_command", "interpreter",
        "selected_distribution", "installed_accepted",
    } or selection["schema"] != "zog-nonresident-certbot-selected-host-install-v1"
        or selection["status"] != "REVIEWED_SOURCE_NATIVE_IMPORT_UNACCEPTED"
        or selection["repository"] != "zog144/host-install"
        or selection["revision"] != REVISION
        or selection["source_prefix"] != PREFIX
        or selection["required_attestation_command"] != "certify-manage-controller-attest-installed"
        or selection["interpreter"] != "/usr/bin/python3.12"
        or selection["selected_distribution"] != "zog"
        or selection["installed_accepted"] is not False
        or type(selection["files"]) is not dict
        or len(selection["files"]) != EXPECTED_COUNT):
        refuse("reviewed source identity or native hold changed")
    for rel, entry in selection["files"].items():
        controller._relative(rel)
        if (not rel.startswith("zog/host_install/")
            or type(entry) is not dict
            or set(entry) != {"git_blob", "mode"}
            or not controller.GIT_SHA.fullmatch(entry["git_blob"])
            or entry["mode"] not in ("100644", "100755")):
            refuse("unreviewed source entry: " + rel)
    if "zog/host_install/certify_manage_profile.py" not in selection["files"]:
        refuse("actual selected installed attestor is absent")
    if "zog/host_install/cli.py" not in selection["files"]:
        refuse("actual selected importer CLI is absent")
    return selection


def _git(source, *args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(source), *args], text=True, timeout=10
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise controller.AggregateHeld("cannot reopen selected host-install Git checkout") from exc


def verify_source(source):
    selected = pins()
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        refuse("original selected host-install checkout unavailable")
    if (_git(source, "rev-parse", "HEAD") != REVISION
            or _git(source, "status", "--porcelain", "--untracked-files=all")):
        refuse("original selected host-install checkout changed")
    origin = source / PREFIX
    found = {
        "zog/host_install/" + p.relative_to(origin).as_posix()
        for p in origin.rglob("*") if p.is_file() or p.is_symlink()
    }
    if found != set(selected["files"]):
        refuse("host-install source tree differs from complete original selection")
    for rel, pin in selected["files"].items():
        original = origin / rel.split("/", 2)[-1]
        if original.is_symlink() or not original.is_file():
            refuse("host-install source member absent/redirected: " + rel)
        data = original.read_bytes()
        mode = "100755" if original.stat().st_mode & 0o111 else "100644"
        if controller._git_blob(data) != pin["git_blob"] or mode != pin["mode"]:
            refuse("host-install selected source content/mode substituted: " + rel)
    return {"source_revision": REVISION, "file_count": EXPECTED_COUNT,
            "source_verified": True, "native_host_installed": False}


def inspect_installed(root):
    """The full aggregate RECORD must first be checked by controller verifier."""
    select = pins()
    # This also fully verifies all installed RECORD members and all selected
    # controller sources, so host-install cannot mask a changed controller.
    base_report = controller.inspect_installed(root)
    selected_controller_pins = controller._check_selection(
        json.loads(controller.PIN.read_text())
    )
    members = base_report["installed_members"]
    installed_modules = {}
    for relative, pin in select["files"].items():
        if relative not in members:
            refuse("selected host-install member absent from installed RECORD: " + relative)
        entry = members[relative]
        recorded = controller._read(root, entry["path"])
        # _read intentionally streams large files and returns bytes only when
        # bounded; all imported host-install Python files are small.
        data = recorded["data"]
        if data is None:
            target, _ = controller._file(root, entry["path"])
            data = target.read_bytes()
        if controller._git_blob(data) != pin["git_blob"]:
            refuse("installed host-install byte differs from reviewed source: " + relative)
        if entry["mode"] != int(pin["mode"][-3:], 8):
            refuse("installed host-install mode differs from selected source: " + relative)
        installed_modules[relative] = {
            "sha256": recorded["sha256"],
            "git_blob": pin["git_blob"],
            "bytes": recorded["size"],
        }
    return {
        "schema": "zog-nonresident-certbot-combined-installed-byte-observation-v1",
        "status": "INSTALLED_CONTROLLERS_AND_IMPORTER_BYTES_COHERENT_UNACCEPTED",
        "distribution": base_report["distribution"],
        "controller_source_pins": base_report["controller_source_pins"],
        "host_install_source_revision": REVISION,
        "host_install_selected_members": installed_modules,
        "record_sha256": base_report["distribution"]["RECORD_sha256"],
        "python_executable_selected": select["interpreter"],
        "complete_record_member_count": len(members),
        "native_host_installed": False,
        "native_importer_attestation": False,
        "issuer_activation_authorized": False,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--rootfs", type=Path)
    args = ap.parse_args()
    report = verify_source(args.source)
    if args.rootfs:
        report["installed"] = inspect_installed(args.rootfs)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

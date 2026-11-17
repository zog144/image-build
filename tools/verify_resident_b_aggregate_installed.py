#!/usr/bin/env python3
"""Read-only verification of an installed *aggregate* zog wheel against pinned
box-control PR21 and root-control PR51 source bytes and the wheel RECORD.

The existing separate component-wheel evidence verifier remains in place; it
cannot attest a single zog aggregate. This verifier neither builds a wheel,
signs a receipt, starts a service, reads credentials nor authorizes activation.
"""
from __future__ import annotations

import argparse
import base64
import configparser
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "project/host/resident-b-aggregate-installed-source-pins-v1.json"
EXPECTED = {
    "box-control": (
        "zog144/box-control",
        "c886e7a90bb4ea74e771a6c5dcefaa2069539ec7",
        "2a2749f9c223fb947695634008c5e37cafc49248c19f84262f60e23c7575a121",
        "box-control/src/zog/box_control/",
        52,
    ),
    "root-control": (
        "zog144/root-control",
        "d9dfd6c02a5a96750f1213bf663cdceab72f1efd",
        "8be83a4d9e50f7165ea08f70b8443cad4553b079fa058d29c3544766ebca5de1",
        "src/zog/root_control/",
        26,
    ),
}
SHA = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
SCRIPT = re.compile(r"\.\./\.\./\.\./bin/[a-zA-Z][a-zA-Z0-9_.-]*\Z")
MAX_RECORD_BYTES = 4_000_000
MAX_ROWS = 20000
MAX_MEMBER_BYTES = 128 * 1024 * 1024


class AggregateHeld(ValueError):
    pass


def deny(message):
    raise AggregateHeld("Resident B pinned aggregate HOLD: " + message)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _relative(raw):
    if (type(raw) is not str or not raw or "\\" in raw or raw.startswith("/")
            or "\0" in raw or any(x in ("", ".", "..") for x in raw.split("/"))
            or str(PurePosixPath(raw)) != raw):
        deny("noncanonical installed member path")
    return raw


def _file(root, relative, *, max_size=MAX_MEMBER_BYTES):
    relative = _relative(relative)
    current = Path(root)
    if current.is_symlink() or not current.is_dir():
        deny("installed root is unavailable/linked")
    for part in relative.split("/")[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            deny("symlink or absent ancestor: " + relative)
    target = current / relative.split("/")[-1]
    if target.is_symlink():
        deny("linked installed file: " + relative)
    try:
        info = target.lstat()
    except OSError as exc:
        raise AggregateHeld("missing installed file: " + relative) from exc
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or not 0 <= info.st_size <= max_size
            or stat.S_IMODE(info.st_mode) & 0o022):
        deny("unsafe installed member inode/mode: " + relative)
    return target, info


def _read(root, path, *, max_size=MAX_MEMBER_BYTES):
    target, info = _file(root, path, max_size=max_size)
    before = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    h = hashlib.sha256()
    size = 0
    chunks = []
    with target.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            if size > max_size:
                deny("installed member too large: " + path)
            h.update(block)
            if max_size <= MAX_RECORD_BYTES:
                chunks.append(block)
    again = target.stat()
    after = (again.st_dev, again.st_ino, again.st_size, again.st_mtime_ns, again.st_ctime_ns)
    if before != after or size != info.st_size:
        deny("installed member changed during readback: " + path)
    return {"sha256": h.hexdigest(), "size": size,
            "mode": stat.S_IMODE(info.st_mode),
            "uid": info.st_uid, "gid": info.st_gid,
            "data": b"".join(chunks) if max_size <= MAX_RECORD_BYTES else None}


def _check_selection(pins):
    if (type(pins) is not dict or set(pins) != {"schema", "status", "distribution",
                                             "controllers", "native"}
            or pins["schema"] != "zog-resident-b-aggregate-installed-source-pins-v1"
            or pins["status"] != "SOURCE_PINNED_AGGREGATE_NOT_YET_PRODUCED"
            or pins["distribution"] != {
                "name": "zog", "version": "0.1.1.dev20261117", "python": "3.12",
                "install_prefix": "usr/lib/python3.12/site-packages",
                "dist_info": "zog-0.1.1.dev20261117.dist-info",
                "required_entry_points": {
                    "box-control": "zog.box_control.cli:main",
                    "root-control": "zog.root_control.daemon:main",
                },
            }
            or pins["native"] != {
                "aggregate_wheel_sha256": None, "installed_root_generation": None,
                "installer_receipt_sha256": None, "installed_accepted": False,
                "source_only": True,
            } or set(pins["controllers"]) != set(EXPECTED)):
        deny("aggregate pins/authority changed")
    for name, expected in EXPECTED.items():
        c = pins["controllers"][name]
        repo, revision, archive, source_prefix, count = expected
        if (set(c) != {"repository", "revision", "archive_sha256",
                      "source_prefix", "files"}
                or (c["repository"], c["revision"], c["archive_sha256"],
                    c["source_prefix"]) != (repo, revision, archive, source_prefix)
                or type(c["files"]) is not dict or len(c["files"]) != count):
            deny("unreviewed controller revision or selected source tree: " + name)
        for rel, entry in c["files"].items():
            _relative(rel)
            if (not rel.startswith("zog/" + name.replace("-", "_") + "/")
                    or type(entry) is not dict or set(entry) != {"git_blob", "mode"}
                    or not GIT_SHA.fullmatch(entry["git_blob"])
                    or entry["mode"] not in ("100644", "100755")):
                deny("invalid pinned controller member: " + rel)
    return pins


def _verify_checkout(pins, name, checkout):
    checkout = Path(checkout)
    if checkout.is_symlink() or not checkout.is_dir():
        deny("missing reviewed source checkout for " + name)
    try:
        revision = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise AggregateHeld("unable to verify original source commit: " + name) from exc
    if revision != pins["controllers"][name]["revision"] or status:
        deny("selected source checkout differs or is dirty: " + name)
    selected = pins["controllers"][name]
    source_dir = checkout / selected["source_prefix"]
    recorded = set(selected["files"])
    actual = {
        "zog/" + name.replace("-", "_") + "/" +
        p.relative_to(source_dir).as_posix()
        for p in source_dir.rglob("*") if p.is_file()
    }
    if actual != recorded:
        deny("selected controller source tree gained/lost files: " + name)
    for installed, expected in selected["files"].items():
        local = checkout / selected["source_prefix"] / installed.split("/", 2)[-1]
        if local.is_symlink() or not local.is_file():
            deny("source file is absent or linked: " + installed)
        content = local.read_bytes()
        if (_git_blob(content) != expected["git_blob"]
                or ("100755" if local.stat().st_mode & 0o111 else "100644")
                != expected["mode"]):
            deny("selected controller source file changed: " + installed)


def verify_sources(box_checkout, root_checkout, *, pins=None):
    selected = _check_selection(json.loads(PIN.read_text()) if pins is None else pins)
    _verify_checkout(selected, "box-control", box_checkout)
    _verify_checkout(selected, "root-control", root_checkout)
    return {"status": "EXACT_CONTROLLER_SOURCE_TREES_PINNED_NATIVE_HOLD",
            "controllers": {name: {"revision": selected["controllers"][name]["revision"],
                                   "files": len(selected["controllers"][name]["files"])}
                            for name in EXPECTED},
            "native_accepted": False}


def _record_member(prefix, raw, dist_info):
    if SCRIPT.fullmatch(raw):
        return "usr/bin/" + raw.rsplit("/", 1)[-1]
    path = _relative(raw)
    if not path.startswith(("zog/", dist_info + "/")):
        deny("unsupported aggregate RECORD member: " + path)
    return prefix + "/" + path


def _verify_record(root, pins):
    d = pins["distribution"]
    prefix = d["install_prefix"]
    metadata_dir = prefix + "/" + d["dist_info"]
    record_name = d["dist_info"] + "/RECORD"
    record = _read(root, metadata_dir + "/RECORD", max_size=MAX_RECORD_BYTES)
    raw = record["data"]
    try:
        lines = list(csv.reader(io.StringIO(raw.decode("utf-8", errors="strict"))))
    except (UnicodeError, csv.Error) as exc:
        raise AggregateHeld("invalid aggregate RECORD encoding") from exc
    if not lines or len(lines) > MAX_ROWS:
        deny("missing or oversized RECORD member list")
    seen = set()
    members = {}
    for line in lines:
        if len(line) != 3:
            deny("invalid aggregate RECORD field count")
        member, encoded, sizepart = line
        if member in seen:
            deny("duplicate aggregate RECORD member: " + member)
        seen.add(member)
        rel = _record_member(prefix, member, d["dist_info"])
        data = _read(root, rel)
        if member == record_name:
            if encoded or sizepart:
                deny("aggregate RECORD must be self-unhashed")
        else:
            if not encoded.startswith("sha256=") or not sizepart.isdecimal():
                deny("unhashed installed aggregate member: " + member)
            declared = encoded[7:]
            if (declared != base64.urlsafe_b64encode(bytes.fromhex(data["sha256"])).
                    decode().rstrip("=") or int(sizepart) != data["size"]):
                deny("aggregate RECORD does not match installed bytes: " + member)
        members[member] = {
            "path": rel, "sha256": data["sha256"], "size": data["size"],
            "mode": data["mode"], "uid": data["uid"], "gid": data["gid"],
        }
    if record_name not in members:
        deny("installed aggregate RECORD does not describe itself")
    return record, members


def inspect_installed(rootfs, *, pins=None, require_root_owned=False):
    """Produce unsigned, nonsecret byte evidence, never an installation grant."""
    pins = _check_selection(json.loads(PIN.read_text()) if pins is None else pins)
    root = Path(rootfs)
    if root.is_symlink() or not root.is_dir():
        deny("unavailable installed root")
    dist = pins["distribution"]
    prefix = dist["install_prefix"]
    dist_name = dist["dist_info"]
    record, members = _verify_record(root, pins)
    required = {p for component in pins["controllers"].values()
                for p in component["files"]}
    if not required <= set(members):
        deny("missing reviewed controller source module in aggregate RECORD")
    modules = {}
    for name, info in pins["controllers"].items():
        for installed, blob in info["files"].items():
            item = members[installed]
            module_file, _ = _file(root, item["path"])
            if _git_blob(module_file.read_bytes()) != blob["git_blob"]:
                deny("aggregate contains different pinned controller source: " + installed)
            expected_mode = int(blob["mode"][-3:], 8)
            if item["mode"] != expected_mode:
                deny("aggregate controller module mode differs: " + installed)
            modules[installed] = {"git_blob": blob["git_blob"],
                                  "sha256": item["sha256"],
                                  "mode": item["mode"]}
    metadata = _read(root, prefix + "/" + dist_name + "/METADATA", max_size=MAX_RECORD_BYTES)
    message = BytesParser().parsebytes(metadata["data"])
    if (message.get("Name", "").lower() != dist["name"]
            or message.get("Version", "") != dist["version"]):
        deny("aggregate METADATA Name/Version not selected")
    wheel = _read(root, prefix + "/" + dist_name + "/WHEEL", max_size=MAX_RECORD_BYTES)
    wheel_meta = BytesParser().parsebytes(wheel["data"])
    if wheel_meta.get("Root-Is-Purelib", "").lower() != "true":
        deny("aggregate wheel would use unreviewed platlib ABI")
    if wheel_meta.get_all("Tag") != ["py3-none-any"]:
        deny("aggregate wheel tag changed")
    entry = _read(root, prefix + "/" + dist_name + "/entry_points.txt", max_size=MAX_RECORD_BYTES)
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read_string(entry["data"].decode("utf-8"))
    except (ValueError, configparser.Error) as exc:
        raise AggregateHeld("invalid installed aggregate entry points") from exc
    if "console_scripts" not in config:
        deny("controller console scripts missing")
    for name, target in dist["required_entry_points"].items():
        if config["console_scripts"].get(name) != target:
            deny("aggregate selected controller CLI target differs: " + name)
        if "../../../bin/" + name not in members:
            deny("aggregate lacks installed controller CLI RECORD member: " + name)
        script = _read(root, "usr/bin/" + name, max_size=MAX_RECORD_BYTES)
        if not script["data"].startswith(b"#!/usr/bin/python3.12"):
            deny("controller launcher uses wrong Python runtime: " + name)
    if require_root_owned:
        if os.geteuid() != 0:
            deny("native ownership check requires root")
        if any(item["uid"] != 0 or item["gid"] != 0 for item in members.values()):
            deny("installed aggregate member not owned by root")
    return {
        "schema": "zog-resident-b-aggregate-installed-byte-observation-v1",
        "status": "INSTALLED_BYTES_AND_RECORD_COHERENT_UNACCEPTED",
        "distribution": {"name": "zog", "version": dist["version"],
                         "python": dist["python"], "RECORD_sha256": record["sha256"],
                         "RECORD_member_count": len(members)},
        "controller_source_pins": {
            name: {"revision": info["revision"], "archive_sha256": info["archive_sha256"]}
            for name, info in pins["controllers"].items()
        },
        "controller_modules": modules,
        "installed_members": members,
        "root_owned_bytes_verified": bool(require_root_owned),
        "generation_accepted": False,
        "source_authorized": False,
        "issuer_activation_authorized": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--box-source", type=Path, required=True)
    p.add_argument("--root-source", type=Path, required=True)
    p.add_argument("--rootfs", type=Path)
    p.add_argument("--require-root-ownership", action="store_true")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    sources = verify_sources(args.box_source, args.root_source)
    if args.rootfs is None:
        if args.require_root_ownership or args.output is not None:
            p.error("installed output and root ownership require --rootfs")
        print(json.dumps(sources, sort_keys=True))
        return
    evidence = inspect_installed(args.rootfs, require_root_owned=args.require_root_ownership)
    evidence["source_checkouts"] = sources
    text = json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        if args.output.exists() or args.output.is_symlink():
            deny("refuse to overwrite pre-existing native installed-byte evidence")
        args.output.write_text(text)


if __name__ == "__main__":
    main()

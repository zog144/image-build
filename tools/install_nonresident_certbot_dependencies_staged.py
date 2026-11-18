#!/usr/bin/env python3
"""Create-only, offline install of the 24 reviewed Python 3.12 dependencies.

All wheel-provided scripts and entry-point launchers are installed under
/usr/libexec/zog/python3.12/bin; libraries keep their standard /usr/lib
Python 3.12 site-packages layout. No live files are written until every
destination and every installed RECORD has passed preflight.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import stat
import sys

from verify_nonresident_certbot_dependency_wheelhouse import (
    DependencyHold, inventory as wheel_inventory, verify as verify_wheels,
)

SITE = "usr/lib/python3.12/site-packages"
SCRIPTS = "usr/libexec/zog/python3.12/bin"
ZOG_DIST_INFO = SITE + "/zog-0.1.1.dev20261117.dist-info"
ACCEPTED_ZOG_RECORD_SHA256 = (
    "8a4428184d096a1f24e68b394b6dcd26a23cf345fe59d7e74ce18c57493e6d30"
)
LOCK = (
    Path(__file__).resolve().parents[1]
    / "project/host/nonresident-certbot-python312-dependencies.lock"
)
SCHEMA = "zog-python312-dependency-staged-private-scripts-v1"
EXPECTED_DEPENDENCIES = 24
O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def hold(why):
    raise DependencyHold("private Python 3.12 dependency install HOLD: " + why)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _relative(name):
    if (type(name) is not str or not name or name.startswith("/")
            or "\\" in name or "\x00" in name or any(
                part in ("", ".", "..") for part in name.split("/")
            )):
        hold("unsafe filesystem member: " + str(name))
    return name


def _under(root, relative):
    return Path(root).joinpath(*_relative(relative).split("/"))


def _regular(path):
    try:
        info = path.lstat()
    except OSError as exc:
        raise DependencyHold("missing expected file: " + str(path)) from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        hold("missing or unsafe regular file: " + str(path))
    return info


def _staged_files(root):
    if root.is_symlink() or not root.is_dir():
        hold("staged root is not a real directory")
    contents = {}
    for parent, dirs, filenames in os.walk(root, followlinks=False):
        for name in dirs:
            entry = Path(parent) / name
            if entry.is_symlink() or not entry.is_dir():
                hold("symlink or special directory in staging: " + str(entry))
        for name in filenames:
            file = Path(parent) / name
            info = _regular(file)
            if stat.S_IMODE(info.st_mode) & 0o022:
                hold("staged member unexpectedly group/world writable: " + str(file))
            rel = file.relative_to(root).as_posix()
            _relative(rel)
            if not (rel.startswith(SITE + "/") or rel.startswith(SCRIPTS + "/")):
                hold("dependency attempted a non-Python/non-private-script output: " + rel)
            contents[rel] = {
                "sha256": digest(file.read_bytes()),
                "bytes": info.st_size,
                "mode": stat.S_IMODE(info.st_mode),
            }
    return contents


def _record_path(raw):
    """Resolve installed RECORD paths, including legitimate relative scripts.

    RECORD paths are relative to the dist-info directory's site root. The
    only accepted escape from site-packages is the reviewed private script
    directory, never /usr/bin or another unreviewed system path.
    """
    if type(raw) is not str or not raw or raw.startswith("/") or "\\" in raw:
        hold("unsafe installed RECORD member")
    if "\x00" in raw or any(part in ("", ".") for part in raw.split("/")):
        hold("noncanonical installed RECORD member")
    normal = posixpath.normpath(posixpath.join(SITE, raw))
    if not (normal.startswith(SITE + "/") or normal.startswith(SCRIPTS + "/")):
        hold("installed RECORD attempts outside selected Python paths: " + raw)
    return _relative(normal)


def verify_staged_records(root, wheels):
    """Require every file in all actual installer-generated RECORDs exactly once."""
    root = Path(root)
    all_members = _staged_files(root)
    records = set()
    scripts = {}
    seen = set()
    for wheel in wheels:
        name = wheel["name"].replace("-", "_")
        version = wheel["version"]
        record_rel = SITE + "/" + name + "-" + version + ".dist-info/RECORD"
        if record_rel not in all_members:
            hold("installer did not write a RECORD for " + wheel["name"])
        content = _under(root, record_rel).read_text(encoding="utf-8")
        rows = list(csv.reader(io.StringIO(content), strict=True))
        if not rows:
            hold("empty installed RECORD: " + record_rel)
        local_seen = set()
        for row in rows:
            if len(row) != 3:
                hold("installed RECORD has invalid columns: " + record_rel)
            raw, declared_hash, declared_size = row
            rel = _record_path(raw)
            if rel in local_seen or rel in seen:
                hold("two dependency wheels own the same staged destination: " + rel)
            local_seen.add(rel)
            seen.add(rel)
            if rel not in all_members:
                hold("installed RECORD points at a missing staged file: " + rel)
            data = all_members[rel]
            if rel == record_rel:
                if declared_hash != "" or declared_size != "":
                    hold("installed RECORD must be self-unhashed")
            else:
                expected = "sha256=" + base64.urlsafe_b64encode(
                    bytes.fromhex(data["sha256"])
                ).decode("ascii").rstrip("=")
                if declared_hash != expected or declared_size != str(data["bytes"]):
                    hold("installed RECORD does not match final file bytes: " + rel)
            if rel.startswith(SCRIPTS + "/"):
                scripts[rel] = {"owner": wheel["name"], **data}
                if raw != posixpath.relpath(rel, SITE):
                    hold("private script RECORD uses wrong actual final path: " + raw)
        if record_rel not in local_seen:
            hold("installer RECORD does not include itself: " + record_rel)
        records.add(record_rel)
    if seen != set(all_members):
        hold("installed RECORD did not enumerate every staged dependency file")
    return {
        "members": all_members,
        "record_paths": sorted(records),
        "scripts": scripts,
    }


def _scheme():
    return {
        "purelib": "/" + SITE,
        "platlib": "/" + SITE,
        "headers": "/usr/include/python3.12",
        "scripts": "/" + SCRIPTS,
        "data": "/usr",
    }


def stage(wheelhouse, workspace, *, lock=LOCK):
    """Install exact wheels into a new disposable root, not the real filesystem."""
    if sys.version_info[:2] != (3, 12):
        hold("installer must execute under Python 3.12")
    from importlib.metadata import version
    try:
        if version("installer") != "1.0.1":
            hold("unreviewed wheel installer version")
    except Exception as exc:
        if isinstance(exc, DependencyHold):
            raise
        hold("Python wheel installer 1.0.1 is not installed in staging environment")
    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile

    wheels = verify_wheels(wheelhouse, lock=lock)["distributions"]
    if len(wheels) != EXPECTED_DEPENDENCIES:
        hold("unexpected dependency wheel count")
    workspace = Path(workspace)
    if workspace.exists() or workspace.is_symlink():
        hold("refuse to overwrite an existing staging workspace")
    workspace.mkdir(parents=True, mode=0o700)
    if stat.S_IMODE(workspace.stat().st_mode) != 0o700:
        hold("staging workspace must be private mode 0700")
    staged = workspace / "root"
    staged.mkdir()
    destination = SchemeDictionaryDestination(
        scheme_dict=_scheme(), interpreter="/usr/bin/python3.12",
        script_kind="posix", bytecode_optimization_levels=(),
        destdir=str(staged), overwrite_existing=False,
    )
    for wheel in wheels:
        with WheelFile.open(str(Path(wheelhouse) / wheel["file"])) as source:
            if (source.distribution.replace("_", "-").lower() != wheel["name"]
                    or source.version != wheel["version"]):
                hold("wheel source name/version mismatch: " + wheel["file"])
            source.validate_record(validate_contents=True)
            install(source, destination, {})
    evidence = verify_staged_records(staged, wheels)
    return {
        "schema": SCHEMA,
        "status": "STAGED_NOT_INSTALLED",
        "root": staged,
        "wheels": wheels,
        **evidence,
    }


def _ancestor_preflight(live_root, relative):
    """Only inspect existing directories. Never create one during preflight."""
    root = Path(live_root)
    if root.is_symlink() or not root.is_dir():
        hold("live root missing or symlinked")
    parent = root
    missing = False
    for part in _relative(relative).split("/")[:-1]:
        parent = parent / part
        if missing:
            continue
        try:
            mode = parent.lstat().st_mode
        except FileNotFoundError:
            missing = True
            continue
        if not stat.S_ISDIR(mode):
            hold("non-directory or symlink in final destination ancestry: " + str(parent))
    return _under(root, relative)


def _inspect_zog(root, *, expected_sha, expected_count, expected_launchers):
    """Read existing aggregate RECORD and verify every installed member byte."""
    rec_rel = ZOG_DIST_INFO + "/RECORD"
    record = _ancestor_preflight(root, rec_rel)
    raw = record.read_bytes()
    if digest(raw) != expected_sha:
        hold("existing accepted zog RECORD digest changed")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8")), strict=True))
    if len(rows) != expected_count:
        hold("accepted zog RECORD entry count changed")
    launchers = {}
    for entry in rows:
        if len(entry) != 3:
            hold("invalid accepted zog RECORD")
        path, sha, size = entry
        if not path or path.startswith("/") or "\\" in path:
            hold("unsafe original zog RECORD path")
        rel = posixpath.normpath(posixpath.join(SITE, path))
        if not (rel.startswith(SITE + "/") or rel.startswith("usr/bin/")):
            hold("unreviewed accepted zog installation destination: " + rel)
        file = _ancestor_preflight(root, rel)
        _regular(file)
        data = file.read_bytes()
        if rel == rec_rel:
            if sha or size:
                hold("accepted zog RECORD self hash unexpectedly present")
        else:
            expected = "sha256=" + base64.urlsafe_b64encode(
                hashlib.sha256(data).digest()
            ).decode("ascii").rstrip("=")
            if sha != expected or size != str(len(data)):
                hold("accepted zog installed byte differs from its RECORD: " + rel)
        if rel.startswith("usr/bin/"):
            if not data.startswith(b"#!/usr/bin/python3.12"):
                hold("existing zog launcher interpreter changed: " + rel)
            launchers[rel] = digest(data)
    if len(launchers) != expected_launchers:
        hold("accepted zog launcher count changed")
    return {"record_sha256": expected_sha, "launchers": launchers}


def preflight(evidence, live_root, *, expected_zog_sha=None,
              expected_zog_count=509, expected_zog_launchers=16):
    """Validate *all* destinations before any live filesystem mutation."""
    staged = Path(evidence["root"])
    current = verify_staged_records(staged, evidence["wheels"])
    if current["members"] != evidence["members"] or current["scripts"] != evidence["scripts"]:
        hold("staged files/RECORD changed after staging")
    # The guarded original aggregate (when provided) remains independent.
    protected = None
    if expected_zog_sha is not None:
        protected = _inspect_zog(
            live_root, expected_sha=expected_zog_sha,
            expected_count=expected_zog_count,
            expected_launchers=expected_zog_launchers,
        )
    for rel in sorted(evidence["members"]):
        target = _ancestor_preflight(live_root, rel)
        try:
            target.lstat()
        except FileNotFoundError:
            continue
        hold("final destination collision (no live files changed): " + rel)
    return {
        "schema": SCHEMA,
        "status": "ALL_FINAL_DESTINATIONS_ABSENT",
        "files": len(evidence["members"]),
        "scripts": sorted(evidence["scripts"]),
        "private_script_directory": "/" + SCRIPTS,
        "protected": protected,
        "root": str(Path(live_root)),
        "live_files_written": 0,
    }


def _exclusive_write(root, rel, staged, expected):
    """Use dirfd + O_NOFOLLOW and O_EXCL to refuse late symlink/collision races."""
    names = _relative(rel).split("/")
    fd = os.open(root, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
    try:
        for name in names[:-1]:
            try:
                child = os.open(name, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(name, 0o755, dir_fd=fd)
                child = os.open(name, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        source = _under(staged, rel)
        info = _regular(source)
        if info.st_size != expected["bytes"] or digest(source.read_bytes()) != expected["sha256"]:
            hold("staged input changed before exclusive final file creation: " + rel)
        target_fd = os.open(
            names[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW,
            0o600, dir_fd=fd,
        )
        try:
            written = hashlib.sha256()
            size = 0
            with source.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    written.update(chunk)
                    view = memoryview(chunk)
                    while view:
                        count = os.write(target_fd, view)
                        view = view[count:]
            if size != expected["bytes"] or written.hexdigest() != expected["sha256"]:
                hold("staged input changed during exclusive final file creation: " + rel)
            os.fchmod(target_fd, stat.S_IMODE(info.st_mode))
            os.fsync(target_fd)
        finally:
            os.close(target_fd)
        os.fsync(fd)
    finally:
        os.close(fd)


def apply(evidence, live_root, *, expected_zog_sha=ACCEPTED_ZOG_RECORD_SHA256,
          expected_zog_count=509, expected_zog_launchers=16):
    """Create-only commit after full preflight, never an implicit pip upgrade.

    A power loss after commit starts may leave a partial new dependency install.
    Preserve the original staging workspace/receipt for explicit recovery.
    Never silently roll back or overwrite existing files.
    """
    if os.geteuid() != 0:
        hold("live dependency installation requires root")
    checked = preflight(
        evidence, live_root, expected_zog_sha=expected_zog_sha,
        expected_zog_count=expected_zog_count,
        expected_zog_launchers=expected_zog_launchers,
    )
    # Preflight evidence is durably retained in the *disposable* workspace
    # before any live installation file is created. An interrupted operation
    # keeps its exact staged inputs and durable intent for explicit recovery.
    operation = Path(evidence["root"]).parent
    intent = operation / "live-commit-preflight.json"
    if intent.exists() or intent.is_symlink():
        hold("refuse to overwrite existing staging operation intent")
    intent.write_text(json.dumps({
        "schema": SCHEMA, "status": "PREPARED_CREATE_ONLY",
        "live_root": str(Path(live_root)), "member_count": len(evidence["members"]),
        "members": evidence["members"], "protected": checked["protected"],
    }, indent=2, sort_keys=True) + "\n")
    with intent.open("rb") as stream:
        os.fsync(stream.fileno())
    completed = 0
    try:
        for rel in sorted(evidence["members"]):
            _exclusive_write(live_root, rel, evidence["root"], evidence["members"][rel])
            completed += 1
    except BaseException:
        # Never delete potentially accepted files or modify the old zog.
        # Owner must reconcile partial create-only transaction explicitly.
        hold("interrupted create-only install after " + str(completed) +
             " files; original workspace and installed evidence retained")
    after = preflight_existing(
        evidence, live_root, expected_zog_sha=expected_zog_sha,
        expected_zog_count=expected_zog_count,
        expected_zog_launchers=expected_zog_launchers,
    )
    receipt = operation / "live-commit-completed.json"
    receipt.write_text(json.dumps({
        "schema": SCHEMA, "status": "FILES_CREATED_NATIVE_READBACK_REQUIRED",
        "member_count": completed, "protected": after,
    }, indent=2, sort_keys=True) + "\n")
    with receipt.open("rb") as stream:
        os.fsync(stream.fileno())
    return {**checked, "status": "FILES_CREATED_NATIVE_READBACK_REQUIRED",
            "live_files_written": completed,
            "postinstallation": after}


def preflight_existing(evidence, live_root, *, expected_zog_sha,
                       expected_zog_count, expected_zog_launchers):
    """After a create-only install, confirm bytes and unchanged original zog."""
    before = verify_staged_records(Path(evidence["root"]), evidence["wheels"])
    for rel, item in before["members"].items():
        file = _ancestor_preflight(live_root, rel)
        if digest(file.read_bytes()) != item["sha256"]:
            hold("installed file changed from staged input: " + rel)
        if stat.S_IMODE(_regular(file).st_mode) != item["mode"]:
            hold("installed file mode changed from staged input: " + rel)
    return _inspect_zog(live_root, expected_sha=expected_zog_sha,
                        expected_count=expected_zog_count,
                        expected_launchers=expected_zog_launchers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true",
                        help="explicitly perform create-only live installation, root required")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.apply and args.live_root.resolve() != Path("/"):
        hold("native --apply requires the real root filesystem")
    result = stage(args.wheelhouse, args.workspace)
    if args.apply:
        final = apply(result, args.live_root)
    else:
        final = preflight(
            result, args.live_root,
            expected_zog_sha=(
                ACCEPTED_ZOG_RECORD_SHA256
                if args.live_root.resolve() == Path("/") else None
            ),
        )
    output = {
        "schema": SCHEMA, "status": final["status"],
        "distribution_count": len(result["wheels"]),
        "member_count": len(result["members"]),
        "relocated_script_paths": sorted(result["scripts"]),
        "live_files_written": final["live_files_written"],
        "original_zog_modified": False,
        "staged_record_paths": result["record_paths"],
    }
    if args.output:
        if args.output.exists() or args.output.is_symlink():
            hold("refuse to overwrite prior install evidence")
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

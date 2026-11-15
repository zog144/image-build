"""Bound offline resident account step for a new, unpublished Boot A rootfs.

Reuses host-install's independently reviewed resident_accounts.py source, never
a copied account implementation or a compiler-host account database. The
preparation, materialization and result files are all part of the producer's
durable operation; the final root inventory is frozen only after this step.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from .errors import ImageBuildError
from .filesystem import write_json
from .metadata import identity
from .staging_durability import inventory as staging_inventory, sync as staging_sync

CONTRACT = "image-build-resident-boot-accounts-v1"
SOURCE_COMMIT = "4fcccb441fec851530c412f619bc02699b8a87b1"
SOURCE_BLOB = "de9a161913959780a3097266d8936e0f7a1391b7"
SERVICE_SCHEMA = "zog-host-install-resident-service-accounts-v1"
BASE_CONTRACT = "zog-resident-minimal-root-account-base-v1"
BASE_PASSWD = b"root:x:0:0:root:/root:/bin/sh\n"
BASE_GROUP = b"root:x:0:\n"
ACCOUNT_FILES = frozenset({
    "etc/passwd", "etc/group", "etc/shadow", "etc/gshadow",
})
PREPARED = "resident-accounts-prepared.json"
RESULT = "resident-accounts-result.json"


def _hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_blob(path):
    content = Path(path).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(content)).encode() + b"\0" + content
    ).hexdigest()


def _regular(path, *, executable=False, root_owned=False):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ImageBuildError("resident account executable/source must be an absolute regular file")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
            (root_owned and (info.st_uid != 0 or info.st_mode & 0o022)) or
            (executable and not info.st_mode & 0o111)):
        raise ImageBuildError("unsafe offline resident account source/tool")
    return path


def source_binding(module, sysusers_executable):
    """The reviewed source blob is actually executed, not a mutable CLI wrapper."""
    module = _regular(Path(module).absolute())
    if _source_blob(module) != SOURCE_BLOB:
        raise ImageBuildError("host-install resident account source differs from reviewed PR43")
    sysusers = _regular(Path(sysusers_executable).absolute(),
                        executable=True, root_owned=True)
    if sysusers.name != "systemd-sysusers":
        raise ImageBuildError("offline resident account tool must be systemd-sysusers")
    return {
        "contract": CONTRACT,
        "host_install_commit": SOURCE_COMMIT,
        "host_install_module_git_blob": SOURCE_BLOB,
        "module": str(module),
        "sysusers_executable": str(sysusers),
        "sysusers_sha256": _hash(sysusers),
        "python_executable": str(Path(sys.executable).resolve()),
        "actions": ["inspect", "materialize", "verify"],
    }


def _check_source(binding):
    if source_binding(binding["module"], binding["sysusers_executable"]) != binding:
        raise ImageBuildError("offline account materializer source/executable changed")


def _account_command(action, root, binding):
    _check_source(binding)
    argv = [
        binding["python_executable"],
        binding["module"], "--" + action, "--root", str(root),
    ]
    if action == "materialize":
        argv += ["--sysusers-executable", binding["sysusers_executable"]]
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=90,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "SYSTEMD_OFFLINE": "1"},
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ImageBuildError("offline resident account action failed: " + action) from error
    if result.returncode:
        raise ImageBuildError(
            "offline resident account action refused: " + action +
            ": " + result.stderr[-1500:]
        )
    try:
        report = json.loads(result.stdout)
    except ValueError as error:
        raise ImageBuildError("offline resident account report is not JSON") from error
    if (not isinstance(report, dict) or report.get("schema") != SERVICE_SCHEMA
            or report.get("action") != action or report.get("rootfs") != str(root)
            or report.get("native_boot_accepted") is not False
            or report.get("generation_published") is not False
            or report.get("compiler_users_created") is not False
            or report.get("account_selection") is not False):
        raise ImageBuildError("offline resident account report contract differs")
    if action != "inspect" and report.get("materialized") is not True:
        raise ImageBuildError("offline resident accounts are not materialized")
    _check_source(binding)
    return report


def _db_state(root):
    records = []
    for item in ("etc/passwd", "etc/group"):
        path = root / item
        if path.is_symlink():
            raise ImageBuildError("linked resident account database refused")
        records.append(path.is_file())
    if records == [True, True]:
        return "retained"
    if records == [False, False]:
        if any((root / item).exists() for item in ("etc/shadow", "etc/gshadow")):
            raise ImageBuildError("missing account database with existing shadow files")
        return "minimal-root"
    raise ImageBuildError("partial resident base account database refused")


def _initialize_base(root, mode):
    if mode == "retained":
        if _db_state(root) != "retained":
            raise ImageBuildError("retained account database disappeared")
        return
    if mode != "minimal-root":
        raise ImageBuildError("unreviewed base account policy")
    etc = root / "etc"
    if etc.is_symlink() or (etc.exists() and not etc.is_dir()):
        raise ImageBuildError("resident etc directory is redirected")
    if not etc.exists():
        etc.mkdir(mode=0o755)
    for name, data in (("passwd", BASE_PASSWD), ("group", BASE_GROUP)):
        target = etc / name
        if target.is_symlink():
            raise ImageBuildError("resident base account file is redirected")
        if target.exists():
            if not target.is_file() or target.read_bytes() != data:
                raise ImageBuildError("interrupted minimal root account base differs")
        else:
            with target.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            target.chmod(0o644)
    staging_sync(root)


def _normalize_unpublished_shadow_modes(root):
    """Make newly generated mode-0000 shadow files owner-readable for hashing.

    The final published rootfs normalizes ownership to root; 0400 means only
    root can read the shadow database. This adjustment is limited to the two
    reviewed files of an unpublished private staging tree and never widens
    access to group/other. An existing readable mode is retained unchanged.
    """
    normalized = []
    for relative in ("etc/shadow", "etc/gshadow"):
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or stat.S_ISLNK(info.st_mode)):
            raise ImageBuildError("unsafe generated shadow database: " + relative)
        mode = stat.S_IMODE(info.st_mode)
        if mode == 0:
            if info.st_uid != os.geteuid():
                raise ImageBuildError(
                    "root-owned mode-0000 shadow requires root publication owner: " + relative
                )
            path.chmod(0o400)
            normalized.append(relative)
        elif not mode & 0o400:
            raise ImageBuildError("unreadable shadow mode requires separate review: " + relative)
    return normalized


def _delta(before, after, *, base_mode):
    """Only reviewed account DB files, plus a missing /etc directory, may vary."""
    previous = {row["path"]: row for row in before}
    current = {row["path"]: row for row in after}
    changes = {name for name in set(previous) | set(current)
               if previous.get(name) != current.get(name)}
    allowed = set(ACCOUNT_FILES)
    if base_mode == "minimal-root" and "etc" not in previous:
        allowed.add("etc")
    if not changes <= allowed:
        raise ImageBuildError(
            "resident account step changed unrelated composed bytes: " +
            ", ".join(sorted(changes - allowed)[:12])
        )
    for name in ("etc/passwd", "etc/group"):
        if current.get(name, {}).get("kind") != "file":
            raise ImageBuildError("resident account database is not an ordinary file")
    return sorted(changes)


def _prepared_record(root, composition, binding, base_mode):
    return {
        "schema": 1, "contract": CONTRACT,
        "overlay_plan_identity": "sha256:" + identity(composition),
        "overlay_expected_outputs": composition["expected_outputs"],
        "root": str(root), "source": binding,
        "base": {
            "contract": BASE_CONTRACT,
            "mode": base_mode,
            "minimal_passwd_sha256": hashlib.sha256(BASE_PASSWD).hexdigest(),
            "minimal_group_sha256": hashlib.sha256(BASE_GROUP).hexdigest(),
        },
    }


def _check_finished(root, work, composition, binding):
    prepared = json.loads((work / PREPARED).read_text())
    final = json.loads((work / RESULT).read_text())
    expected = _prepared_record(root, composition, binding, prepared["base"]["mode"])
    if prepared != expected:
        raise ImageBuildError("frozen resident account preparation differs")
    if (set(final) != {"schema", "contract", "preparation_identity", "source",
                       "materialization", "verification", "final_outputs", "delta"}
            or final["schema"] != 1 or final["contract"] != CONTRACT
            or final["preparation_identity"] != "sha256:" + identity(prepared)
            or final["source"] != binding):
        raise ImageBuildError("frozen account result differs")
    actual = staging_inventory(root)
    if final["final_outputs"] != actual:
        raise ImageBuildError("retained account-materialized root inventory changed")
    if final["delta"] != _delta(composition["expected_outputs"], actual,
                                base_mode=prepared["base"]["mode"]):
        raise ImageBuildError("frozen account delta differs")
    verified = _account_command("verify", root, binding)
    for key in ("vendor_declarations", "before"):
        if verified[key] != final["verification"][key]:
            raise ImageBuildError("offline resident account report changed")
    return final


def materialize(root, work, composition, binding):
    """Durable, retryable account operation on an unpublished assembled root.

    After an interruption, never recompose over unrecorded account edits. The
    frozen overlay inventory and restricted account-only delta provide recovery
    without silently replacing a previously published generation.
    """
    root, work = Path(root).absolute(), Path(work)
    if not root.is_dir() or root.is_symlink():
        raise ImageBuildError("resident account target must be unpublished staged root")
    _check_source(binding)
    prepared_path, result_path = work / PREPARED, work / RESULT
    if result_path.exists():
        if not prepared_path.is_file():
            raise ImageBuildError("resident account result lacks preparation")
        return _check_finished(root, work, composition, binding)
    if prepared_path.exists():
        prepared = json.loads(prepared_path.read_text())
        if (prepared.get("contract") != CONTRACT
                or prepared.get("base", {}).get("mode") not in ("retained", "minimal-root")
                or prepared != _prepared_record(
                    root, composition, binding, prepared["base"]["mode"]
                )):
            raise ImageBuildError("retained account preparation changed")
        base_mode = prepared["base"]["mode"]
        _normalize_unpublished_shadow_modes(root)
        _delta(composition["expected_outputs"], staging_inventory(root),
               base_mode=base_mode)
    else:
        if staging_inventory(root) != composition["expected_outputs"]:
            raise ImageBuildError("unprepared account root differs from package overlay")
        base_mode = _db_state(root)
        prepared = _prepared_record(root, composition, binding, base_mode)
        write_json(prepared_path, prepared)
    _initialize_base(root, base_mode)
    _delta(composition["expected_outputs"], staging_inventory(root),
           base_mode=base_mode)
    inspect = _account_command("inspect", root, binding)
    materialized = _account_command("materialize", root, binding)
    verified = _account_command("verify", root, binding)
    if (materialized["vendor_declarations"] != verified["vendor_declarations"]
            or not materialized["after"]["all_preexisting_records_preserved"]):
        raise ImageBuildError("resident account materializer did not preserve inputs")
    if (materialized["after"]["passwd_sha256"] !=
            verified["before"]["passwd_sha256"]
            or materialized["after"]["group_sha256"] !=
            verified["before"]["group_sha256"]):
        raise ImageBuildError("resident account database changed after materialization")
    _normalize_unpublished_shadow_modes(root)
    staging_sync(root)
    outputs = staging_inventory(root)
    delta = _delta(composition["expected_outputs"], outputs, base_mode=base_mode)
    result = {
        "schema": 1, "contract": CONTRACT,
        "preparation_identity": "sha256:" + identity(prepared),
        "source": binding, "materialization": materialized,
        "verification": verified, "final_outputs": outputs, "delta": delta,
    }
    write_json(result_path, result)
    return _check_finished(root, work, composition, binding)


def verify_materialized(root, work, composition, binding):
    if not (work / RESULT).is_file():
        raise ImageBuildError("offline resident account result was not durably recorded")
    return _check_finished(Path(root).absolute(), Path(work), composition, binding)

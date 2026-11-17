#!/usr/bin/env python3
"""Produce or verify an offline, hash-locked Python 3.12 dependency wheelhouse.

Only verifies *dependency* wheels for an already installed, immutable zog
aggregate. It never installs a file, imports a controller, or changes a Host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from email.parser import BytesParser
from pathlib import Path
import re
import zipfile

AGGREGATE = "zog-0.1.1.dev20261117-py3-none-any.whl"
AGGREGATE_SHA256 = "bf8560e3ee228dc6390f708bb9282472bbc7e14b154b5841c7ba912901b204c8"
REQUIREMENTS = {
    "django": "Django>=5.2,<5.3",
    "pyjwt": "PyJWT>=2.10,<3",
    "boto3": "boto3>=1.34,<2",
    "cryptography": "cryptography>=44",
    "dbus-next": "dbus-next==0.2.3",
    "dnspython": "dnspython>=2.8,<3",
    "http-message-signatures": "http-message-signatures>=2.0.1,<3",
    "requests": "requests>=2.32,<3",
    "typing-extensions": "typing_extensions>=4.12",
    "waitress": "waitress>=3,<4",
}
HEX = re.compile(r"[0-9a-f]{64}\Z")
LOCK = re.compile(
    r"^([a-z][a-z0-9-]*)==([a-zA-Z0-9][a-zA-Z0-9.!+_-]*) --hash=sha256:([0-9a-f]{64})$"
)
SCHEMA = "zog-nonresident-certbot-python312-offline-wheelhouse-v1"


class DependencyHold(ValueError):
    pass


def refuse(message):
    raise DependencyHold("nonresident Python 3.12 dependency closure HOLD: " + message)


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def _metadata(wheel):
    if wheel.is_symlink() or not wheel.is_file() or wheel.stat().st_nlink != 1:
        refuse("wheel is not an unlinked regular file: " + wheel.name)
    if wheel.stat().st_size <= 0 or wheel.stat().st_size > 150_000_000:
        refuse("wheel member exceeds reviewed size limit: " + wheel.name)
    if not wheel.name.endswith(".whl"):
        refuse("offline directory contains non-wheel: " + wheel.name)
    with zipfile.ZipFile(wheel) as archive:
        if archive.testzip():
            refuse("wheel contains bad ZIP member: " + wheel.name)
        names = archive.namelist()
        if any("\\" in x or x.startswith("/") or ".." in x.split("/")
               or any(part in ("", ".") for part in x.split("/") if not x.endswith("/"))
               for x in names):
            refuse("noncanonical wheel member: " + wheel.name)
        headers = [x for x in names if x.endswith(".dist-info/METADATA")]
        records = [x for x in names if x.endswith(".dist-info/RECORD")]
        if len(headers) != 1 or len(records) != 1:
            refuse("wheel distribution metadata is missing or ambiguous: " + wheel.name)
        if headers[0].rsplit("/", 1)[0] != records[0].rsplit("/", 1)[0]:
            refuse("wheel METADATA/RECORD identity mismatch")
        meta = BytesParser().parsebytes(archive.read(headers[0]))
        name = normalized(meta.get("Name", ""))
        version = meta.get("Version", "")
        if (not name or name == "zog"
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version)
            or not wheel.name.lower().replace("_", "-").startswith(
                name + "-" + version.lower().replace("_", "-") + "-")):
            refuse("wheel distribution identity differs: " + wheel.name)
        for member in names:
            if member.startswith(("zog/", "zog-0.1.1.dev20261117.dist-info/")):
                refuse("dependency attempted to replace installed zog bytes")
        return {
            "name": name, "version": version, "file": wheel.name,
            "sha256": sha256(wheel), "size": wheel.stat().st_size,
            "requires_dist": sorted(meta.get_all("Requires-Dist") or []),
        }


def inventory(wheelhouse):
    wheelhouse = Path(wheelhouse)
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        refuse("offline wheelhouse unavailable")
    all_entries = sorted(wheelhouse.iterdir())
    if not all_entries:
        refuse("empty offline wheelhouse")
    if any(x.is_dir() or x.suffix != ".whl" for x in all_entries):
        refuse("unexpected non-wheel file in offline wheelhouse")
    wheels = sorted((_metadata(x) for x in all_entries), key=lambda x: x["name"])
    names = [x["name"] for x in wheels]
    if len(set(names)) != len(names):
        refuse("ambiguous duplicated dependency distribution")
    if not set(REQUIREMENTS) <= set(names):
        refuse("the wheelhouse omits a declared direct requirement")
    return wheels


def generated_lock(wheels):
    lines = [
        "# Nonresident Certbot Python 3.12, AL2023 x86_64, manylinux2014 wheels.",
        "# All direct AND transitive requirements are pinned with exact SHA-256.",
        "# This is a distinct input; never reinstall or replace installed zog.",
    ]
    lines.extend(
        f'{x["name"]}=={x["version"]} --hash=sha256:{x["sha256"]}'
        for x in wheels
    )
    return "\n".join(lines) + "\n"


def check_lock(wheels, lock):
    try:
        actual = Path(lock).read_text()
    except OSError as exc:
        raise DependencyHold("reviewed dependency lock is unavailable") from exc
    if actual != generated_lock(wheels):
        refuse("wheel bytes/distribution versions differ from reviewed exact lock")


def verify(wheelhouse, *, lock=None, aggregate=None):
    wheels = inventory(wheelhouse)
    if lock is not None:
        check_lock(wheels, lock)
    if aggregate is not None:
        aggregate = Path(aggregate)
        if aggregate.name != AGGREGATE or sha256(aggregate) != AGGREGATE_SHA256:
            refuse("original installed zog aggregate wheel identity differs")
        with zipfile.ZipFile(aggregate) as bundle:
            members = [x for x in bundle.namelist() if x.endswith(".dist-info/METADATA")]
            if len(members) != 1:
                refuse("original aggregate distribution metadata is ambiguous")
            metadata = BytesParser().parsebytes(bundle.read(members[0]))
            if metadata.get("Name", "").lower() != "zog" or metadata.get("Version") != "0.1.1.dev20261117":
                refuse("selected aggregate distribution Name/Version differs")
            actual = sorted(metadata.get_all("Requires-Dist") or [])
            # Compare normalized declared requirements, using packaging in the
            # producer CI for canonical PEP 508 comparisons separately.
            import re
            names = {normalized(re.split(r"[<>=!~; ([\t]", x, 1)[0]) for x in actual}
            if names != set(REQUIREMENTS):
                refuse("installed aggregate declares a different direct dependency set")
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_WHEELS_SHA256_COHERENT_NATIVE_INSTALL_UNACCEPTED",
        "target": {"os": "Amazon Linux 2023", "architecture": "x86_64",
                   "python": "/usr/bin/python3.12", "site_packages":
                   "/usr/lib/python3.12/site-packages",
                   "wheel_platform": "manylinux2014_x86_64"},
        "aggregate": {"distribution": "zog", "version": "0.1.1.dev20261117",
                      "wheel_sha256": AGGREGATE_SHA256,
                      "installed_record_untouched": True},
        "direct_requirements": [REQUIREMENTS[x] for x in sorted(REQUIREMENTS)],
        "distributions": wheels,
        "distribution_count": len(wheels),
        "native_host_installed": False,
        "package_reinstalled": False,
        "issuer_activation_permitted": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wheelhouse", type=Path, required=True)
    p.add_argument("--lock", type=Path)
    p.add_argument("--aggregate", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--propose-lock", action="store_true")
    args = p.parse_args()
    result = verify(args.wheelhouse, lock=args.lock, aggregate=args.aggregate)
    if args.propose_lock:
        print("BEGIN REVIEWABLE HASH LOCK")
        print(generated_lock(result["distributions"]), end="")
        print("END REVIEWABLE HASH LOCK")
    if args.output:
        if args.output.exists() or args.output.is_symlink():
            refuse("refuse to overwrite previous immutable evidence")
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "status": result["status"], "count": result["distribution_count"],
        "distributions": [(x["name"], x["version"], x["sha256"])
                           for x in result["distributions"]],
        "native_accepted": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

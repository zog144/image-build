#!/usr/bin/env python3
"""Inspect exact xcb cursor-closure source archives; source-only, not native admission."""
import argparse
import hashlib
import io
import json
import tarfile
import urllib.request

SOURCES = {
    "xcb-util-renderutil": {
        "version": "0.3.10",
        "url": "https://xorg.freedesktop.org/archive/individual/lib/xcb-util-renderutil-0.3.10.tar.xz",
        "sha256": "3e15d4f0e22d8ddbfbb9f5d77db43eacd7a304029bf25a6166cc63caa96d04ba",
    },
    "xcb-util-cursor": {
        "version": "0.1.6",
        "url": "https://xorg.freedesktop.org/archive/individual/lib/xcb-util-cursor-0.1.6.tar.xz",
        "sha256": "fdeb8bd127873519be5cc70dcd0d3b5d33b667877200f9925a59fdcad8f7a933",
    },
}
MAX_DOWNLOAD = 8 * 1024 * 1024
MAX_MEMBER = 2 * 1024 * 1024


def inspect(name, data):
    spec = SOURCES[name]
    actual = hashlib.sha256(data).hexdigest()
    if actual != spec["sha256"]:
        raise ValueError("upstream archive digest mismatch: " + name)
    root = name + "-" + spec["version"] + "/"
    members = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as archive:
        for member in archive.getmembers():
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise ValueError("path traversal in archive")
            if member.name in (root + "COPYING", root + "configure.ac", root + "Makefile.am"):
                if not member.isfile() or member.size > MAX_MEMBER:
                    raise ValueError("unsafe source metadata member")
                member_file = archive.extractfile(member)
                if member_file is None:
                    raise ValueError("unreadable source metadata member")
                members[member.name[len(root):]] = hashlib.sha256(member_file.read()).hexdigest()
    if "COPYING" not in members or "configure.ac" not in members:
        raise ValueError("original source notice / configure metadata missing")
    return {"project": name, "version": spec["version"],
            "original_archive_sha256": actual, "members": members,
            "status": "original-archive-content-observed-not-redistribution-approved"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", required=True)
    args = parser.parse_args()
    for name, spec in SOURCES.items():
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "Zog-source-evidence/1"})
        with urllib.request.urlopen(request, timeout=90) as stream:
            data = stream.read(MAX_DOWNLOAD + 1)
        if len(data) > MAX_DOWNLOAD:
            raise ValueError("archive exceeds bounded inspection allowance")
        print(json.dumps(inspect(name, data), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

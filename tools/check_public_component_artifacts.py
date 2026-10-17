#!/usr/bin/env python3
"""Validate public component wheel/sdist contents before any publication.

Run only after build artifacts are produced from the exact reviewed public
image-build source tree. Never uploads anything or executes archive members.
This check is about source/package privacy and complete first-party notice
delivery, not target-rootfs or bundled third-party binary authorization.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import zipfile

REQUIRED_NOTICE_SUFFIXES = (
    "LICENSE", "LICENSES/BSD-3-Clause.txt",
    "LICENSES/GPL-3.0-only.txt", "THIRD-PARTY-NOTICES.md"
)
REQUIRED_PACKAGE_SUFFIX = "zog/image_build/__init__.py"
BAD_PATTERNS = {
    "private_github_link": re.compile(rb"zog144/(?:know-file|[\w-]+-old)\b"),
    "old_private_grant": re.compile(rb"LicenseRef-Zog-" rb"Private|"
                                    rb"private development" rb" material|"
                                    rb"Private :: Do Not" rb" Upload", re.I),
    "cross_repo_secret": re.compile(rb"ZOG_CROSS_REPO_" rb"READ_TOKEN"),
    "bad_double_namespace": re.compile(rb"zog\.zog\.image_build"),
}
SCANNABLE = {".py", ".txt", ".md", ".toml", ".json", ".yaml", ".yml", ".sh"}

def safe_path(name):
    p = PurePosixPath(name)
    return bool(name and not p.is_absolute()
                and all(part not in ("", ".", "..") for part in p.parts))

def inspect_member(name, data, failures, archive):
    if not safe_path(name):
        failures.append(f"{archive}: unsafe path")
        return
    if name.endswith((".so", ".a", ".o", ".dll", ".dylib")):
        failures.append(f"{archive}: unexpected compiled binary {name}")
    if PurePosixPath(name).suffix in SCANNABLE:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(f"{archive}: non-UTF8 source member {name}")
            return
        for label, pattern in BAD_PATTERNS.items():
            if pattern.search(data):
                failures.append(f"{archive}: {label} at {name}")

def scan_archive(path, wheel):
    failures, names = [], {}
    if wheel:
        with zipfile.ZipFile(path) as z:
            for item in z.infolist():
                if item.is_dir():
                    continue
                if item.file_size > 20_000_000:
                    failures.append(f"{path.name}: oversize member {item.filename}")
                    continue
                if item.filename in names:
                    failures.append(f"{path.name}: duplicate {item.filename}")
                    continue
                data = z.read(item)
                names[item.filename] = data
                inspect_member(item.filename, data, failures, path.name)
    else:
        with tarfile.open(path, "r:gz") as t:
            for item in t:
                if item.isdir():
                    continue
                if not item.isfile():
                    failures.append(f"{path.name}: nonregular member {item.name}")
                    continue
                if item.size > 20_000_000:
                    failures.append(f"{path.name}: oversize member {item.name}")
                    continue
                if item.name in names:
                    failures.append(f"{path.name}: duplicate {item.name}")
                    continue
                data = t.extractfile(item).read()
                names[item.name] = data
                inspect_member(item.name, data, failures, path.name)
    rels = list(names)
    if not any(n.endswith(REQUIRED_PACKAGE_SUFFIX) for n in rels):
        failures.append(f"{path.name}: missing component namespace package")
    if any(n.endswith("/src/zog/__init__.py") or n == "zog/__init__.py"
           or n.endswith("/zog/__init__.py") for n in rels):
        failures.append(f"{path.name}: top-level zog/__init__.py belongs to release-build")
    notice_files = {}
    for suffix in REQUIRED_NOTICE_SUFFIXES:
        matches = [(n, d) for n, d in names.items()
                   if n == suffix or n.endswith("/" + suffix)]
        if not matches:
            failures.append(f"{path.name}: missing notice {suffix}")
        else:
            notice_files[suffix] = len(matches)
    return {"name": path.name, "members": len(names),
            "notice_matches": notice_files, "errors": failures}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    args = p.parse_args()
    wheels = sorted(args.directory.glob("*.whl"))
    sdists = sorted(args.directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        print("Expected exactly one wheel and one sdist", file=sys.stderr)
        return 1
    results = [scan_archive(wheels[0], True), scan_archive(sdists[0], False)]
    print(json.dumps(results, sort_keys=True, indent=2))
    return 1 if any(x["errors"] for x in results) else 0

if __name__ == "__main__":
    sys.exit(main())

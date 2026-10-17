"""Immutable certify-manage application software producer.

This module does not resolve dependencies or access the network.  A caller supplies a
complete reviewed runtime lock, installs only those exact inputs into the durable
ApplicationSoftwareStore staging root, then asks this producer to validate and
publish the immutable artifact/view/controller binding.
"""
from __future__ import annotations

import argparse
import email.parser
import hashlib
import json
import os
import re
from pathlib import Path

from .application_software import (
    ApplicationSoftwareStore,
    compatibility,
)
from .application_views import ApplicationSoftwareViewStore
from .errors import ImageBuildError
from .filesystem import inventory

APPLICATION = "certify-manage"
LOCK_CONTRACT = "image-build-certify-manage-runtime-lock-v1"
RESULT_CONTRACT = "image-build-certify-manage-software-result-v1"
VIEW_ROOT = "/applications/certify-manage"
PYTHON = VIEW_ROOT + "/bin/python3"
CERTBOT = VIEW_ROOT + "/bin/certbot"
SITE = "lib/python3.15/site-packages"
PYTHON_VERSION = "3.15.0rc2"

CORE = {
    "certify-manage": "0.1.0",
    "certbot": "5.8.0",
    "acme": "5.8.0",
    "configargparse": "1.7.5",
    "configobj": "5.0.9",
    "cryptography": "50.0.2",
    "distro": "1.9.0",
    "josepy": "2.2.0",
    "parsedatetime": "2.6",
    "pyrfc3339": "2.1.0",
    "pyopenssl": "26.4.0",
    "requests": "2.34.2",
    "certifi": "2026.7.22",
    "charset-normalizer": "3.4.9",
    "idna": "3.18",
    "urllib3": "2.7.0",
    "typing-extensions": "4.16.0",
}
CLOUDFLARE = {
    "certbot-dns-cloudflare": "5.8.0",
    "cloudflare": "5.6.0",
    "anyio": "4.14.2",
    "httpx": "0.28.1",
    "httpcore": "1.0.9",
    "h11": "0.16.0",
    "pydantic": "2.13.4",
    "pydantic-core": "2.46.4",
    "annotated-types": "0.8.0",
    "sniffio": "1.3.1",
    "typing-inspection": "0.4.2",
}
PROFILES = {
    "http-01": CORE,
    "cloudflare-dns-01": {**CORE, **CLOUDFLARE},
}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_DIST = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")

PYTHON_WRAPPER = """#!/bin/sh
exec /usr/bin/python3 -I -S /applications/certify-manage/libexec/python-launcher.py "$@"
"""
PYTHON_LAUNCHER = """# Immutable certify-manage Python path gate.
import runpy
import sys
import sysconfig

site = "/applications/certify-manage/lib/python3.15/site-packages"
paths = sysconfig.get_paths()
stdlib = paths["stdlib"]
platstdlib = paths.get("platstdlib", stdlib)
allowed = []
for value in (site, stdlib, platstdlib):
    if value not in allowed:
        allowed.append(value)
sys.path[:] = allowed

args = sys.argv[1:]
if len(args) >= 2 and args[0] == "-m":
    sys.argv = [args[1], *args[2:]]
    runpy.run_module(args[1], run_name="__main__", alter_sys=True)
elif len(args) >= 2 and args[0] == "-c":
    sys.argv = ["-c", *args[2:]]
    exec(compile(args[1], "<certify-manage -c>", "exec"), {"__name__": "__main__"})
elif args and not args[0].startswith("-"):
    sys.argv = args
    runpy.run_path(args[0], run_name="__main__")
else:
    raise SystemExit("immutable certify-manage Python requires -m, -c, or a script")
"""
CERTBOT_SCRIPT = """#!/applications/certify-manage/bin/python3
from certbot.main import main
if __name__ == "__main__":
    raise SystemExit(main())
"""


def _normalized(value):
    if not isinstance(value, str):
        raise ImageBuildError("invalid certify-manage distribution name")
    value = re.sub(r"[-_.]+", "-", value).lower()
    if not _DIST.fullmatch(value):
        raise ImageBuildError("invalid certify-manage distribution name")
    return value


def _load(value):
    if isinstance(value, (str, os.PathLike, Path)):
        try:
            value = json.loads(Path(value).read_text())
        except (OSError, ValueError, TypeError) as error:
            raise ImageBuildError("invalid certify-manage runtime lock") from error
    return value


def validate_lock(value):
    value = _load(value)
    if not isinstance(value, dict) or set(value) != {
        "contract", "profile", "certify_manage_revision", "compatibility", "packages"
    }:
        raise ImageBuildError("invalid certify-manage runtime lock")
    if value["contract"] != LOCK_CONTRACT or value["profile"] not in PROFILES:
        raise ImageBuildError("unsupported certify-manage runtime lock")
    revision = value["certify_manage_revision"]
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise ImageBuildError("exact certify-manage revision required")
    required = compatibility(value["compatibility"])
    python = required["python"]
    if (
        not python
        or python["implementation"] != "cpython"
        or python["version"] != PYTHON_VERSION
        or not python["soabi"].startswith("cpython-315-")
    ):
        raise ImageBuildError("certify-manage requires reviewed CPython 3.15 ABI")
    if required != value["compatibility"]:
        raise ImageBuildError("certify-manage compatibility descriptor is not canonical")

    packages = value["packages"]
    if not isinstance(packages, list):
        raise ImageBuildError("certify-manage packages must be a list")
    expected = PROFILES[value["profile"]]
    seen = {}
    notices = set()
    sources = []
    canonical_packages = []
    for record in packages:
        if not isinstance(record, dict) or set(record) != {
            "name", "version", "source", "notices"
        }:
            raise ImageBuildError("invalid certify-manage package record")
        name = _normalized(record["name"])
        if name in seen:
            raise ImageBuildError("duplicate certify-manage package")
        if name not in expected or record["version"] != expected[name]:
            raise ImageBuildError("unexpected certify-manage package version: " + name)
        source = record["source"]
        if (
            not isinstance(source, dict)
            or set(source) != {"url", "sha256"}
            or not isinstance(source["url"], str)
            or not source["url"].startswith("https://")
            or not isinstance(source["sha256"], str)
            or not _SHA.fullmatch(source["sha256"])
        ):
            raise ImageBuildError("invalid certify-manage source identity: " + name)
        package_notices = record["notices"]
        if (
            not isinstance(package_notices, list)
            or not package_notices
            or package_notices != sorted(set(package_notices))
            or any(
                not isinstance(path, str)
                or not path.startswith("share/licenses/")
                or path.startswith("/")
                or ".." in Path(path).parts
                for path in package_notices
            )
        ):
            raise ImageBuildError("invalid certify-manage notice paths: " + name)
        for path in package_notices:
            if path in notices:
                raise ImageBuildError("duplicate certify-manage notice destination")
            notices.add(path)
        seen[name] = record["version"]
        sources.append({"name": name, **source})
        canonical_packages.append({
            "name": name,
            "version": record["version"],
            "source": dict(source),
            "notices": list(package_notices),
        })
    if seen != expected:
        missing = sorted(set(expected) - set(seen))
        extra = sorted(set(seen) - set(expected))
        raise ImageBuildError(
            "incomplete certify-manage dependency closure: "
            + "missing=" + ",".join(missing)
            + " extra=" + ",".join(extra)
        )
    canonical_packages.sort(key=lambda item: item["name"])
    return {
        "contract": LOCK_CONTRACT,
        "profile": value["profile"],
        "certify_manage_revision": revision,
        "compatibility": required,
        "packages": canonical_packages,
        "sources": sorted(sources, key=lambda item: item["name"]),
        "notices": sorted(notices),
    }


def lock_digest(value):
    lock = validate_lock(value)
    payload = {
        key: lock[key]
        for key in ("contract", "profile", "certify_manage_revision", "compatibility", "packages")
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def begin(state_dir, operation, runtime_lock):
    lock = validate_lock(runtime_lock)
    store = ApplicationSoftwareStore(state_dir)
    return store.begin(
        operation,
        application=APPLICATION,
        revision="git:" + lock["certify_manage_revision"],
        sources=lock["sources"],
        compatibility_requirements=lock["compatibility"],
        notices=lock["notices"],
        provenance={
            "contract": LOCK_CONTRACT,
            "profile": lock["profile"],
            "runtime_lock_digest": lock_digest(runtime_lock),
            "python_executable": PYTHON,
            "certbot_executable": CERTBOT,
            "python_isolation": "-I -S fixed immutable site-packages",
            "package_versions": {
                item["name"]: item["version"] for item in lock["packages"]
            },
        },
    )


def materialize_launchers(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ImageBuildError("certify-manage staging root is unavailable")
    for directory in ("bin", "libexec"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    values = {
        root / "bin/python3": PYTHON_WRAPPER,
        root / "libexec/python-launcher.py": PYTHON_LAUNCHER,
        root / "bin/certbot": CERTBOT_SCRIPT,
    }
    for path, content in values.items():
        if path.is_symlink():
            raise ImageBuildError("certify-manage launcher path is a symlink")
        path.write_text(content)
        path.chmod(0o755)
    return root


def _metadata(site):
    parser = email.parser.Parser()
    result = {}
    for path in sorted(site.glob("*.dist-info/METADATA")):
        if path.is_symlink() or not path.is_file():
            raise ImageBuildError("invalid certify-manage distribution metadata")
        metadata = parser.parsestr(path.read_text(errors="strict"))
        name = _normalized(metadata.get("Name"))
        version = metadata.get("Version")
        if not version or name in result:
            raise ImageBuildError("ambiguous certify-manage installed distribution")
        result[name] = version
    return result


def _require_any(site, *paths):
    if not any((site / path).is_file() and not (site / path).is_symlink() for path in paths):
        raise ImageBuildError("missing certify-manage installed module: " + paths[0])


def verify_staging(root, runtime_lock):
    lock = validate_lock(runtime_lock)
    root = Path(root)
    records = inventory(root)
    allowed = {"bin", "lib", "lib64", "libexec", "share"}
    for record in records:
        top = record["path"].split("/", 1)[0]
        if top not in allowed:
            raise ImageBuildError("certify-manage staging contains mutable/runtime path: " + record["path"])
    forbidden = {
        "policy.json", "cloudflare.ini", "privkey.pem", "cert.pem", "fullchain.pem",
        "renewal.conf", "issuer.lock",
    }
    for record in records:
        if Path(record["path"]).name.lower() in forbidden:
            raise ImageBuildError("certify-manage staging contains mutable/secret material")
    expected_files = {
        "bin/python3": PYTHON_WRAPPER,
        "libexec/python-launcher.py": PYTHON_LAUNCHER,
        "bin/certbot": CERTBOT_SCRIPT,
    }
    for relative, content in expected_files.items():
        path = root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or path.read_text() != content
            or path.stat().st_mode & 0o7777 != 0o755
        ):
            raise ImageBuildError("certify-manage immutable launcher changed: " + relative)

    site = root / SITE
    if site.is_symlink() or not site.is_dir():
        raise ImageBuildError("certify-manage site-packages is missing")
    installed = _metadata(site)
    expected = {item["name"]: item["version"] for item in lock["packages"]}
    if installed != expected:
        raise ImageBuildError("certify-manage installed dependency closure differs")

    _require_any(site, "zog/certify_manage/__init__.py")
    _require_any(site, "certbot/__init__.py")
    _require_any(site, "acme/__init__.py")
    _require_any(site, "cryptography/__init__.py")
    _require_any(site, "configobj/__init__.py", "configobj.py")
    _require_any(site, "certifi/cacert.pem")
    if not list(site.glob("cryptography/hazmat/bindings/_rust*.so")):
        raise ImageBuildError("certify-manage cryptography native extension is missing")
    if lock["profile"] == "cloudflare-dns-01":
        _require_any(site, "certbot_dns_cloudflare/__init__.py")
        _require_any(site, "cloudflare/__init__.py")
        if not list(site.glob("pydantic_core/_pydantic_core*.so")):
            raise ImageBuildError("certify-manage pydantic-core native extension is missing")
    else:
        for name in ("certbot_dns_cloudflare", "cloudflare"):
            if (site / name).exists():
                raise ImageBuildError("HTTP-only certify-manage profile contains Cloudflare plugin")

    files = {record["path"] for record in records if record["kind"] == "file"}
    for notice in lock["notices"]:
        if notice not in files:
            raise ImageBuildError("certify-manage retained notice is missing: " + notice)
    return lock


def finalize(state_dir, operation, runtime_lock, rootfs_compatibility):
    lock = validate_lock(runtime_lock)
    store = ApplicationSoftwareStore(state_dir)
    operation_path = store.root / "operations" / operation
    if (operation_path / "result.json").exists():
        artifact = store.finalize(operation)
        verify_staging(artifact.root, runtime_lock)
    else:
        verify_staging(operation_path / "root", runtime_lock)
        artifact = store.finalize(operation)
    views = ApplicationSoftwareViewStore(state_dir)
    view = views.publish(
        operation + "-view",
        application=APPLICATION,
        artifacts=[artifact.artifact],
        profile="application",
    )
    binding = views.consumer_manifest(view.view, rootfs_compatibility)
    if binding["mount_point"] != VIEW_ROOT or binding["objects"][0]["artifact"] != artifact.artifact:
        raise ImageBuildError("certify-manage consumer binding differs")
    result = {
        "contract": RESULT_CONTRACT,
        "profile": lock["profile"],
        "runtime_lock_digest": lock_digest(runtime_lock),
        "artifact": artifact.artifact,
        "view": view.view,
        "binding": binding,
        "commands": {
            "python": PYTHON,
            "certbot": CERTBOT,
        },
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("begin")
    start.add_argument("operation")
    start.add_argument("lock", type=Path)
    launchers = sub.add_parser("materialize-launchers")
    launchers.add_argument("root", type=Path)
    check = sub.add_parser("verify")
    check.add_argument("root", type=Path)
    check.add_argument("lock", type=Path)
    finish = sub.add_parser("finalize")
    finish.add_argument("operation")
    finish.add_argument("lock", type=Path)
    finish.add_argument("rootfs", type=Path)
    args = parser.parse_args()
    if args.command == "begin":
        value = begin(args.state_dir, args.operation, args.lock)
        result = {"operation": value.operation, "root": str(value.root), "frozen": value.frozen, "artifact": value.artifact}
    elif args.command == "materialize-launchers":
        result = {"root": str(materialize_launchers(args.root))}
    elif args.command == "verify":
        result = verify_staging(args.root, args.lock)
    else:
        result = finalize(
            args.state_dir,
            args.operation,
            args.lock,
            json.loads(args.rootfs.read_text()),
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

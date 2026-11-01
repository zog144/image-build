#!/usr/bin/env python3
"""Check the protected Zog-installed Mesa build-toolchain closure.

Requires a root-protected receipt issued and bound by the native controller.
This file *does not* authenticate a receipt itself. A source-CI pass alone never
constitutes a Host software provenance or license admission pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

TOOLS = ("python", "cmake", "ninja", "meson", "pkgconf", "llvm-config")
MODULES = ("setuptools", "packaging", "wheel", "installer", "markupsafe", "mako", "yaml")
PC = ("x11", "xext", "x11-xcb", "xcb", "xcb-randr", "xcb-glx", "xcb-shm",
      "xcb-dri3", "xcb-present", "xcb-sync", "xcb-xfixes", "xshmfence",
      "xxf86vm", "libdrm", "expat", "zlib")


class IsolationError(RuntimeError):
    pass


def inside(path, roots):
    real = Path(path).resolve(strict=True)
    return any(real == root or root in real.parents for root in roots)


def roots_for(data):
    if data.get("schema") != "zog-mesa-native-tool-receipt-v1":
        raise IsolationError("missing installed-source receipt schema")
    if data.get("authority") != "root-control-protected-installed-bytes":
        raise IsolationError("unverified native authority")
    roots = tuple(Path(x).resolve(strict=True) for x in data["allowed_roots"])
    if not roots or any(r == Path("/") or not r.is_dir() for r in roots):
        raise IsolationError("invalid protected software roots")
    return roots


def check_files(data):
    roots = roots_for(data)
    if set(data["tools"]) != set(TOOLS):
        raise IsolationError("incomplete executable closure")
    if set(data["imports"]) != set(MODULES):
        raise IsolationError("incomplete Python import closure")
    if not data["pkgconfig_dirs"]:
        raise IsolationError("missing pkgconf search roots")
    for d in data["pkgconfig_dirs"]:
        if not inside(d, roots):
            raise IsolationError("Host pkgconfig directory")
    if not inside(data["sysroot"], roots):
        raise IsolationError("Host sysroot")
    for name, info in data["tools"].items():
        digest = info["sha256"]
        if len(digest) != 64 or any(x not in "0123456789abcdef" for x in digest):
            raise IsolationError("invalid executable digest: " + name)
        if not inside(info["path"], roots):
            raise IsolationError("Host executable: " + name)
        if not Path(info["path"]).is_file():
            raise IsolationError("missing tool: " + name)
        if hashlib.sha256(Path(info["path"]).read_bytes()).hexdigest() != digest:
            raise IsolationError("wrong installed tool bytes: " + name)
    for name, paths in data["imports"].items():
        if not paths or any(not inside(path, roots) for path in paths):
            raise IsolationError("Host module origin allowance: " + name)
    return roots


def check_environment(data, env):
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE",
                 "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "CMAKE_PREFIX_PATH",
                 "CMAKE_MODULE_PATH", "LD_LIBRARY_PATH", "LD_PRELOAD",
                 "LD_AUDIT", "PKG_CONFIG_PATH", "PKG_CONFIG_ALLOW_SYSTEM_CFLAGS",
                 "PKG_CONFIG_ALLOW_SYSTEM_LIBS"):
        if env.get(name):
            raise IsolationError("Host search override: " + name)
    if env.get("PYTHONNOUSERSITE") != "1" or env.get("PIP_NO_INDEX") != "1":
        raise IsolationError("unisolated Python packaging")
    if env.get("PKG_CONFIG_LIBDIR") != os.pathsep.join(data["pkgconfig_dirs"]):
        raise IsolationError("pkgconf can resolve Host .pc files")
    if env.get("PKG_CONFIG_SYSROOT_DIR") != data["sysroot"]:
        raise IsolationError("non-isolated pkgconf sysroot")
    parts = env.get("PATH", "").split(os.pathsep)
    if any(not p for p in parts):
        raise IsolationError("empty PATH component")
    roots = [Path(r).resolve(strict=True) for r in data["allowed_roots"]]
    if any(not inside(p, roots) for p in parts):
        raise IsolationError("Host PATH component")


def check_imports(data):
    python = data["tools"]["python"]["path"]
    code = """import importlib,json,sys
names = %r
print(json.dumps({"executable":sys.executable,"paths":sys.path,
 "modules":{n:getattr(importlib.import_module(n),"__file__",None) for n in names}}))
""" % (MODULES,)
    result = subprocess.run([python, "-I", "-c", code], capture_output=True,
                            text=True, timeout=40, check=True)
    report = json.loads(result.stdout)
    if Path(report["executable"]).resolve() != Path(python).resolve():
        raise IsolationError("wrong Python interpreter")
    roots = [Path(p).resolve(strict=True) for p in data["allowed_roots"]]
    for name, origin in report["modules"].items():
        allowed = tuple(Path(p).resolve(strict=True) for p in data["imports"][name])
        if not origin or not inside(origin, allowed):
            raise IsolationError("Host Python module: " + name)
    for search_path in report["paths"]:
        if search_path and not inside(search_path, roots):
            raise IsolationError("Host Python sys.path: " + search_path)


def check_pkgconf(data):
    env = {k:v for k,v in os.environ.items() if not k.startswith("PKG_CONFIG_")}
    env.update(PKG_CONFIG_LIBDIR=os.pathsep.join(data["pkgconfig_dirs"]),
               PKG_CONFIG_PATH="", PKG_CONFIG_SYSROOT_DIR=data["sysroot"])
    exe = data["tools"]["pkgconf"]["path"]
    roots = tuple(Path(x).resolve(strict=True) for x in data["allowed_roots"])
    for package in PC:
        check = subprocess.run([exe, "--variable=pcfiledir", package],
                               env=env, capture_output=True, text=True,
                               timeout=20, check=True)
        found = check.stdout.strip()
        if not found or not inside(found, roots):
            raise IsolationError("Host pkgconf provider: " + package)
        flags = subprocess.run([exe, "--cflags", "--libs", package],
                               env=env, capture_output=True, text=True,
                               timeout=20, check=True).stdout.split()
        for flag in flags:
            if (flag.startswith(("-I", "-L")) and len(flag)>2 and
                not inside(flag[2:], roots)):
                raise IsolationError("Host pkgconf include/library path: " + package)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attestation", required=True, type=Path)
    args = parser.parse_args()
    receipt = args.attestation
    if not receipt.is_file() or receipt.stat().st_uid != 0 or receipt.stat().st_mode & 0o022:
        raise IsolationError("receipt must be protected and root-owned")
    data = json.loads(receipt.read_text())
    check_files(data)
    check_environment(data, os.environ)
    check_imports(data)
    check_pkgconf(data)
    print("ZOG_MESA_ISOLATED_TOOLCHAIN_PASS")


if __name__ == "__main__":
    main()

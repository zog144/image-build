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
import shutil
import shlex
import stat
from pathlib import Path
import subprocess

BASE_TOOLS = ("python", "cmake", "ninja", "meson", "pkgconf")
BASE_MODULES = ("setuptools", "packaging", "wheel", "installer", "markupsafe")
TOOLS = BASE_TOOLS + ("llvm-config",)
MODULES = BASE_MODULES + ("mako", "yaml")
PC = ("x11", "xext", "x11-xcb", "xcb", "xcb-randr", "xcb-glx", "xcb-shm",
      "xcb-dri3", "xcb-present", "xcb-sync", "xcb-xfixes", "xshmfence",
      "xxf86vm", "libdrm", "expat", "zlib")


class IsolationError(RuntimeError):
    pass


def inside(path, roots):
    # sys.path may legitimately contain an uncreated pythonXY.zip under Zog.
    # Resolve existing symlink prefixes, but do not treat absence as Host access.
    real = Path(path).resolve(strict=False)
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


def check_files(data, phase="mesa"):
    roots = roots_for(data)
    needed_tools = TOOLS if phase == "mesa" else BASE_TOOLS
    needed_modules = MODULES if phase == "mesa" else BASE_MODULES
    if phase not in ("mako", "pyyaml", "mesa"):
        raise IsolationError("unknown build phase")
    if set(data["tools"]) != set(needed_tools):
        raise IsolationError("incomplete executable closure")
    if set(data["imports"]) != set(needed_modules):
        raise IsolationError("incomplete Python import closure")
    if not data["pkgconfig_dirs"]:
        raise IsolationError("missing pkgconf search roots")
    for d in data["pkgconfig_dirs"]:
        if not Path(d).is_dir() or not inside(d, roots):
            raise IsolationError("Host pkgconfig directory")
    if not inside(data["sysroot"], roots):
        raise IsolationError("Host sysroot")
    verifier = data.get("verifier", {})
    self_path = Path(__file__).resolve(strict=True)
    if verifier.get("path") is None or Path(verifier["path"]).resolve(strict=True) != self_path:
        raise IsolationError("native verifier source not pinned to installed path")
    if not inside(self_path, roots):
        raise IsolationError("native verifier outside approved Zog roots")
    digest = verifier.get("sha256", "")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise IsolationError("invalid native verifier hash pin")
    if hashlib.sha256(self_path.read_bytes()).hexdigest() != digest:
        raise IsolationError("wrong protected verifier source bytes")
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
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "PYTHONINSPECT",
                 "PYTHONSTARTUP", "PYTHONPYCACHEPREFIX", "PYTHONPLATLIBDIR",
                 "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_CONFIG_FILE",
                 "CMAKE_PREFIX_PATH", "CMAKE_MODULE_PATH", "CMAKE_TOOLCHAIN_FILE",
                 "LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT",
                 "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                 "GCC_EXEC_PREFIX", "COMPILER_PATH", "MESON_PACKAGE_CACHE_DIR",
                 "BASH_ENV", "ENV", "PKG_CONFIG_PATH",
                 "PKG_CONFIG_ALLOW_SYSTEM_CFLAGS", "PKG_CONFIG_ALLOW_SYSTEM_LIBS"):
        if env.get(name):
            raise IsolationError("Host search override: " + name)
    if env.get("PYTHONNOUSERSITE") != "1" or env.get("PIP_NO_INDEX") != "1":
        raise IsolationError("unisolated Python packaging")
    allowed_pc = {"PKG_CONFIG_LIBDIR", "PKG_CONFIG_SYSROOT_DIR", "PKG_CONFIG_PATH"}
    if any(name.startswith("PKG_CONFIG_") and name not in allowed_pc for name in env):
        raise IsolationError("unsupported pkgconf environment override")
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


def check_invoked_commands(data):
    """Prevent PATH aliases from selecting unreviewed binaries in Zog roots."""
    aliases = {"python3": "python", "cmake": "cmake", "ninja": "ninja",
               "meson": "meson", "pkgconf": "pkgconf", "pkg-config": "pkgconf"}
    if "llvm-config" in data["tools"]:
        aliases["llvm-config"] = "llvm-config"
    for executable, key in aliases.items():
        resolved = shutil.which(executable)
        if resolved is None or Path(resolved).resolve(strict=True) != Path(
                data["tools"][key]["path"]).resolve(strict=True):
            raise IsolationError("PATH command is not approved tool: " + executable)


def check_imports(data):
    python = data["tools"]["python"]["path"]
    code = """import importlib,json,sys
names = %r
print(json.dumps({"executable":sys.executable,"paths":sys.path,
 "isolated":sys.flags.isolated,"no_user_site":sys.flags.no_user_site,
 "modules":{n:getattr(importlib.import_module(n),"__file__",None) for n in names}}))
""" % (tuple(data["imports"]),)
    result = subprocess.run([python, "-I", "-c", code], capture_output=True,
                            text=True, timeout=40, check=True)
    report = json.loads(result.stdout)
    if Path(report["executable"]).resolve() != Path(python).resolve():
        raise IsolationError("wrong Python interpreter")
    if report.get("isolated") != 1 or report.get("no_user_site") != 1:
        raise IsolationError("Python isolated mode was not active")
    if set(report["modules"]) != set(data["imports"]):
        raise IsolationError("Python import observation incomplete")
    roots = [Path(p).resolve(strict=True) for p in data["allowed_roots"]]
    for name, origin in report["modules"].items():
        allowed = tuple(Path(p).resolve(strict=True) for p in data["imports"][name])
        if not origin or not inside(origin, allowed):
            raise IsolationError("Host Python module: " + name)
    for search_path in report["paths"]:
        if search_path and not inside(search_path, roots):
            raise IsolationError("Host Python sys.path: " + search_path)


def check_pkgconf_flags(package, raw, roots):
    """Allow ordinary pkgconf switches; hold opaque options for native review."""
    words = shlex.split(raw)
    paired = ("-I", "-L", "-isystem", "-iquote", "-idirafter")
    i = 0
    while i < len(words):
        arg = words[i]
        if arg in paired:
            i += 1
            if i >= len(words) or not inside(words[i], roots):
                raise IsolationError("Host pkgconf split include/library path: " + package)
        elif any(arg.startswith(prefix) and len(arg) > len(prefix)
                 for prefix in paired):
            prefix = next(prefix for prefix in paired if arg.startswith(prefix))
            if not inside(arg[len(prefix):], roots):
                raise IsolationError("Host pkgconf include/library path: " + package)
        elif arg.startswith("-l") and len(arg) > 2 and "/" not in arg:
            pass
        elif arg.startswith(("-D", "-U")) and "/" not in arg and "@" not in arg:
            pass
        elif arg == "-pthread":
            pass
        else:
            raise IsolationError("unreviewed pkgconf compiler/linker option: " + package)
        i += 1


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
        # Also include Requires.private and Libs.private. Native ELF and
        # actual library resolution evidence remains a separate acceptance gate.
        flags = subprocess.run([exe, "--static", "--cflags", "--libs", package],
                               env=env, capture_output=True, text=True,
                               timeout=20, check=True).stdout
        check_pkgconf_flags(package, flags, roots)


def read_protected_receipt(receipt):
    """Reject symlinks and user-writable directory replacement before reading."""
    path = Path(receipt)
    if not path.is_absolute():
        raise IsolationError("native receipt must use absolute protected path")
    for ancestor in list(reversed(path.parents)):
        st = ancestor.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise IsolationError("unprotected receipt ancestor: " + str(ancestor))
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
        raise IsolationError("unprotected receipt file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise IsolationError("receipt changed during inspection")
        if st.st_size > 1024 * 1024:
            raise IsolationError("oversized receipt")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return json.loads(stream.read(1024 * 1024 + 1))
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attestation", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("mako", "pyyaml", "mesa"))
    args = parser.parse_args()
    data = read_protected_receipt(args.attestation)
    check_files(data, args.phase)
    check_environment(data, os.environ)
    check_invoked_commands(data)
    check_imports(data)
    if args.phase == "mesa":
        check_pkgconf(data)
    print("ZOG_MESA_ISOLATED_TOOLCHAIN_PASS")


if __name__ == "__main__":
    main()

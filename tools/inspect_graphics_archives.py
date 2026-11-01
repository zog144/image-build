#!/usr/bin/env python3
"""Inspect exact pinned upstream graphics archives; never builds or publishes.

Use only in unprivileged source CI. Check expected URL+SHA from inert metadata.
Emit deterministic archive-member digests for human rights/build review.
No extraction, shell, plugins, mutable URL resolution, or installed output.
"""
import argparse
import ast
import hashlib
import io
import json
import re
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "project/pins/2026-11-01/graphics-source-pin.py"
MAX_BYTES = 240 * 1024 * 1024
MEMBER_LIMIT = 2 * 1024 * 1024
NAMES = ("llvm", "mesa", "mesa-demos", "libdrm", "mako", "pyyaml",
         "libxshmfence", "libXxf86vm")
OPTIONS = ("meson.options", "meson_options.txt", "CMakeLists.txt",
           "meson.build", "src/glx/meson.build",
           "src/gallium/targets/dri/meson.build", "src/xdemos/meson.build")
DEMOS_RIGHTS = ("src/xdemos/glxgears.c", "src/xdemos/glxinfo.c")
LIBDRM_RIGHTS = ("xf86drm.c", "xf86drm.h", "meson.build")
NOTICES = ("LICENSE", "COPYING", "NOTICE", "LICENSE.TXT",
           "license.rst", "LICENSE.md", "COPYRIGHT", "README.license")


def check_member(member):
    path = PurePosixPath(member.name)
    if (path.is_absolute() or ".." in path.parts or "\\" in member.name
            or not member.isfile()):
        return None
    if len(path.parts) < 2 or len(member.name) > 512:
        return None
    lower = path.name.lower()
    relative = "/".join(path.parts[1:])
    if (lower in {p.lower() for p in NOTICES}
            or relative in OPTIONS or relative in DEMOS_RIGHTS or relative in LIBDRM_RIGHTS
            or lower.startswith(("license.", "copying.", "notice."))):
        return path
    return None


def inspect_one(name, entry, output, fetch=True):
    source = entry["source"]
    if (set(source) != {"url", "sha256"} or not source["url"].startswith("https://")
            or len(source["sha256"]) != 64 or
            any(c not in "0123456789abcdef" for c in source["sha256"])):
        raise ValueError("invalid bound archive pin: " + name)
    url = source["url"]
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / "source-archive"
        if fetch:
            length = 0
            h = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=180) as response:
                if response.url.split("?")[0].startswith("http://"):
                    raise ValueError("insecure source redirect")
                with archive.open("wb") as dest:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        length += len(chunk)
                        if length > MAX_BYTES:
                            raise ValueError("oversized source archive")
                        h.update(chunk)
                        dest.write(chunk)
            digest = h.hexdigest()
        else:
            raise ValueError("offline inspection requires a supplied verified archive")
        if digest != source["sha256"]:
            raise ValueError("archive SHA-256 differs for " + name)
        record = {"source_sha256": digest, "url": url, "members": {}}
        option_names = set()
        source_tree_layout = []
        referenced_dependencies = {}
        build_targets = {}
        dependency_contexts = {}
        with tarfile.open(archive, "r:*") as tar:
            for member in tar:
                all_parts = PurePosixPath(member.name).parts
                if (name in ("libxshmfence", "libXxf86vm", "mesa-demos")
                    and len(all_parts) <= 4 and member.isfile()
                    and len(source_tree_layout) < 120):
                    source_tree_layout.append("/".join(all_parts[1:]))
                path = check_member(member)
                if path is None:
                    continue
                if member.size > MEMBER_LIMIT:
                    raise ValueError("oversized selected archive member")
                content = tar.extractfile(member)
                if content is None:
                    raise ValueError("unreadable selected archive member")
                data = content.read(MEMBER_LIMIT + 1)
                if len(data) != member.size:
                    raise ValueError("archive member size mismatch")
                if member.name in record["members"]:
                    raise ValueError("duplicate archive member")
                record["members"][member.name] = {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": member.size,
                }
                relative = "/".join(PurePosixPath(member.name).parts[1:])
                if relative in ("meson.options", "meson_options.txt"):
                    option_names = set(re.findall(
                        "option\\s*\\(\\s*[\u0027\"]([^\u0027\"]+)", data.decode("utf-8")))
                if relative.endswith("meson.build"):
                    contents = data.decode("utf-8")
                    referenced_dependencies[relative] = sorted(set(re.findall(
                        "dependency\\s*\\(\\s*[\u0027\"]([^\u0027\"]+)", contents)))
                    if name == "mesa" and relative == "meson.build":
                        names = ("x11", "x11-xcb", "xcb", "xcb-glx",
                                 "xcb-dri3", "xcb-present", "xcb-xfixes",
                                 "xrandr", "xshmfence", "xxf86vm")
                        dependency_contexts[relative] = {}
                        for dep in names:
                            pat = re.compile("dependency\\s*\\(\\s*[\u0027\"]" +
                                             re.escape(dep) + "[\u0027\"]")
                            dependency_contexts[relative][dep] = [
                                contents[max(0, m.start() - 320): m.end() + 250]
                                for m in list(pat.finditer(contents))[:3]]
                    if relative == "src/xdemos/meson.build":
                        build_targets[relative] = sorted(set(
                            x for x in ("glxgears", "glxinfo") if x in contents))
        notices = {
            path: value for path, value in record["members"].items()
            if any(token in path.rsplit("/", 1)[-1].lower()
                   for token in ("license", "copying", "notice"))
        }
        if name == "mesa-demos":
            source_paths = [p for p in record["members"]
                            if p.endswith("/src/xdemos/glxgears.c")
                            or p.endswith("/src/xdemos/glxinfo.c")]
            if len(source_paths) != 2:
                raise ValueError("demo rights source headers are missing")
        elif name == "libdrm":
            inspected = [p for p in record["members"]
                         if p.endswith("/xf86drm.c") or p.endswith("/xf86drm.h")]
            if len(inspected) != 2:
                raise ValueError("libdrm source rights headers are missing")
        elif not notices:
            raise ValueError("no inspectable upstream notice: " + name)
        if name in ("mesa", "mesa-demos", "libdrm"):
            draft = ast.literal_eval((ROOT / "project/graphics-drafts" / name /
                                      "stages/final/build.py").read_text())
            arguments = draft["configure"][0][-1]
            required = set(re.findall(r"-D([a-z][a-z0-9_-]*)=", arguments))
            required.discard("auto_features")
            missing = sorted(required - option_names)
            if missing:
                raise ValueError("unrecognized exact-release Meson option for " +
                                 name + ": " + ", ".join(missing))
            record["meson_options"] = sorted(option_names)
            record["profile_options_checked"] = sorted(required)
        output[name] = record
        print(json.dumps({
            "package": name,
            "source_sha256": digest,
            "source_tree_layout": source_tree_layout,
            "selected_notices": notices,
            "profile_options_checked": record.get("profile_options_checked", []),
            "referenced_dependencies": referenced_dependencies,
            "selected_dependency_contexts": dependency_contexts,
            "smoke_build_targets": build_targets,
            "top_level_options": {
                p: v for p, v in record["members"].items()
                if p.endswith("/meson.options") or
                   p.endswith("/meson_options.txt") or
                   p.endswith("/CMakeLists.txt")
            },
            "source_rights": {
                p: v for p,v in record["members"].items()
                if p.endswith("/src/xdemos/glxgears.c") or
                   p.endswith("/src/xdemos/glxinfo.c") or
                   p.endswith("/xf86drm.c") or p.endswith("/xf86drm.h")
            },
        }, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = ast.literal_eval(SOURCE.read_text())
    assert manifest["status"].startswith("supplementary-source-review-only")
    assert set(manifest["packages"]) == set(NAMES)
    result = {}
    for name in NAMES:
        inspect_one(name, manifest["packages"][name], result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only, pinned original Mesa-family source-rights questions.

No compiler/source inclusion, native evidence, installed notices or license approval.
"""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] / "project/graphics-drafts"
SELECTED = {
    "llvm": {
        "prefixes": ("lib/Support/BLAKE3/", "utils/TableGen/"),
        "members": ("LICENSE.TXT", "lib/Support/BLAKE3/LICENSE",
                    "include/llvm/Support/LICENSE.TXT"),
        "question": "Which BLAKE3 and TableGen/generated code units actually link into libLLVM.so, and which notices travel with them?",
    },
    "mesa": {
        "prefixes": ("src/mesa/glapi/glapi/gen/", "src/gallium/drivers/llvmpipe/",
                     "src/vulkan/", "src/imgui/"),
        "members": ("docs/license.rst", "src/mesa/glapi/glapi/gen/license.py",
                    "src/gallium/drivers/llvmpipe/lp_screen.c", "src/glx/meson.build"),
        "question": "Which GLAPI/llvmpipe generators and generated files link to swrast/GLX, while Vulkan and imgui stay excluded?",
    },
    "libdrm": {
        "prefixes": ("intel/", "radeon/", "amdgpu/", "nouveau/", "tests/"),
        "members": ("xf86drm.c", "xf86drm.h", "xf86drmMode.c"),
        "question": "Does disabling driver/udev/tests truly exclude all vendor and KMS source objects, including xf86drmMode.c?",
    },
    "mesa-demos": {
        "prefixes": ("src/xdemos/",),
        "members": ("src/xdemos/glxgears.c", "src/xdemos/glxinfo.c"),
        "question": "Do both selected programs carry independently reviewed original copyright/public-domain notices and only selected sources?",
    },
}
LIMIT = 100 * 1024 * 1024

def inspect(name, data, *, source_sha):
    if name not in SELECTED:
        raise ValueError("unknown rights scope")
    if hashlib.sha256(data).hexdigest() != source_sha:
        raise ValueError("original source archive digest differs from pin")
    selected = SELECTED[name]
    members = {}
    groups = {prefix: 0 for prefix in selected["prefixes"]}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive:
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise ValueError("unsafe upstream path")
            if not member.isfile():
                continue
            relative = member.name.partition("/")[2]
            for prefix in groups:
                if relative.startswith(prefix):
                    groups[prefix] += 1
            if relative in selected["members"]:
                if member.size > 1024 * 1024:
                    raise ValueError("oversized selected member")
                if relative in members:
                    raise ValueError("duplicate selected member")
                members[relative] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    if set(members) != set(selected["members"]):
        raise ValueError("original candidate rights/source member missing")
    if any(not count for count in groups.values()):
        raise ValueError("expected selected/excluded feature tree absent")
    return {
        "schema": "mesa-original-rights-question-inventory-v1",
        "package": name,
        "source_sha256": source_sha,
        "selected_original_members": members,
        "original_tree_file_counts": groups,
        "unresolved_question": selected["question"],
        "native_selected_compilation": "not observed",
        "installed_notices": "not observed",
        "independent_rights_approved": False,
        "canonical_admitted": False,
    }

def original_pin(name):
    record = ast.literal_eval((ROOT / name / "license.py").read_text())
    if record["status"] != "unresolved":
        raise ValueError("rights status changed")
    return record["source"]["url"], record["source"]["sha256"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", choices=sorted(SELECTED), required=True)
    args = parser.parse_args()
    url, digest = original_pin(args.package)
    with urlopen(Request(url, headers={"User-Agent": "Zog-original-rights-review/1"}), timeout=90) as response:
        contents = response.read(LIMIT + 1)
    if len(contents) > LIMIT:
        raise ValueError("original archive exceeds source-only review bound")
    print(json.dumps(inspect(args.package, contents, source_sha=digest), sort_keys=True))

if __name__ == "__main__":
    main()

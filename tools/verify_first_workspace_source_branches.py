#!/usr/bin/env python3
"""Read-only frozen two-PR Workspace source-graph and admission boundary audit.

No compiler, native executable, source admittance, rights or generation mutation.
"""
import ast
import json
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MESA_HEAD = "9cbd652226b863a7b4bb2d6d9539722e1a262508"
URL_BASE = "https://raw.githubusercontent.com/zog144/image-build/" + MESA_HEAD
ROOT = Path(__file__).resolve().parents[1]
MESA_PACKAGES = ("llvm", "mesa", "mesa-demos", "libdrm", "libxshmfence", "libXxf86vm")
I3_PACKAGES = ("libev", "yajl", "startup-notification", "xkeyboard-config", "libxkbcommon",
               "xcb-util", "xcb-util-image", "xcb-util-renderutil", "xcb-util-cursor")
CANONICAL_HOLD = "source-prepared-native-and-rights-NO-GO"

def guard(local, external, status, scopes):
    if local.get("status") != "source-incomplete":
        raise ValueError("PR9 source graph is not truthfully held")
    if local.get("native_accepted") is not False or local.get("rights_authorized") is not False:
        raise ValueError("source-only graph attempts native or rights approval")
    if local.get("canonical_promotion_allowed") is not False or local.get("build_submission_allowed") is not False:
        raise ValueError("source graph attempts admission/submit")
    if external.get("status") != CANONICAL_HOLD:
        raise ValueError("Mesa source draft is not held")
    if status.get("status") != "independent-rights-and-native-output-NO-GO":
        raise ValueError("Mesa selected-source rights unexpectedly authorized")
    for pkg in MESA_PACKAGES:
        item = status["components"][pkg]
        if item.get("installed_outputs_observed") is not False or item.get("notice_delivery_verified") is not False:
            raise ValueError("Mesa package claims native output evidence")
        if item.get("actual_compile_commands_status") != "not received":
            raise ValueError("Mesa compiler evidence must remain a separate native input")
    if external.get("draft_root") != "project/graphics-drafts":
        raise ValueError("Mesa drafts have been canonically promoted")
    if not {"LLVM X86 shared RTTI", "Mesa Gallium swrast llvmpipe GLX/X11"}.issubset(set(scopes["enabled"])):
        raise ValueError("Mesa software feature scope changed")
    if "Vulkan" not in scopes["excluded"]:
        raise ValueError("Mesa hardware feature scope expanded")

def remote_json(path):
    req = Request(URL_BASE + "/" + path, headers={"User-Agent": "zog-source-integration/1"})
    with urlopen(req, timeout=30) as result:
        raw = result.read(512 * 1024 + 1)
    if len(raw)>512*1024:
        raise ValueError("oversized Mesa source contract")
    return json.loads(raw)

REVIEW_BLOBS = {
    "tests/test_mesa_selected_notice_rights.py": "2c6fa34ed4a55501af788934c21dd81431feaaf1",
    "docs/image-build/mesa-selected-notice-re-review-2026-11-02.md": "8071a19831f3d1ab050b645a6196e08fbebe982d",
    ".github/workflows/public-source-ci.yml": "1b4946018d9344323f53a24a503f2f18867087d0",
    "tests/test_mesa_original_rights_questions.py": "377f83a6d74748173d09430ecdf0221fe92be9cd",
    "docs/image-build/mesa-original-rights-questions-2026-11-02.md": "7c44f53d95dfb94d7443b2b901afd1e6edab43d3",
    ".github/workflows/inspect-mesa-original-rights-questions.yml": "828159829b7f18cf27fd1f10e2dff3ea29205d56",
    "tools/inspect_mesa_original_rights_questions.py": "2b8ba6ce5c64e8f5f3482671ec5b3d98daadd9bd",
    "project/graphics-drafts/llvm/stages/final/dependencies.py": "e690125fe0a1acb957505d03788e88b53a7600d9",
    "project/graphics-drafts/mesa/stages/final/dependencies.py": "40ecf8ecaada03921744f819a8a0e5bdf848486c",
    "docs/image-build/mesa-inherited-zlib-stage-2026-11-02.md": "f7fed7c9c20e61dc6eeeb282733ab68fdf1dc7b5",
}

def verify_review_blob(path, data):
    # SHA-1 is the Git *object identity* here, not a new source hash or
    # authority. The exact reviewed PR8 commit provides the immutable origin.
    actual = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()
    if actual != REVIEW_BLOBS[path]:
        raise ValueError("selected Mesa notice-review byte identity changed")

def remote_bytes(path):
    req = Request(URL_BASE + "/" + path, headers={"User-Agent": "zog-immutable-review/1"})
    with urlopen(req, timeout=30) as result:
        data = result.read(512 * 1024 + 1)
    if len(data) > 512 * 1024:
        raise ValueError("oversized selected Mesa review blob")
    verify_review_blob(path, data)
    return data


def verify_x11_glx_dependency_intersection(mesa, llvm, xvnc, local):
    """No masked host zlib stage, software GLX omission, or device expansion."""
    if any(type(x) is not dict for x in (mesa,llvm,xvnc,local)):
        raise ValueError("untyped source graph")
    mesa_build=set(mesa.get("build",[]))
    llvm_build=set(llvm.get("build",[]))
    xvnc_build=set(xvnc.get("build",[]))
    required_mesa={"llvm-final","libX11-final","libXext-final","libxcb-final",
                   "libdrm-final","libxshmfence-final","libXxf86vm-final",
                   "zlib-native-environment"}
    required_xvnc={"mesa-final","libX11-final","libXfont2-final","xkbcomp-final",
                   "zlib-native-environment","pixman-final","libjpeg-turbo-final"}
    if (not required_mesa.issubset(mesa_build)
            or llvm_build != {"zlib-native-environment"}
            or not required_xvnc.issubset(xvnc_build)
            or "zlib-final" in mesa_build|llvm_build|xvnc_build
            or "libdrm-final" in xvnc_build):
        raise ValueError("missing software GLX or inherited source-stage closure")
    if local.get("frozen_accepted_generations_required") != ["fonts","XCB","X11"]:
        raise ValueError("accepted generation order altered")
    profile=local.get("consumers",{}).get("turbovnc",{}).get("cmake_profile",{})
    for key,value in {"TVNC_DRI3":"OFF","TVNC_ZLIBNG":"OFF","TVNC_USEPAM":"OFF",
                      "TVNC_BUILDVIEWER":"OFF","TVNC_NVCONTROL":"OFF",
                      "TVNC_USETLS":"OpenSSL"}.items():
        if profile.get(key)!=value:
            raise ValueError("Xvnc server-only feature expansion: "+key)

def main():
    local = json.loads((ROOT/"project/graphics-first-workspace/closure.json").read_text())
    plan = remote_json("project/graphics-drafts/admission-plan.json")
    rights = remote_json("project/graphics-drafts/rights-admission-evidence.json")
    guard(local,plan,rights,rights["scope"])
    for path in REVIEW_BLOBS:
        remote_bytes(path)
    mesa_deps=ast.literal_eval(remote_bytes("project/graphics-drafts/mesa/stages/final/dependencies.py").decode("utf-8"))
    llvm_deps=ast.literal_eval(remote_bytes("project/graphics-drafts/llvm/stages/final/dependencies.py").decode("utf-8"))
    xvnc_deps=ast.literal_eval((ROOT/"project/graphics-first-workspace/turbovnc-draft/stages/final/dependencies.py").read_text())
    verify_x11_glx_dependency_intersection(mesa_deps,llvm_deps,xvnc_deps,local)
    for pkg in I3_PACKAGES:
        record = ast.literal_eval((ROOT/"project/package"/pkg/"package.py").read_text())
        if record["status"] != "catalogue-only":
            raise ValueError("i3 source input unexpectedly admitted: " + pkg)
    for pkg in ("i3","turbovnc","xterm"):
        record = ast.literal_eval((ROOT/"project/package"/pkg/"package.py").read_text())
        if record["status"] != "catalogue-only":
            raise ValueError("Workspace consumer unexpectedly admitted: " + pkg)
    if local["frozen_accepted_generations_required"] != ["fonts","XCB","X11"]:
        raise ValueError("accepted predecessor ordering altered")
    print(json.dumps({"schema":"first-workspace-source-two-branch-consistency-v1",
        "image_build_workspace_source_revision":"local-git-checkout",
        "mesa_source_revision":MESA_HEAD,
        "mesa_rights_native":"NO-GO",
        "i3_xterm_xvnc":"source-incomplete",
        "fonts_xcb_x11":"independent-native-generation-required",
        "source_consistency_checked":True,
        "native_accepted":False,"redistribution_authorized":False,
        "canonical_admitted":False,"generation_created":False}, sort_keys=True))

if __name__=="__main__":
    main()

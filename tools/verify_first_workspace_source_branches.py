#!/usr/bin/env python3
"""Read-only frozen two-PR Workspace source-graph and admission boundary audit.

No compiler, native executable, source admittance, rights or generation mutation.
"""
import ast
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MESA_HEAD = "ad35f53dac8355f86bc517357a6a88ba8bf850bd"
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

def main():
    local = json.loads((ROOT/"project/graphics-first-workspace/closure.json").read_text())
    plan = remote_json("project/graphics-drafts/admission-plan.json")
    rights = remote_json("project/graphics-drafts/rights-admission-evidence.json")
    guard(local,plan,rights,rights["scope"])
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

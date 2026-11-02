"""Source-only intersection deliberately rejects any accepted-but-unwitnessed state."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workspace_cross_branch",ROOT/"tools/verify_first_workspace_source_branches.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def valid():
    local={"status":"source-incomplete","native_accepted":False,
           "rights_authorized":False,"canonical_promotion_allowed":False,
           "build_submission_allowed":False}
    plan={"status":mod.CANONICAL_HOLD,"draft_root":"project/graphics-drafts"}
    records={"status":"independent-rights-and-native-output-NO-GO",
             "components":{p:{"installed_outputs_observed":False,
                              "notice_delivery_verified":False,
                              "actual_compile_commands_status":"not received"}
                           for p in mod.MESA_PACKAGES}}
    scope={"enabled":["LLVM X86 shared RTTI","Mesa Gallium swrast llvmpipe GLX/X11"],
           "excluded":["Vulkan"]}
    return local,plan,records,scope


def test_held_sources_are_allowed_but_not_admitted():
    mod.guard(*valid())


@pytest.mark.parametrize("path,value",[
    (("local","native_accepted"),True),
    (("local","canonical_promotion_allowed"),True),
    (("plan","draft_root"),"project/package"),
    (("records","status"),"approved"),
    (("records","components","mesa","installed_outputs_observed"),True),
    (("records","components","llvm","actual_compile_commands_status"),"complete"),
    (("scope","excluded"),[])
])
def test_local_and_mesa_source_authority_escalation_denied(path,value):
    local,plan,records,scope=valid()
    group={"local":local,"plan":plan,"records":records,"scope":scope}[path[0]]
    for key in path[1:-1]:group=group[key]
    group[path[-1]]=value
    with pytest.raises(ValueError):
        mod.guard(local,plan,records,scope)


def test_exact_selected_review_blob_binding_rejects_substituted_bytes():
    for path in mod.REVIEW_BLOBS:
        with pytest.raises(ValueError, match="byte identity"):
            mod.verify_review_blob(path, b"forged but structurally consistent approval")


def test_selected_review_artifacts_are_newer_but_cannot_change_native_holds():
    assert mod.MESA_HEAD == "9cbd652226b863a7b4bb2d6d9539722e1a262508"
    assert set(mod.REVIEW_BLOBS) == {
        "tests/test_mesa_selected_notice_rights.py",
        "docs/image-build/mesa-selected-notice-re-review-2026-11-02.md",
        ".github/workflows/public-source-ci.yml",
        "tests/test_mesa_original_rights_questions.py",
        "docs/image-build/mesa-original-rights-questions-2026-11-02.md",
        ".github/workflows/inspect-mesa-original-rights-questions.yml",
        "tools/inspect_mesa_original_rights_questions.py",
        "project/graphics-drafts/llvm/stages/final/dependencies.py",
        "project/graphics-drafts/mesa/stages/final/dependencies.py",
        "docs/image-build/mesa-inherited-zlib-stage-2026-11-02.md",
    }
    mod.guard(*valid())


def sample_graph():
    mesa={"build":["llvm-final","libX11-final","libXext-final","libxcb-final",
                  "libdrm-final","libxshmfence-final","libXxf86vm-final",
                  "zlib-native-environment"]}
    llvm={"build":["zlib-native-environment"]}
    xvnc={"build":["mesa-final","libX11-final","libXfont2-final","xkbcomp-final",
                  "zlib-native-environment","pixman-final","libjpeg-turbo-final"]}
    local={"frozen_accepted_generations_required":["fonts","XCB","X11"],
           "consumers":{"turbovnc":{"cmake_profile":{
               "TVNC_DRI3":"OFF","TVNC_ZLIBNG":"OFF","TVNC_USEPAM":"OFF",
               "TVNC_BUILDVIEWER":"OFF","TVNC_NVCONTROL":"OFF",
               "TVNC_USETLS":"OpenSSL"}}}}
    return mesa,llvm,xvnc,local

def test_software_glx_cross_branch_holds_source_only():
    mod.verify_x11_glx_dependency_intersection(*sample_graph())

@pytest.mark.parametrize("bad",["fake-zlib","no-x11","no-mesa","no-xkb","dri3",
                                 "pam","wrong-tls","wrong-generation"])
def test_negative_x11_glx_and_inherited_provenance(bad):
    mesa,llvm,xvnc,local=sample_graph()
    if bad=="fake-zlib": llvm["build"]=["zlib-final"]
    if bad=="no-x11": mesa["build"].remove("libX11-final")
    if bad=="no-mesa": xvnc["build"].remove("mesa-final")
    if bad=="no-xkb": xvnc["build"].remove("xkbcomp-final")
    if bad=="dri3": local["consumers"]["turbovnc"]["cmake_profile"]["TVNC_DRI3"]="ON"
    if bad=="pam": local["consumers"]["turbovnc"]["cmake_profile"]["TVNC_USEPAM"]="ON"
    if bad=="wrong-tls": local["consumers"]["turbovnc"]["cmake_profile"]["TVNC_USETLS"]="1"
    if bad=="wrong-generation": local["frozen_accepted_generations_required"]=["X11","XCB","fonts"]
    with pytest.raises(ValueError):
        mod.verify_x11_glx_dependency_intersection(mesa,llvm,xvnc,local)

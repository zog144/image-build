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
    assert mod.MESA_HEAD == "9da9ee74b0bceeb5104fe079fd8b48a9e74ce2d4"
    assert set(mod.REVIEW_BLOBS) == {
        "tests/test_mesa_selected_notice_rights.py",
        "docs/image-build/mesa-selected-notice-re-review-2026-11-02.md",
        ".github/workflows/public-source-ci.yml",
    }
    mod.guard(*valid())

"""Source-notice observations and independent rights/native selection must not be conflated."""
import ast
import json
from pathlib import Path
import re
import pytest

ROOT=Path(__file__).resolve().parents[1]
RECORD=json.loads((ROOT/"project/graphics-first-workspace/selected-component-rights-handoff.json").read_text())
REQUIRED={"turbovnc-xserver","turbovnc-libsha1","turbovnc-zlib-ng-excluded",
          "llvm-generated-blake3","mesa-glapi-generated","mesa-llvmpipe",
          "libdrm-common","mesa-demos-glxgears","mesa-demos-glxinfo"}


def test_original_scoped_evidence_is_not_native_or_rights_grant():
    assert RECORD["schema"]=="zog-graphics-selected-component-rights-handoff-v1"
    assert RECORD["source_revisions"]["mesa_pr8"]=="9cbd652226b863a7b4bb2d6d9539722e1a262508"
    assert RECORD["native_compiled_selection_observed"] is False
    assert RECORD["independent_redistribution_approved"] is False
    assert RECORD["installed_notice_bytes_observed"] is False
    rows=RECORD["components"]
    assert {r["id"] for r in rows} == REQUIRED
    for row in rows:
        assert re.fullmatch(r"[0-9a-f]{64}",row["source_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}",row["member_sha256"])
        assert row["source_bytes_status"]=="pinned_original_archive_member_sha256_observed"
        assert row["native_selection_status"]=="unobserved"
        assert row["redistribution_status"]=="HOLD"
        assert row["remaining"]


def test_turbovnc_members_are_exactly_selected_original_archive_notice_hashes():
    rights=ast.literal_eval((ROOT/"project/graphics-first-workspace/turbovnc-draft/license.py").read_text())
    rows=[r for r in RECORD["components"] if r["package"]=="turbovnc"]
    evidence={entry["path"].split("turbovnc-3.3.1/")[1]:entry for entry in rights["evidence"]}
    assert rights["status"]=="unresolved"
    for row in rows:
        assert evidence[row["member"]]["sha256"]==row["member_sha256"]
        assert evidence[row["member"]]["source_sha256"]==row["source_sha256"]


def test_mesa_original_member_digest_records_are_review_pins_not_approval():
    expected={
        "llvm-generated-blake3":("llvm","lib/Support/BLAKE3/LICENSE","6a94bedb"),
        "mesa-glapi-generated":("mesa","src/mesa/glapi/glapi/gen/license.py","9f11bc36"),
        "mesa-llvmpipe":("mesa","src/gallium/drivers/llvmpipe/lp_screen.c","77005dfc"),
        "libdrm-common":("libdrm","xf86drm.c","67684594"),
        "mesa-demos-glxgears":("mesa-demos","src/xdemos/glxgears.c","344a03af"),
        "mesa-demos-glxinfo":("mesa-demos","src/xdemos/glxinfo.c","54844ad4"),
    }
    for row in RECORD["components"]:
        if row["id"] not in expected:
            continue
        package,member,digest_prefix=expected[row["id"]]
        assert (row["package"],row["member"])==(package,member)
        assert row["member_sha256"].startswith(digest_prefix)
    assert "independently signed" in " ".join(RECORD["independent_next_evidence"])


def test_excluded_source_in_original_archive_is_not_compiled_object_proof():
    excluded={r["id"]:r for r in RECORD["components"] if "excluded" in r["id"]}
    assert set(excluded)=={"turbovnc-zlib-ng-excluded"}
    assert all(x["native_selection_status"]=="unobserved" for x in excluded.values())
    assert all(x["redistribution_status"]=="HOLD" for x in excluded.values())

# Reviewed full digests, not truncated prefixes. These pins are independently
# compared to the immutable PR8 Git blobs by the cross-branch source workflow.
FROZEN_MEMBERS = {
    "llvm-generated-blake3":"6a94bedb8b707ed97f6e310d0d015ab14e0683ffa0a612b02958581b9cc9fc0e",
    "mesa-glapi-generated":"9f11bc368fa08ad8a0fed990e5d54235425e4d1908625a4b06e860bb9aa1352a",
    "mesa-llvmpipe":"77005dfcb7ad695a8ea508a82c87f383ef117d66d4170d553239fabb6ed4ddc5",
    "libdrm-common":"676845942ab8b9bc5759b295528fce0f32b28ca7765c17d4546e253caaba62c4",
    "mesa-demos-glxgears":"344a03aff01708350d90603fd6b841bccd295157670f519b459bbf3874acf847",
    "mesa-demos-glxinfo":"54844ad4d57d65ae2041467f52035f3f4f8d299467a5790a0b6f6d56e6a2a4f7",
}

def test_full_selected_original_member_hashes_and_roles():
    import importlib.util
    spec=importlib.util.spec_from_file_location(
        "frozen_review",ROOT/"tools/verify_first_workspace_source_branches.py")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert {row["id"] for row in RECORD["components"]}==set(m.RIGHTS_PATHS)
    for row in RECORD["components"]:
        pkg,member,kind,paths=m.RIGHTS_PATHS[row["id"]]
        assert (row["package"],row["member"],row["member_role"],
                tuple(row["planned_notice_output_paths"]))==(pkg,member,kind,paths)
        assert row["delivery_proof_status"]=="not_observed"
        if row["id"] in FROZEN_MEMBERS:
            assert row["member_sha256"]==FROZEN_MEMBERS[row["id"]]


def test_original_turbovnc_notice_output_paths_have_real_source_manifest():
    manifest=ast.literal_eval((ROOT/"project/graphics-first-workspace/turbovnc-draft/stages/final/produce-manifest.py").read_text())
    install=ast.literal_eval((ROOT/"project/graphics-first-workspace/turbovnc-draft/stages/final/build.py").read_text())["install"][0][-1]
    for row in RECORD["components"]:
        if row["package"]!="turbovnc":
            continue
        for destination in row["planned_notice_output_paths"]:
            assert destination in manifest["required"]
            assert destination in install
    excluded=next(row for row in RECORD["components"] if row["id"]=="turbovnc-zlib-ng-excluded")
    assert excluded["planned_notice_output_paths"]==[]
    assert "TVNC_ZLIBNG=OFF" in ast.literal_eval(
        (ROOT/"project/graphics-first-workspace/turbovnc-draft/stages/final/build.py").read_text()
    )["configure"][0][-1]


def test_notice_matrix_is_not_reclassified_as_native_rights_permission():
    for row in RECORD["components"]:
        assert row["redistribution_status"]=="HOLD"
        assert row["native_selection_status"]=="unobserved"
    assert RECORD["independent_redistribution_approved"] is False
    assert RECORD["installed_notice_bytes_observed"] is False

def _synthetic_pinned_pr8_review_fixtures():
    """Negative-unit fixtures only; real immutable PR8 bytes checked by cross-branch CI."""
    import copy
    licenses={}
    manifests={}
    for row in RECORD["components"]:
        package=row["package"]
        prefix={"turbovnc":"turbovnc-3.3.1/",
                "llvm":"llvm-21.1.6.src/",
                "mesa":"mesa-25.3.0/",
                "libdrm":"libdrm-2.4.128/",
                "mesa-demos":"mesa-demos-9.0.0/"}[package]
        license=licenses.setdefault(package,{
            "status":"unresolved","source":{"sha256":row["source_sha256"]},"evidence":[]})
        if row["id"]!="mesa-llvmpipe":
            license["evidence"].append({
                "path":prefix+row["member"],"sha256":row["member_sha256"],
                "source_sha256":row["source_sha256"]})
        manifest=manifests.setdefault(package,{"required":[]})
        manifest["required"].extend(row["planned_notice_output_paths"])
    rights={
        "status":"independent-rights-and-native-output-NO-GO",
        "components":{"mesa":{"original_scoped_source_candidates":[{
            "relative_member":"src/gallium/drivers/llvmpipe/lp_screen.c",
            "sha256":FROZEN_MEMBERS["mesa-llvmpipe"]}]}}}
    return copy.deepcopy(RECORD),licenses,manifests,rights


@pytest.mark.parametrize("failure",[
    "source_hash","member_hash","notice_output","source_role",
    "notice_claim","rights_claim","missing_linked_notice","rights_approved"
])
def test_cross_branch_rights_validator_fails_closed_on_contradictory_evidence(failure):
    import importlib.util
    spec=importlib.util.spec_from_file_location(
        "rights_review",ROOT/"tools/verify_first_workspace_source_branches.py")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    matrix,licenses,manifests,rights=_synthetic_pinned_pr8_review_fixtures()
    row=next(r for r in matrix["components"] if r["id"]=="mesa-glapi-generated")
    if failure=="source_hash":
        row["source_sha256"]="a"*64
    elif failure=="member_hash":
        row["member_sha256"]="b"*64
    elif failure=="notice_output":
        row["planned_notice_output_paths"]=["usr/share/licenses/mesa/missing"]
    elif failure=="source_role":
        row["member_role"]="copyright-permission-approved"
    elif failure=="notice_claim":
        row["delivery_proof_status"]="approved"
    elif failure=="rights_claim":
        matrix["independent_redistribution_approved"]=True
    elif failure=="missing_linked_notice":
        manifests["mesa"]["required"].remove("usr/share/licenses/mesa/glapi-generator-license.py")
    elif failure=="rights_approved":
        rights["status"]="approved"
    with pytest.raises(ValueError):
        m.verify_selected_rights_matrix(matrix,licenses,manifests,rights)

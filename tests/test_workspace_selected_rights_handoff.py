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

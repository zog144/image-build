"""Adversarial negative handoff validation, offline and source-only."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("handoff", ROOT/"tools/verify_workspace_native_handoff.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
original=json.loads((ROOT/"project/graphics-first-workspace/source-to-native-handoff.json").read_text())

def test_source_handoff_remains_non_submittable():
    assert mod.verify(original)

@pytest.mark.parametrize("key,mutation",[
    ("producer_order",["XCB","fonts","X11","Xvnc-i3-xterm","Mesa"]),
    ("producer_order",["fonts","XCB","Xvnc-i3-xterm","Mesa"]),
    ("source_revisions",{"workspace_pr9":"fake","mesa_pr8":"fake"}),
    ("inherited_stages",["zlib-native-environment"]),
    ("expected_outputs",["usr/bin/Xvnc"]),
    ("build_submission_allowed",True),
    ("native_accepted",True),
])
def test_refuses_missing_predecessor_or_escalated_source_claim(key, mutation):
    altered=copy.deepcopy(original)
    altered[key]=mutation
    with pytest.raises(ValueError):
        mod.verify(altered)

@pytest.mark.parametrize("slot",mod.RECEIPTS)
def test_fabricated_generation_identifier_is_never_accepted(slot):
    altered=copy.deepcopy(original)
    altered["accepted_generation_receipts"][slot]="sha256:"+"a"*64
    with pytest.raises(ValueError,match="fabricated"):
        mod.verify(altered)

"""Combined PR14/PR15 source boundary: explicit joins and negative evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "resident_combined", ROOT/"tools/verify_resident_b_combined_source.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE=json.loads(m.RECORD.read_text())

def test_exact_merged_stage_graph_and_installed_security_is_held():
    result=m.verify()
    assert result["review"]=="SOURCE_GRAPH_AND_INSTALLATION_CONSISTENT"
    assert result["selected_native_generation"] is None
    assert result["authority"]=="NO_GO"

@pytest.mark.parametrize("field,value",[
    ("pr14_source_head","f"*40),("pr15_original_source_head","a"*40),
    ("status","SOURCE_ACCEPTED"),
    ("trusted_native_witness",{"signature":"looks valid"}),
    ("accepted_generation","a"*64),
    ("compiler_submission_allowed",True),
    ("service_activation_allowed",True),
    ("redistribution_authorized",True)
])
def test_old_source_or_forged_witness_cannot_pass(field,value):
    altered=copy.deepcopy(BASE)
    altered[field]=value
    with pytest.raises(ValueError,match="NOT READY"):
        m.verify(record=altered)

@pytest.mark.parametrize("name,missing",[
    ("box-control","usr/bin/box-control"),
    ("box-control","usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/RECORD"),
    ("root-control","usr/bin/root-control"),
    ("root-control","usr/lib/systemd/system/zog-root-control.service"),
    ("root-control","usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/RECORD"),
    ("root-control","usr/share/licenses/root-control/THIRD-PARTY-NOTICES.md")
])
def test_declared_outputs_stay_exact_and_no_missing_license_or_metadata(name,missing):
    altered=copy.deepcopy(BASE)
    assert missing in altered["expected_installed_outputs"][name]
    altered["expected_installed_outputs"][name].remove(missing)
    with pytest.raises(ValueError,match="NOT READY"):
        m.verify(record=altered)

def test_stale_controller_edges_denied_even_if_install_service_unit_is_unchanged():
    altered=copy.deepcopy(m.dep.CONTROLLERS)
    altered["box-control"]["runtime"][2]="dbus-next-final"
    with pytest.raises(ValueError,match="transitive source NO-GO"):
        m.dep.verify(controllers=altered)

def test_missing_protected_socket_requirement_and_missing_tool_edge_both_denied():
    root=m.install.base.data(m.PKG/"root-control/stages/final/build.py")
    root["install"][0][-1]=root["install"][0][-1].replace("ConditionPathIsMountPoint=/state","ConditionPathExists=/state")
    with pytest.raises(ValueError,match="NOT READY"):
        m.verify(controller_overrides={
            ("root-control","stages/final/build.py"):root})
    package=m.dep.literal(m.PKG/"resident312-image-build/stages/final/dependencies.py")
    package["build"].remove("resident312-setuptools-final")
    with pytest.raises(ValueError,match="transitive source NO-GO"):
        m.verify(tool_overrides={
            ("resident312-image-build","stages/final/dependencies.py"):package})

def test_review_never_selects_real_root_or_socket_group():
    assert BASE["trusted_native_witness"] is None
    assert BASE["accepted_generation"] is None
    assert any("socket GID" in x for x in BASE["required_native_holds"])

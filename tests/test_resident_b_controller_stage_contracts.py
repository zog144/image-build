"""Source-only Resident B controller-stage design is not native authority."""
import ast
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"project"
RECORD=json.loads((P/"host/resident-b-controller-stage-contracts-v1.json").read_text())

def test_both_root_and_box_controller_designs_are_held_not_installable():
    assert RECORD["schema"]=="zog-resident-b-controller-stage-design-v1"
    assert RECORD["status"]=="CATALOGUE_ONLY_SOURCE_STAGES_AUTHORED_NATIVE_NO_GO"
    assert RECORD["source_selected"] is False
    assert RECORD["compilation_allowed"] is False
    assert RECORD["native_generation"] is None
    assert {entry["id"] for entry in RECORD["controllers"]}=={"root-control","box-control"}
    for entry in RECORD["controllers"]:
        assert len(entry["source_revision"])==40
        assert entry["status"]=="CATALOGUE_ONLY_SOURCE_STAGE_AUTHORED"
        assert entry["executable"]=="usr/bin/"+entry["id"]
        assert entry["package_stage"]==entry["id"]+"-final"
        assert "python-resident312-final" in entry["required_runtime"]
        assert (P/"package"/entry["id"]/"stages/final/build.py").exists()
        assert entry["source_revision"] == ast.literal_eval((P/"package"/entry["id"]/"package.py").read_text())["source_revision"]
    root=next(e for e in RECORD["controllers"] if e["id"]=="root-control")
    box=next(e for e in RECORD["controllers"] if e["id"]=="box-control")
    assert "STATE" in root["installation"]["state"]
    assert root["runtime_services"]==["usr/lib/systemd/system/zog-root-control.service"]
    assert box["runtime_services"]==[]

@pytest.mark.parametrize("package,paths",[
    ("systemd",["usr/bin/networkctl","usr/bin/resolvectl"]),
    ("host-install",["usr/bin/host-install"]),
    ("host-discover",["usr/bin/host-discover","usr/bin/host-discover-recovery",
                      "usr/bin/host-discover-supervisor"])
])
def test_selected_network_and_python_console_scripts_are_required_outputs(package,paths):
    manifest=ast.literal_eval((P/"package"/package/"stages/final/produce-manifest.py").read_text())
    assert set(paths).issubset(manifest["required"])

@pytest.mark.parametrize("package,version,entrypoints",[
    ("host-install","f82576c4f430398bc914b3e9d56b10c366ba0eac",("usr/bin/host-install",)),
    ("host-discover","b61197461f2fe19fd29203a1d148a66c6ce89f6d",
        ("usr/bin/host-discover","usr/bin/host-discover-recovery","usr/bin/host-discover-supervisor"))
])
def test_cli_contract_tied_to_pinned_wheel_source_not_invented_launcher(package,version,entrypoints):
    stage=P/"package"/package/"stages/final"
    source=ast.literal_eval((stage/"sources.py").read_text())
    assert len(source)==1 and version in source[0]["url"]
    build=ast.literal_eval((stage/"build.py").read_text())
    assert any("python3 -m installer --destdir" in step[-1] for step in build["install"])
    for entry in entrypoints:
        assert entry.startswith("usr/bin/")
    assert "unreviewed" not in str(build)

def test_executable_outputs_do_not_promote_wheel_or_service_to_native_acceptance():
    assert RECORD["source_selected"] is False
    assert "NATIVE_INSTALLED_PROOF_ABSENT" in RECORD["holds"]
    assert "PYTHON312_NOT_SELECTED" in RECORD["holds"]
    assert RECORD["required_python_runtime"]["selected_generation_receipt"] is None

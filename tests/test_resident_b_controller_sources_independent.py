"""Adversarial selected controller-source checks; never create native receipts."""
import ast
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("resident_control_verifier",
    ROOT/"tools/verify_resident_b_controller_source_stages.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def item(name,path):
    return ast.literal_eval((ROOT/"project/package"/name/path).read_text())

def test_real_original_archive_source_and_held_package_stages():
    result=mod.verify()
    assert result["source_stages"]=="PINNED_AND_HELD"
    assert result["native_generation"] is None
    assert result["authorization"]=="NO_GO"
    assert result["unresolved_transitive_stage_producers"]==[]
    assert "resident312-image-build-final" in result["native_unaccepted_transitive_stage_producers"]
    assert "resident312-dbus-next-final" in result["native_unaccepted_transitive_stage_producers"]

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_catalogue_only_and_archive_sha_not_fabricated(name):
    source=item(name,"stages/final/sources.py")
    assert source[0]["sha256"]==mod.SOURCES[name]["archive"]
    assert source[0]["url"].endswith(mod.SOURCES[name]["commit"])
    pkg=item(name,"package.py")
    assert pkg["status"]=="catalogue-only"
    assert pkg["source_archive_sha256"]==source[0]["sha256"]

@pytest.mark.parametrize("name,field,changed",[
    ("box-control","source","f"*64),
    ("root-control","source","0"*64),
    ("box-control","package","READY"),
    ("root-control","package","READY"),
    ("root-control","unit","[Install]"),
    ("box-control","deps","remove"),
    ("root-control","deps","remove"),
    ("root-control","install","remove"),
])
def test_synthetic_substitution_stage_permission_or_privilege_is_denied(name,field,changed):
    overrides={}
    if field=="source":
        s=item(name,"stages/final/sources.py");s[0]["sha256"]=changed
        overrides[name,"stages/final/sources.py"]=s
    elif field=="package":
        s=item(name,"package.py");s["status"]=changed
        overrides[name,"package.py"]=s
    elif field=="unit":
        s=item(name,"stages/final/build.py")
        s["install"][0][-1]+="\n"+changed+"\n"
        overrides[name,"stages/final/build.py"]=s
    elif field=="deps":
        s=item(name,"stages/final/dependencies.py")
        s["runtime"].remove("resident312-image-build-final")
        overrides[name,"stages/final/dependencies.py"]=s
    elif field=="install":
        s=item(name,"stages/final/produce-manifest.py")
        s["required"].remove("usr/bin/root-control")
        overrides[name,"stages/final/produce-manifest.py"]=s
    with pytest.raises(ValueError,match="NOT READY"):
        mod.verify(overrides=overrides)

def test_root_daemon_is_not_automatically_enabled_by_source_stage():
    stage=item("root-control","stages/final/build.py")
    assert "[Install]" not in stage["install"][0][-1]
    assert "ConditionPathIsMountPoint=/state" in stage["install"][0][-1]
    assert "User=root" in stage["install"][0][-1]
    contract=item("root-control","stages/final/integration.py")
    assert contract["unit_auto_enabled"] is False
    assert contract["socket_group"].startswith("installer-selected")

def test_box_control_does_not_get_a_global_daemon_service():
    output=item("box-control","stages/final/produce-manifest.py")
    assert not any("/systemd/system/" in path for path in output["required"])
    contract=item("box-control","stages/final/integration.py")
    assert contract["service_mode"]=="one-shot-project-evaluator"
    assert contract["auto_enable"] is False
    assert "HOME" in contract["working_directory"]

"""Adversarial Resident B controller wheel/source/service stage contract tests."""
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("resident_controller",ROOT/"tools/verify_resident_b_controller_stages.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_both_source_stages_authored_without_runtime_or_native_selection():
 assert mod.verify_all()=={
  "source_stages":2,"native_generation":"NO_GO","production_pins":"UNCHANGED"}
 assert not (ROOT/"project/package/python-dbus-next").exists()
 assert not (ROOT/"project/package/image-build-python").exists()

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_exact_upstream_tarball_source_provenance_and_output(name):
 assert mod.verify_one(name)["stage"]=="AUTHORED_SOURCE_ONLY"

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_changed_revision_digest_or_removed_exec_refused(name):
 stage=ROOT/"project/package"/name/"stages/final"
 sources=copy.deepcopy(mod.read(stage/"sources.py"))
 sources[0]["sha256"]="f"*64
 with pytest.raises(ValueError,match="archive"):
  mod.verify_one(name,source=sources)
 manifest=copy.deepcopy(mod.read(stage/"produce-manifest.py"))
 manifest["required"].remove(f"usr/bin/{name}")
 with pytest.raises(ValueError,match="required executable"):
  mod.verify_one(name,manifest=manifest)

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_changed_dependency_or_python_interpreter_cannot_pass(name):
 stage=ROOT/"project/package"/name/"stages/final"
 edges=copy.deepcopy(mod.read(stage/"dependencies.py"))
 edges["runtime"].remove("python-dbus-next-final")
 with pytest.raises(ValueError,match="dependency"):
  mod.verify_one(name,edges=edges)
 build=copy.deepcopy(mod.read(stage/"build.py"))
 build["build"][0][-1]=build["build"][0][-1].replace("python3.12","python3.15")
 with pytest.raises(ValueError,match="source wheel"):
  mod.verify_one(name,build=build)

def test_disabling_root_protection_or_enabling_systemd_is_refused():
 path=ROOT/"project/package/root-control/units/zog-root-control.service"
 unit=path.read_text()
 for wrong in (unit+"\n[Install]\nWantedBy=multi-user.target\n",
               unit.replace("User=root","User=nobody"),
               unit.replace("EnvironmentFile=/state/zog/root-control/controller.env",
                            "EnvironmentFile=-/state/zog/root-control/controller.env"),
               unit.replace("ConditionPathIsMountPoint=/state","ConditionPathExists=/state")):
  with pytest.raises(ValueError,match="service unit"):
   mod.verify_one("root-control",unit=wrong)

def test_box_control_is_not_an_invented_privileged_service():
 assert not (ROOT/"project/package/box-control/units").exists()
 assert mod.read(ROOT/"project/package/box-control/stages/final/produce-manifest.py")["required"]==[
  "usr/bin/box-control","usr/lib/python3.12/site-packages/zog/box_control/__init__.py",
  "usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/METADATA"]

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_package_source_metadata_must_match_exact_reviewed_source(name,tmp_path):
 expected=mod.EXPECTED[name]
 meta=tmp_path/"pyproject.toml"
 meta.write_text(f'''[build-system]
requires = ["setuptools>=80,<83"]
build-backend = "setuptools.build_meta"
[project]
name="{name}"
version="0.1.0"
dependencies = {expected["dependencies"]!r}
[project.scripts]
{name}="{expected["entry"]}"
''')
 assert mod.verify_one(name,upstream=meta)["stage"]=="AUTHORED_SOURCE_ONLY"
 meta.write_text(meta.read_text().replace("0.1.0","9.9.9"))
 with pytest.raises(ValueError,match="upstream"):
  mod.verify_one(name,upstream=meta)

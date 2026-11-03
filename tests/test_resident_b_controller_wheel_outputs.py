"""Require pinned controller wheel METADATA/RECORD and exact source dependency closure."""
import ast,copy,importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("resident_controller",ROOT/"tools/verify_resident_b_controller_source_stages.py")
verify=importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
def stage(name,part):
 return ast.literal_eval((ROOT/"project/package"/name/"stages/final"/part).read_text())

@pytest.mark.parametrize("name,expected",[
 ("box-control",["image-build==0.2.0.dev5","dbus-next==0.2.3"]),
 ("root-control",["box-control==0.1.0","image-build==0.2.0.dev5","dbus-next==0.2.3"])
])
def test_wheel_entrypoint_and_requires_dist_exact(name,expected):
 build=stage(name,"build.py")
 conf=build["configure"][0][-1];wheel=build["test"][0][-1]
 assert "unreviewed build backend" in conf
 assert 'meta["project"]["dependencies"]' in conf
 assert "version(requirement.name) in requirement.specifier" in conf
 assert "meta.get_all(\"Requires-Dist\")" in wheel
 assert "assert observed==expected" in wheel
 assert "dict(parser[\"console_scripts\"])" in wheel
 assert all(x in conf and x in wheel for x in expected)
 assert f'assert meta["Name"].replace("_","-").lower()=="{name}"' in wheel
 manifest=stage(name,"produce-manifest.py")
 module=name.replace("-","_")
 for leaf in ("METADATA","RECORD"):
  assert f"usr/lib/python3.12/site-packages/{module}-0.1.0.dist-info/{leaf}" in manifest["required"]

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_metadata_and_record_cannot_be_removed_as_required_outputs(name):
 path=f"project/package/{name}/stages/final/produce-manifest.py"
 original=stage(name,"produce-manifest.py")
 module=name.replace("-","_")
 for leaf in ("METADATA","RECORD"):
  changed=copy.deepcopy(original)
  changed["required"].remove(f"usr/lib/python3.12/site-packages/{module}-0.1.0.dist-info/{leaf}")
  with pytest.raises(ValueError,match="NOT READY"):
   verify.verify(overrides={(name,"stages/final/produce-manifest.py"):changed})

@pytest.mark.parametrize("name",["box-control","root-control"])
def test_exact_upstream_wheel_assertions_cannot_be_weakened(name):
 original=stage(name,"build.py")
 for source in ('"Requires-Dist"', '"unreviewed build backend"','"entry_points.txt"'):
  changed=copy.deepcopy(original)
  for key in ("configure","test"):
   changed[key][0][-1]=changed[key][0][-1].replace(source,'"removed-assertion"')
  with pytest.raises(ValueError,match="NOT READY"):
   verify.verify(overrides={(name,"stages/final/build.py"):changed})

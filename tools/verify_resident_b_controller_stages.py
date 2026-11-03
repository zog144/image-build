#!/usr/bin/env python3
"""Resident B boxed/root controller source recipe validation; never native acceptance."""
import ast
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/"project/package"
RECORD=json.loads((ROOT/"project/host/resident-b-controller-stage-contracts-v1.json").read_text())
EXPECTED={
 "box-control":{
  "revision":"b513a9bde79135c7569adc7cadb4d45a163c7841",
  "sha256":"60b95ae7842dd1a81f0e5891858e4a9035c629dbbc59c06f7793d4d1499bcf05",
  "entry":"zog.box_control.cli:main",
  "dependencies":["image-build==0.2.0.dev5","dbus-next==0.2.3"],
  "required":{"usr/bin/box-control","usr/lib/python3.12/site-packages/zog/box_control/__init__.py",
              "usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/METADATA"}},
 "root-control":{
  "revision":"0c217182d25f05b9cc0f7528ee614bb5669370d3",
  "sha256":"ecd2e33416b56c8e1124db4604af4128e77bee36175c49ebfd6671bbbb488d0f",
  "entry":"zog.root_control.daemon:main",
  "dependencies":["box-control==0.1.0","image-build==0.2.0.dev5","dbus-next==0.2.3"],
  "required":{"usr/bin/root-control","usr/lib/python3.12/site-packages/zog/root_control/__init__.py",
              "usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/METADATA",
              "usr/lib/python3.12/site-packages/zog/root_control/native/journal-wait.c",
              "usr/lib/systemd/system/zog-root-control.service"}},
}

def read(path):
 return ast.literal_eval(Path(path).read_text())

def ensure(ok, what):
 if not ok: raise ValueError(what)

def verify_one(name, *, source=None, provenance=None, package=None, build=None,
               manifest=None, edges=None, unit=None, integration=None, license=None,
               upstream=None):
 ensure(name in EXPECTED,"unexpected package")
 expected=EXPECTED[name]
 path=PACKAGE/name
 stage=path/"stages/final"
 package=read(path/"package.py") if package is None else package
 source=read(stage/"sources.py") if source is None else source
 provenance=read(stage/"source-provenance.py") if provenance is None else provenance
 build=read(stage/"build.py") if build is None else build
 manifest=read(stage/"produce-manifest.py") if manifest is None else manifest
 edges=read(stage/"dependencies.py") if edges is None else edges
 integration=read(stage/"integration.py") if integration is None else integration
 license=read(path/"license.py") if license is None else license
 base=f"https://api.github.com/repos/zog144/{name}/tarball/{expected['revision']}"
 ensure(package["name"]==name and package["status"]=="catalogue-only"
        and package["recipe_status"]=="stage-recipes-authored-unselected","unselected package")
 ensure(type(source) is list and len(source)==1 and source[0]=={
  "url":base,"sha256":expected["sha256"],"destination":"upstream","archive":True
 }, "exact source archive/revision/hash")
 ensure(provenance["schema"]==1 and len(provenance["sources"])==1
        and provenance["sources"][0]["source"]==source[0]
        and provenance["sources"][0]["upstream"]==[{
            "repository":f"https://github.com/zog144/{name}",
            "revision":expected["revision"],"revision_type":"git"
        }], "upstream revision provenance")
 ensure(integration["revision"]==expected["revision"]
        and integration["runtime_requirements"]==expected["dependencies"]
        and integration["patches"]==[],"runtime package source contract")
 ensure(license["source"]["sha256"]==expected["sha256"]
        and license["status"]=="declared-source-rights-review-pending"
        and license["evidence"]==[],"rights must remain pending")
 ensure(set(manifest)=={"trees","required"} and manifest["trees"]==["usr"]
        and set(manifest["required"])==expected["required"],"required executable/metadata/service outputs")
 ensure("usr/lib/python3.15" not in str(manifest),"Resident B Python ABI wrong")
 ensure(set(edges)=={"build","runtime"}
        and {"python-resident312-final","python-setuptools-final","python-wheel-final",
             "python-packaging-final","python-installer-final"}.issubset(edges["build"])
        and {"python-resident312-final","python-dbus-next-final",
             "image-build-python-final"}.issubset(edges["runtime"])
        and (name!="root-control" or
             {"box-control-final","dbus-final","systemd-final"}.issubset(edges["runtime"])),
        "held exact declared build/runtime dependency edges")
 ensure(set(build)=={"build","test","install","environment"}
        and all(len(build[k])==1 and build[k][0][:5]==
                ["/bin/bash","-eu","-o","pipefail","-c"] for k in
                ("build","test","install")),"package stage script layout")
 script=build["build"][0][-1]; test=build["test"][0][-1]; install=build["install"][0][-1]
 ensure(all(token in script for token in
        ("python3.12","cpython-312-x86_64-linux-gnu","pyproject.toml",
         expected["entry"],"setuptools.build_meta","missing selected build prerequisite")),
        "source wheel build metadata/ABI")
 ensure(all(token in test for token in
        ("python3.12","cpython-312-x86_64-linux-gnu","METADATA",
         "Requires-Dist","entry_points.txt",expected["entry"],
         "zog/"+name.replace("-","_")+"/__init__.py")),
        "source wheel required metadata test")
 ensure("python3.12 -m installer --destdir=" in install
        and f'test -x "$DESTDIR/usr/bin/{name}"' in install,
        "selected Python 3.12 console script installation")
 ensure(build["environment"]["PIP_NO_INDEX"]=="1"
        and build["environment"]["PYTHONNOUSERSITE"]=="1","offline build environment")
 if name=="root-control":
  unit=(path/"units/zog-root-control.service").read_text() if unit is None else unit
  ensure("[Install]" not in unit and "WantedBy=" not in unit
         and "User=root" in unit and "Group=root" in unit and "UMask=0077" in unit
         and "Type=exec" in unit and "Restart=no" in unit
         and "RequiresMountsFor=/state" in unit
         and "ConditionPathIsMountPoint=/state" in unit
         and "EnvironmentFile=/state/zog/root-control/controller.env" in unit
         and "ExecStart=/usr/bin/root-control" in unit
         and "RuntimeDirectory=zog" in unit
         and "/state/zog/root-control/controller.env" in install
         and unit.strip() in install,
         "unsafe or mismatched privileged service unit")
  ensure("multi-user.target.wants" in install
         and "test ! -e" in install,"service auto-enable forbidden")
 else:
  ensure(not (path/"units").exists() and "zog-box-control.service" not in install,
         "one-shot box-control must not gain invented daemon authority")
 if upstream is not None:
  metadata=tomllib.loads(Path(upstream).read_text())
  ensure(metadata["project"]["name"]==name
         and metadata["project"]["version"]=="0.1.0"
         and metadata["project"]["scripts"]=={name:expected["entry"]}
         and metadata["project"]["dependencies"]==expected["dependencies"]
         and metadata["build-system"]["build-backend"]=="setuptools.build_meta"
         and metadata["build-system"]["requires"]==["setuptools>=80,<83"],
         "selected upstream package metadata mismatch")
 return {"package":name,"revision":expected["revision"],
         "sha256":expected["sha256"],"stage":"AUTHORED_SOURCE_ONLY",
         "native":"NO_GO"}

def verify_all(*, box_upstream=None, root_upstream=None):
 ensure(RECORD["schema"]=="zog-resident-b-controller-stage-design-v2"
        and RECORD["status"]=="AUTHORED_SOURCE_STAGES_UNSELECTED_NATIVE_HOLD"
        and RECORD["source_selected"] is False
        and RECORD["compilation_allowed"] is False
        and RECORD["native_generation"] is None
        and RECORD["required_python_runtime"]["abi"]=="cpython-312-x86_64-linux-gnu"
        and RECORD["required_python_runtime"]["selected_generation_receipt"] is None,
        "source package cannot promote Resident B")
 ensure({x["id"] for x in RECORD["controllers"]}==set(EXPECTED),"controller source stage identities")
 for ctrl in RECORD["controllers"]:
  expected=EXPECTED[ctrl["id"]]
  ensure(ctrl["source_revision"]==expected["revision"] and
         ctrl["source_sha256"]==expected["sha256"] and
         ctrl["status"]=="AUTHORED_SOURCE_STAGE_HELD" and
         ctrl["version"]=="0.1.0" and
         ctrl["executable"]==f"usr/bin/{ctrl['id']}" and
         ctrl["runtime_services"]==([] if ctrl["id"]=="box-control" else
          ["usr/lib/systemd/system/zog-root-control.service"]),
         "resident B source design selection")
  verify_one(ctrl["id"],upstream=box_upstream if ctrl["id"]=="box-control" else root_upstream)
 ensure("NATIVE_INSTALLED_PROOF_ABSENT" in RECORD["holds"]
        and "PYTHON312_NOT_SELECTED" in RECORD["holds"]
        and "DEPENDENCY_GRAPH_INCOMPLETE_CP312" in RECORD["holds"],
        "native dependency hold erased")
 return {"source_stages":2,"native_generation":"NO_GO","production_pins":"UNCHANGED"}

if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser()
 parser.add_argument("--box-upstream")
 parser.add_argument("--root-upstream")
 args=parser.parse_args()
 print(json.dumps(verify_all(box_upstream=args.box_upstream,
                             root_upstream=args.root_upstream),sort_keys=True))

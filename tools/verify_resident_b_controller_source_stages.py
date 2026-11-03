#!/usr/bin/env python3
"""Read-only source closure for pinned, catalogue-only Resident B controllers."""
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"project/package"
AUDIT=ROOT/"project/host/resident-b-controller-stage-contracts-v1.json"
SOURCES={
"box-control":{
 "commit":"b513a9bde79135c7569adc7cadb4d45a163c7841",
 "archive":"60b95ae7842dd1a81f0e5891858e4a9035c629dbbc59c06f7793d4d1499bcf05",
 "archive_root":"zog144-box-control-b513a9b",
 "project":"zog144-box-control-b513a9b/box-control",
 "entry":"zog.box_control.cli:main",
 "pyproject_sha256":"a099487955e9b42e90aed4103cb32e76f7dae0535692534c25b7be2f09a4eb47",
 "license":"aaf3d5919ea7f2720b7649d4f1e4fd28a54c58425a45dfd736d040a56480578f",
 "notice":"b6636714adafd8c7c8e9ab1db2d07e3c7efe3b312fa10268bc393b83e1db7036",
 "runtime":{"python-resident312-final","image-build-python-final","dbus-next-final"},
 "required":{"usr/bin/box-control","usr/lib/python3.12/site-packages/zog/box_control/__init__.py",
             "usr/share/licenses/box-control/LICENSE",
             "usr/share/licenses/box-control/THIRD-PARTY-NOTICES.md"},
},
"root-control":{
 "commit":"0c217182d25f05b9cc0f7528ee614bb5669370d3",
 "archive":"ecd2e33416b56c8e1124db4604af4128e77bee36175c49ebfd6671bbbb488d0f",
 "archive_root":"zog144-root-control-0c21718",
 "project":"zog144-root-control-0c21718",
 "entry":"zog.root_control.daemon:main",
 "pyproject_sha256":"f42d1b9458536b4b20aef183d438267b0790bb8fc9238afcc10b9a1bc62b1c96",
 "license":"421a457ded4d2bf4b853c5ce211f74797292b2ef2f82bc7245304956fb7cf68f",
 "notice":"b3aa6c652c70db0faecdd42d35723c62bc61282dc53d73f637f26e",
 "runtime":{"python-resident312-final","image-build-python-final","dbus-next-final",
            "box-control-final","systemd-final"},
 "required":{"usr/bin/root-control","usr/lib/python3.12/site-packages/zog/root_control/__init__.py",
            "usr/share/licenses/root-control/LICENSE","usr/share/licenses/root-control/THIRD-PARTY-NOTICES.md",
            "usr/lib/python3.12/site-packages/zog/root_control/native/journal-wait.c",
            "usr/lib/systemd/system/zog-root-control.service"},
},
}
BUILD_TOOLS={"python-resident312-final","setuptools-final","packaging-final","installer-final","wheel-final"}
UNRESOLVED={"setuptools-final","packaging-final","installer-final","wheel-final",
            "image-build-python-final","dbus-next-final"}
def data(path):
    return ast.literal_eval(path.read_text())
def deny(message):
    raise ValueError("Resident B controller native NOT READY: "+message)

def verify(*, records=None, overrides=None):
    record=records if records is not None else json.loads(AUDIT.read_text())
    if (record.get("schema")!="zog-resident-b-controller-stage-design-v1" or
        record.get("status")!="CATALOGUE_ONLY_SOURCE_STAGES_AUTHORED_NATIVE_NO_GO" or
        record.get("source_selected") is not False or
        record.get("compilation_allowed") is not False or
        record.get("native_generation") is not None):
        deny("source contract falsely promoted")
    reviewed={p["id"]:p for p in record.get("controllers",[])}
    if set(reviewed)!=set(SOURCES) or len(record["controllers"])!=len(SOURCES):
        deny("controller source omitted or duplicated")
    overrides=overrides or {}
    for name,expected in SOURCES.items():
        base=PKG/name
        def read(relative):
            if (name,relative) in overrides:return overrides[name,relative]
            return data(base/relative)
        pkg=read("package.py")
        sources=read("stages/final/sources.py")
        license=read("license.py")
        deps=read("stages/final/dependencies.py")
        manifest=read("stages/final/produce-manifest.py")
        build=read("stages/final/build.py")
        integration=read("stages/final/integration.py")
        entry=reviewed[name]
        if (pkg.get("status")!="catalogue-only" or pkg.get("source_revision")!=expected["commit"]
           or pkg.get("source_archive_sha256")!=expected["archive"]
           or pkg.get("version")!="0.1.0" or
            entry.get("source_revision")!=expected["commit"] or
            entry.get("archive_sha256")!=expected["archive"] or
            entry.get("status")!="CATALOGUE_ONLY_SOURCE_STAGE_AUTHORED"):
            deny("source pin changed or native admitted: "+name)
        original={"url":f"https://api.github.com/repos/zog144/{name}/tarball/{expected['commit']}",
                  "sha256":expected["archive"],"destination":"upstream","archive":True}
        if sources!=[original] or license.get("source")!={**{k:original[k] for k in ("url","sha256")}, "commit":expected["commit"]}:
            deny("original tarball identity differs: "+name)
        if license.get("status")!="unresolved" or license.get("expression")!="BSD-3-Clause OR GPL-3.0-only":
            deny("original source rights improperly approved: "+name)
        evidence={e["path"]:e["sha256"] for e in license.get("evidence",[])}
        root=expected["archive_root"]
        if (evidence.get(root+"/LICENSE")!=expected["license"] or
            evidence.get(root+"/THIRD-PARTY-NOTICES.md")!=expected["notice"] or
            evidence.get(root+("/box-control/pyproject.toml" if name=="box-control" else "/pyproject.toml"))!=expected["pyproject_sha256"]):
            deny("actual original archive member identity missing: "+name)
        if (set(deps.get("build",[]))!=
              BUILD_TOOLS|({"box-control-final"} if name=="root-control" else set()) or
            set(deps.get("runtime",[]))!=expected["runtime"]):
            deny("missing Python/companion/build tool dependency: "+name)
        if set(manifest.get("required",[]))!=expected["required"] or manifest.get("trees")!=["usr"]:
            deny("missing exact installed program, notice or service source contract: "+name)
        if (integration.get("status")!="SOURCE_DEFINED_NATIVE_NOT_ACCEPTED" or
            integration.get("native_accepted") is not False or
            integration.get("source_grant") is not False or
            integration.get("rights_approved") is not False or
            integration.get("auto_enable") is not False or
            integration.get("source_revision")!=expected["commit"] or
            integration.get("installed_entrypoint")!="usr/bin/"+name):
            deny("source-only installation falsely admitted: "+name)
        for phase in ("configure","build","test","install"):
            steps=build.get(phase,[])
            if (len(steps)!=1 or steps[0][:5]!=["/bin/bash","-eu","-o","pipefail","-c"]):
                deny("controller native build phase changed: "+name+"/"+phase)
        combined="\n".join(build[phase][0][-1] for phase in ("configure","build","test","install"))
        for required in (expected["project"],expected["pyproject_sha256"],expected["license"],
                         expected["notice"],"python3.12 -I","python3.12 -I -m installer",
                         "source" if False else "ZOG_CONTROLLER_WHEEL_SOURCE_TEST_PASS"):
            if required not in combined:
                deny("original/pinned build or wheel contract missing: "+name)
        if name=="box-control":
            if (integration.get("service_mode")!="one-shot-project-evaluator" or
                integration.get("unit_installed") is not False or
                "usr/lib/systemd/system/zog-box-control.service" in manifest["required"]):
                deny("box-control one-shot service falsely enabled")
        else:
            unit=build["install"][0][-1]
            for req in ("ConditionPathIsMountPoint=/state","RequiresMountsFor=/state",
                        "ExecStart=/usr/bin/root-control","User=root",
                        "Group=root","Environment=ROOT_CONTROL_JOURNAL_BARRIER=0"):
                if req not in unit:
                    deny("root-control source service lost mount/privilege protection")
            if ("[Install]" in unit or integration.get("unit_auto_enabled") is not False or
                integration.get("service_mode")!="privileged systemd daemon"):
                deny("root-control service unexpectedly auto-enabled")
    return {"source_stages":"PINNED_AND_HELD","archive_member_provenance":"EXACT_SHA256",
            "unresolved_transitive_stage_producers":sorted(UNRESOLVED),
            "native_generation":None,"authorization":"NO_GO"}

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))

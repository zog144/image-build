#!/usr/bin/env python3
"""Fail-closed exact source review for Resident B cp312. Never native admission."""
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"project/package"
PINS={
"flit-core":("flit_core","3.12.0","18f63100d6f94385c6ed57a72073443e1a71a4acb4339491615d0f16d6ff01b2",[],[]),
"installer":("installer","1.0.1","052c7fc3721d54c696e2dea019be67539d7b144e924f559f54beb3121831c364",["flit-core"],[]),
"packaging":("packaging","26.3","94edc256424af38762eb31306eed28beb9f0efc50a8837492c9d6fd6004aed79",["flit-core","installer"],[]),
"wheel":("wheel","0.48.0","94800765601e9171bf5d58d066e640662842bcedcbab982b2c90787a2c987322",["flit-core","installer","packaging"],["packaging"]),
"setuptools":("setuptools","82.0.1","7d872682c5d01cfde07da7bccc7b65469d3dca203318515ada1de5eda35efbf9",["packaging","installer","wheel"],[]),
"dbus-next":("dbus-next","0.2.3","f4eae26909332ada528c0a3549dda8d4f088f9b365153952a408e28023a626a5",["setuptools","wheel","installer","packaging"],[]),
"image-build":("image-build","0.2.0.dev5","74ca7fe804e08eb6102ca7ce2e227476aa8f448872cec08b6d6b1fab60b4f376",["setuptools","wheel","installer","packaging"],[]),
}
URLS={
"flit-core":"https://files.pythonhosted.org/packages/69/59/b6fc2188dfc7ea4f936cd12b49d707f66a1cb7a1d2c16172963534db741b/flit_core-3.12.0.tar.gz",
"installer":"https://files.pythonhosted.org/packages/06/fe/b9f481cf0cc867958a21338baa900357b7b7d86cac9b025948049d77923c/installer-1.0.1.tar.gz",
"packaging":"https://files.pythonhosted.org/packages/7d/fa/3944b40b07da9ce895c0e6303a5ab7d53da063554f534556b134a54d6093/packaging-26.3.tar.gz",
"wheel":"https://files.pythonhosted.org/packages/d0/20/50ed6bdf27dec98b568a8ae25dc599f35baa3d9709f9e83fd1edb56b9a90/wheel-0.48.0.tar.gz",
"setuptools":"https://files.pythonhosted.org/packages/4f/db/cfac1baf10650ab4d1c111714410d2fbb77ac5a616db26775db562c8fab2/setuptools-82.0.1.tar.gz",
"dbus-next":"https://files.pythonhosted.org/packages/ce/45/6a40fbe886d60a8c26f480e7d12535502b5ba123814b3b9a0b002ebca198/dbus_next-0.2.3.tar.gz",
"image-build":"https://api.github.com/repos/zog144/image-build/tarball/1f07e83dbd80dacb9bed0d6494c697375f0e26cd",
}
MODULE={"flit-core":"flit_core","dbus-next":"dbus_next","image-build":"zog/image_build"}
CONTROLLERS={
 "box-control":{"build":["python-resident312-final","resident312-setuptools-final","resident312-packaging-final","resident312-installer-final","resident312-wheel-final"],
                "runtime":["python-resident312-final","resident312-image-build-final","resident312-dbus-next-final"]},
 "root-control":{"build":["python-resident312-final","resident312-setuptools-final","resident312-packaging-final","resident312-installer-final","resident312-wheel-final","box-control-final"],
                 "runtime":["python-resident312-final","resident312-image-build-final","resident312-dbus-next-final","box-control-final","systemd-final"]}
}
SITE="usr/lib/python3.12/site-packages"
def literal(path):
    return ast.literal_eval(path.read_text())
def deny(reason):
    raise ValueError("Resident B transitive source NO-GO: "+reason)
def verify(*, overrides=None, controllers=None):
    overrides=overrides or {}
    def read(name,part):
        return overrides[(name,part)] if (name,part) in overrides else literal(PKG/name/part)
    for key,(dist,version,sha,build_deps,runtime_deps) in PINS.items():
        name="resident312-"+key
        pkg=read(name,"package.py")
        sources=read(name,"stages/final/sources.py")
        deps=read(name,"stages/final/dependencies.py")
        outputs=read(name,"stages/final/produce-manifest.py")
        build=read(name,"stages/final/build.py")
        license=read(name,"license.py")
        integration=read(name,"stages/final/integration.py")
        if (type(pkg) is not dict or pkg.get("name")!=name or pkg.get("version")!=version or
            pkg.get("status")!="catalogue-only" or pkg.get("original_source_sha256")!=sha or
            pkg.get("intended_interpreter")!="/usr/bin/python3.12" or
            pkg.get("production_python315_unchanged") is not True):
            deny("unselected package or source version drift: "+name)
        if sources!=[{"url":URLS[key],"sha256":sha,"destination":"upstream","archive":True}]:
            deny("original source archive substituted: "+name)
        if (license.get("status")!="unresolved" or license.get("evidence")!=[] or
            license.get("source",{}).get("sha256")!=sha or license.get("source",{}).get("url")!=URLS[key]):
            deny("source provenance/rights incorrectly approved: "+name)
        if key=="image-build" and license["source"].get("commit")!="1f07e83dbd80dacb9bed0d6494c697375f0e26cd":
            deny("image-build interface commit substituted")
        expected={"build":["python-resident312-final"]+["resident312-"+x+"-final" for x in build_deps],
                  "runtime":["python-resident312-final"]+["resident312-"+x+"-final" for x in runtime_deps]}
        if deps!=expected:
            deny("missing source-stage edge or undeclared Host tool: "+name)
        module=MODULE.get(key,dist)
        dinfo=dist.replace("-","_")+"-"+version+".dist-info"
        required={SITE+"/"+module+"/__init__.py",SITE+"/"+dinfo+"/METADATA",SITE+"/"+dinfo+"/RECORD"}
        if (outputs.get("trees")!=["usr"] or set(outputs.get("required",[]))!=required or
            len(outputs["required"])!=3):
            deny("missing CPython312 exact installed module/metadata/RECORD: "+name)
        if (integration.get("status")!="SOURCE_ONLY_NATIVE_NO_GO" or
            integration.get("python_abi")!="cpython-312-x86_64-linux-gnu" or
            integration.get("source_archive_sha256")!=sha or
            integration.get("selected_generation_id") is not None or
            integration.get("selected_predecessor_receipts") is not None or
            integration.get("installed_wheel_RECORD_verified") is not False or
            integration.get("toolchain_origin_proven") is not False or
            any(integration.get(k) is not False for k in
                ("compiler_submission_allowed","install_allowed","rights_approved"))):
            deny("fabricated native proof/authority: "+name)
        if key=="image-build" and integration.get("source_commit")!="1f07e83dbd80dacb9bed0d6494c697375f0e26cd":
            deny("image-build interface source revision drift")
        if set(build)!={"configure","build","test","install","environment"}:
            deny("stage build phase omitted: "+name)
        env={"PATH":"/usr/bin:/bin","PYTHONNOUSERSITE":"1","PYTHONSAFEPATH":"1",
             "PIP_NO_INDEX":"1","PKG_CONFIG_LIBDIR":"/usr/lib/pkgconfig:/usr/share/pkgconfig",
             "PKG_CONFIG_SYSROOT_DIR":"/"}
        if build["environment"]!=env:
            deny("Host build environment changed: "+name)
        scripts={}
        for phase in ("configure","build","test","install"):
            steps=build[phase]
            if type(steps) is not list or len(steps)!=1 or steps[0][:5]!=["/bin/bash","-eu","-o","pipefail","-c"]:
                deny("uncontrolled build phase: "+name+"/"+phase)
            script=steps[0][5]
            scripts[phase]=script
            if "/usr/bin/python3.12 -I" not in script or any(
                 bad in script for bad in ("python3.15", "/host/", "pip install", "PYTHONPATH=")):
                deny("Host Python fallback: "+name+"/"+phase)
        for token in ("sys.flags.isolated","sys.executable=='/usr/bin/python3.12'",
                      "importlib.metadata.version","spec.origin.startswith('/usr/lib/python3.12/site-packages/')"):
            if token not in scripts["configure"]:
                deny("selected source tool/module origin unverified: "+name)
        for token in ("dist-info/METADATA","dist-info/RECORD","m['Version']=='"+version+"'"):
            if token not in scripts["test"]:
                deny("wheel metadata or RECORD verification missing: "+name)
        for path in required:
            if path not in scripts["install"]:
                deny("stage output not asserted: "+name)
        if "DESTDIR" not in scripts["install"]:
            deny("writable installation outside selected DESTDIR")
    graph=controllers if controllers is not None else {
        k:read(k,"stages/final/dependencies.py") for k in CONTROLLERS}
    if graph!=CONTROLLERS:
        deny("controller selects stale 3.15 or undeclared source dependency")
    if "setuptools-84.0.0" not in literal(PKG/"python-setuptools/stages/final/sources.py")[0]["url"]:
        deny("incumbent Python 3.15 source changed without review")
    if literal(PKG/"python/stages/final/upstream.py").get("version")!="3.15.0rc2":
        deny("incumbent Python 3.15 repinned")
    return {"source_chain":"SEVEN_PINNED_CP312_CANDIDATES",
            "source_stage_predecessors":"EXACT","native_tool_origin":"NOT_ACCEPTED",
            "native_generation":None,"compiler_authorization":False}
if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))

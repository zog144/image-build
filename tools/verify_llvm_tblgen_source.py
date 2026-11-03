#!/usr/bin/env python3
"""LLVM TableGen -> Mesa source-only requirement, never native admission."""
import ast
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DRAFT=ROOT/"project/graphics-drafts"
def lit(path):return ast.literal_eval(path.read_text())
def deny(reason):raise ValueError("LLVM TableGen source NOT READY: "+reason)
def verify(*,llvm=None,manifest=None,mesa=None,dependencies=None,rights=None):
    llvm=llvm if llvm is not None else lit(DRAFT/"llvm/stages/final/build.py")
    manifest=manifest if manifest is not None else lit(DRAFT/"llvm/stages/final/produce-manifest.py")
    mesa=mesa if mesa is not None else lit(DRAFT/"mesa/stages/final/build.py")
    dependencies=dependencies if dependencies is not None else lit(DRAFT/"mesa/stages/final/dependencies.py")
    rights=rights if rights is not None else json.loads((DRAFT/"rights-admission-evidence.json").read_text())
    src=lit(DRAFT/"llvm/stages/final/sources.py")[0]
    package=lit(DRAFT/"llvm/package.py")
    if src.get("sha256")!="908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad" or package.get("status")!="catalogue-only":
        deny("source pin or catalogue-only state changed")
    for name,recipe in (("LLVM",llvm),("Mesa",mesa)):
        for phase in ("configure","build","test","install"):
            if type(recipe.get(phase)) is not list or len(recipe[phase])!=1 or recipe[phase][0][:5]!=["/bin/bash","-eu","-o","pipefail","-c"]:
                deny("unexpected stage shell "+name+"/"+phase)
    lc={k:llvm[k][0][-1] for k in ("configure","build","test","install")}
    mc=mesa["configure"][0][-1]
    for token in ("-DLLVM_TARGETS_TO_BUILD=X86","-DLLVM_ENABLE_RTTI=ON",
                  "-DLLVM_BUILD_LLVM_DYLIB=ON","-DCMAKE_INSTALL_PREFIX=/usr"):
        if token not in lc["configure"]:deny("LLVM pinned X86 configuration drift")
    for phase,token in (
        ("build","cmake --build build-llvm --target llvm-tblgen --parallel 2"),
        ("test","test -x build-llvm/bin/llvm-tblgen"),
        ("install",'install -Dm755 build-llvm/bin/llvm-tblgen "$DESTDIR/usr/bin/llvm-tblgen"'),
        ("install",'test -x "$DESTDIR/usr/bin/llvm-tblgen"'),
        ("install",'test -x "$DESTDIR/usr/bin/llvm-config"')):
        if token not in lc[phase]:deny("LLVM TableGen build/test/install output absent: "+phase)
    if ("DESTDIR" not in lc["install"] or
        manifest.get("trees")!=["usr"] or
        type(manifest.get("required")) is not list or
        len(manifest["required"])!=len(set(manifest["required"])) or
        set(manifest["required"])!={"usr/bin/llvm-config","usr/bin/llvm-tblgen",
            "usr/lib/libLLVM.so","usr/share/licenses/llvm/LICENSE.TXT",
            "usr/share/licenses/llvm/BLAKE3-LICENSE"}):
        deny("installed executable or original LLVM/notice outputs omitted")
    if ("llvm-final" not in dependencies.get("build",[]) or
        "llvm-final" not in dependencies.get("runtime",[]) or
        "test -x /usr/bin/llvm-tblgen" not in mc or
        "ZOG_GRAPHICS_TOOLCHAIN_VERIFIER" not in mc or
        "--phase mesa" not in mc or
        "llvm-config --has-rtti" not in mc):
        deny("Mesa source generator could proceed without selected LLVM tool")
    row=rights.get("components",{}).get("llvm",{})
    if (rights.get("status")!="independent-rights-and-native-output-NO-GO" or
        rights.get("rights_approved") is not False or
        rights.get("canonical_admitted") is not False or
        row.get("installed_outputs_observed") is not False or
        row.get("notice_delivery_verified") is not False or
        row.get("expected_output_paths")!=manifest["required"] or
        not any("TableGen" in x for x in row.get("outstanding",[]))):
        deny("native generation or original rights prematurely approved")
    if (ROOT/"project/package/llvm").exists():deny("LLVM draft masquerades as canonical package")
    return {"source":"LLVM_TABLEGEN_REQUIRED_FOR_MESA","source_gate":"PASS",
            "native_installed_output":None,"source_compilation_executed":False,
            "rights_approved":False,"compiler_submission_authorized":False}
if __name__=="__main__":print(json.dumps(verify(),sort_keys=True))

"""Adversarial LLVM TableGen and Mesa generator source-stage obligations."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("tblgen",ROOT/"tools/verify_llvm_tblgen_source.py")
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def fixture():
    return [
        ast.literal_eval((m.DRAFT/"llvm/stages/final/build.py").read_text()),
        ast.literal_eval((m.DRAFT/"llvm/stages/final/produce-manifest.py").read_text()),
        ast.literal_eval((m.DRAFT/"mesa/stages/final/build.py").read_text()),
        ast.literal_eval((m.DRAFT/"mesa/stages/final/dependencies.py").read_text()),
        json.loads((m.DRAFT/"rights-admission-evidence.json").read_text())
    ]
def check(x):return m.verify(llvm=x[0],manifest=x[1],mesa=x[2],dependencies=x[3],rights=x[4])
def test_source_is_held_but_tablegen_output_declared():
    r=m.verify()
    assert r["source_gate"]=="PASS"
    assert r["native_installed_output"] is None
    assert r["source_compilation_executed"] is False
    assert r["compiler_submission_authorized"] is False
@pytest.mark.parametrize("phase,token",[
    ("build","cmake --build build-llvm --target llvm-tblgen --parallel 2"),
    ("test","test -x build-llvm/bin/llvm-tblgen"),
    ("install",'install -Dm755 build-llvm/bin/llvm-tblgen "$DESTDIR/usr/bin/llvm-tblgen"'),
    ("install",'test -x "$DESTDIR/usr/bin/llvm-tblgen"')])
def test_build_test_or_install_obligation_cannot_be_deleted(phase,token):
    x=copy.deepcopy(fixture());assert token in x[0][phase][0][-1]
    x[0][phase][0][-1]=x[0][phase][0][-1].replace(token,"")
    with pytest.raises(ValueError,match="NOT READY"):check(x)
@pytest.mark.parametrize("required",[
    "usr/bin/llvm-tblgen","usr/lib/libLLVM.so","usr/share/licenses/llvm/BLAKE3-LICENSE"])
def test_installed_manifest_must_keep_tool_runtime_and_original_notice(required):
    x=copy.deepcopy(fixture());x[1]["required"].remove(required)
    with pytest.raises(ValueError,match="NOT READY"):check(x)
@pytest.mark.parametrize("token",[
    "test -x /usr/bin/llvm-tblgen","ZOG_GRAPHICS_TOOLCHAIN_VERIFIER","--phase mesa"])
def test_mesa_configure_cannot_skip_selected_generator_or_provenance(token):
    x=copy.deepcopy(fixture());x[2]["configure"][0][-1]=x[2]["configure"][0][-1].replace(token,"")
    with pytest.raises(ValueError,match="NOT READY"):check(x)
def test_mesa_llvm_stage_edge_is_required_for_build_and_runtime():
    for part in ("build","runtime"):
        x=copy.deepcopy(fixture());x[3][part].remove("llvm-final")
        with pytest.raises(ValueError,match="NOT READY"):check(x)
def test_source_licensing_and_generation_status_stay_held():
    for key in ("rights_approved","canonical_admitted"):
        x=copy.deepcopy(fixture());x[4][key]=True
        with pytest.raises(ValueError,match="NOT READY"):check(x)
    x=copy.deepcopy(fixture());x[4]["components"]["llvm"]["installed_outputs_observed"]=True
    with pytest.raises(ValueError,match="NOT READY"):check(x)
    assert not (ROOT/"project/package/llvm").exists()

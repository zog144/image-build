"""Source contracts for exact original-rights questions, not native evidence."""
import ast
import importlib.util
import io
import json
from pathlib import Path
import tarfile
from copy import deepcopy
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rights_questions",ROOT/"tools/inspect_mesa_original_rights_questions.py")
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

def example(name):
    items={}
    for relative in tool.SELECTED[name]["members"]:
        items[relative]=b"rights-original-bytes "+relative.encode()
    for prefix in tool.SELECTED[name]["prefixes"]:
        items[prefix+"candidate.c"]=b"/* only a source candidate, NOT a selected object */"
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode="w") as archive:
        for relative, data in items.items():
            entry=tarfile.TarInfo(name="original/"+relative)
            entry.size=len(data)
            archive.addfile(entry,io.BytesIO(data))
    import hashlib
    raw=buf.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()

@pytest.mark.parametrize("name",sorted(tool.SELECTED))
def test_original_source_scope_is_not_native_acceptance(name):
    raw,digest=example(name)
    output=tool.inspect(name,raw,source_sha=digest)
    assert output["independent_rights_approved"] is False
    assert output["canonical_admitted"] is False
    assert output["native_selected_compilation"]=="not observed"
    assert set(output["selected_original_members"])==set(tool.SELECTED[name]["members"])
    with pytest.raises(ValueError, match="digest"):
        tool.inspect(name,raw,source_sha="0"*64)
    assert tool.original_pin(name)[1]==ast.literal_eval(
        (tool.ROOT/name/"license.py").read_text())["source"]["sha256"]

@pytest.mark.parametrize("name",sorted(tool.SELECTED))
def test_absent_upstream_candidate_fail_closed(name):
    raw,digest=example(name)
    old=tool.SELECTED[name]
    tool.SELECTED[name]={**old,"members":(*old["members"],"not-real/LICENSE")}
    try:
        with pytest.raises(ValueError,match="missing"):
            tool.inspect(name,raw,source_sha=digest)
    finally:
        tool.SELECTED[name]=old

def test_held_feature_selection_is_explicit_in_selected_source_recipes():
    data={n:ast.literal_eval((tool.ROOT/n/"stages/final/build.py").read_text())
          for n in tool.SELECTED}
    llvm=data["llvm"]["configure"][0][-1]
    mesa=data["mesa"]["configure"][0][-1]
    drm=data["libdrm"]["configure"][0][-1]
    demos=data["mesa-demos"]["configure"][0][-1]
    for flag in ("-DLLVM_ENABLE_RTTI=ON","-DLLVM_TARGETS_TO_BUILD=X86",
                 "-DLLVM_INCLUDE_TESTS=OFF"):
        assert flag in llvm
    for flag in ("-Dgallium-drivers=swrast","-Dvulkan-drivers=",
                 "-Degl=disabled","-Dgbm=disabled","-Dauto_features=disabled"):
        assert flag in mesa
    for flag in ("-Dintel=disabled","-Dradeon=disabled","-Damdgpu=disabled",
                 "-Dnouveau=disabled","-Dudev=False","-Dtests=False"):
        assert flag in drm
    for flag in ("-Dvulkan=disabled","-Degl=disabled","-Dglut=disabled",
                 "-Dauto_features=disabled"):
        assert flag in demos
    rights=json.loads((tool.ROOT/"rights-admission-evidence.json").read_text())
    assert rights["rights_approved"] is False
    assert rights["canonical_admitted"] is False
    assert not rights["review_scope"]["compile_commands_received"]

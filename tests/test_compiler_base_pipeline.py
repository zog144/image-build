"""Exercise the real remote submit, durable prepare/resume and graphical merge gates.

All test-only signed compiler receipts come from disposable local fixtures.
No native authenticated Host or compiler job is created.
"""
from pathlib import Path
from types import SimpleNamespace
import copy

import pytest

from zog.image_build import compiler_base_acceptance as ca
from zog.image_build import graphical_composition as gc
from zog.image_build import pipeline as pipeline_module
from zog.image_build.engine import ImageBuild
from zog.image_build.errors import ImageBuildError
from zog.image_build.remote_operations import RemoteOperations
from zog.image_build.metadata import identity
from test_compiler_base_acceptance import signed_fixture

SOURCE="1f07e83dbd80dacb9bed0d6494c697375f0e26cd"

def remote(builder,selection,receipt):
    adapter=RemoteOperations.__new__(RemoteOperations)
    adapter.builder=builder
    adapter.source_revision=SOURCE
    snapshot=SimpleNamespace(
        snapshot="sha256:"+"e"*64,
        manifest={"packages":{x:"fixture" for x in gc.FONTS}})
    adapter._resolve_recipe_snapshot=lambda _:snapshot
    adapter._validate_submit_snapshot_predecessor=lambda *_:None
    adapter._generation=lambda _:selection
    request={
        "arguments":{
            "mode":"image","selection":selection.generation,
            "targets":list(gc.FONTS),"recipe_snapshot":snapshot.snapshot,
            **({"compiler_base":receipt} if receipt is not None else {}),
        }
    }
    return adapter,request

def test_remote_fonts_submittable_shape_requires_actual_independently_signed_base(tmp_path):
    builder,selection,claim,policy,sign=signed_fixture(tmp_path)
    ref=sign()
    adapter,request=remote(builder,selection,ref)
    mode,selected,arguments,snapshot=adapter._pipeline_arguments(request)
    assert mode=="image"
    assert selected.generation==claim["generation_id"]
    assert arguments["compiler_base"]==ref
    assert snapshot.snapshot==request["arguments"]["recipe_snapshot"]
    del request["arguments"]["compiler_base"]
    with pytest.raises(ImageBuildError,match="lacks independent compiler base"):
        adapter._pipeline_arguments(request)

def test_remote_refuses_signed_looking_stale_receipt_and_wrong_mode(tmp_path):
    builder,selection,claim,policy,sign=signed_fixture(tmp_path)
    adapter,request=remote(builder,selection,"sha256:"+"f"*64)
    with pytest.raises(ImageBuildError,match="receipt"):
        adapter._pipeline_arguments(request)
    request["arguments"]["mode"]="native-check"
    with pytest.raises(ImageBuildError,match="image-mode only"):
        adapter._pipeline_arguments(request)

def test_real_pipeline_prepare_and_resume_freeze_receipt_before_work(monkeypatch,tmp_path):
    builder,selection,claim,policy,sign=signed_fixture(tmp_path)
    receipt=sign()
    b=ImageBuild.__new__(ImageBuild)
    b.state=builder.state
    b.package_dir=tmp_path/"recipes"
    b.package_dir.mkdir()
    (b.package_dir/"fixture").write_text("synthetic-only")
    b.provenance=SimpleNamespace(
        pin={"revision":SOURCE},configuration=lambda:{"schema":2,"source":"synthetic"})
    b.runner=builder.runner
    b.source_mirror=None
    b.dependency_replacements={}
    b.maximum_generations=10
    b.compiler_base_authority=policy
    import zog.image_build.pins as pins
    monkeypatch.setattr(pins,"validate",lambda *args,**kwargs:{"pinned":"fixture"})
    monkeypatch.setattr(pipeline_module,"load_packages",lambda *args,**kwargs:{})
    args={"targets":list(gc.FONTS),"compiler_base":receipt}
    record=b._prepare_pipeline("image",selection,**args)
    assert record["arguments"]["compiler_base"]==receipt
    assert record["selection"]==str(Path(selection.root).parent.resolve())
    assert "compiler_base_authority_identity" in record["policy"]
    # Reusing a saved pipeline does not produce a new native command or issue.
    calls=[]
    b._ensure=lambda targets,**kw:(calls.append((targets,kw)),
       SimpleNamespace(generation="a"*64))[1]
    b._publish_observation_snapshot=lambda _:None
    out=b._continue_pipeline(
        b._pipeline_directory(record["pipeline_id"]),record)
    assert out.generation=="a"*64
    assert len(calls)==1
    assert calls[0][1]["compiler_base"]==receipt
    assert calls[0][1]["toolchain"].generation==selection.generation

def test_preparation_requires_same_selected_signed_original_receipt(tmp_path,monkeypatch):
    builder,selection,claim,policy,sign=signed_fixture(tmp_path)
    b=ImageBuild.__new__(ImageBuild)
    b.state=builder.state
    b.package_dir=tmp_path/"recipes"
    b.package_dir.mkdir()
    b.provenance=SimpleNamespace(pin={"revision":SOURCE},
                                 configuration=lambda:{"schema":2})
    b.runner=builder.runner
    b.source_mirror=None
    b.dependency_replacements={}
    b.compiler_base_authority=policy
    import zog.image_build.pins as pins
    monkeypatch.setattr(pins,"validate",lambda *a:{"fixture":"ok"})
    monkeypatch.setattr(pipeline_module,"load_packages",lambda *a:{})
    with pytest.raises(ImageBuildError,match="requires accepted compiler"):
        b._prepare_pipeline("image",selection,targets=list(gc.FONTS))
    with pytest.raises(ImageBuildError,match="receipt"):
        b._prepare_pipeline("image",selection,targets=list(gc.FONTS),
                           compiler_base="sha256:"+"d"*64)
    assert not (b.state/"image-build/pipelines").exists()

def test_graphical_fonts_predecessor_accepts_image_compiler_without_relabel(monkeypatch,tmp_path):
    base=SimpleNamespace(
        generation="a"*64,
        manifest={"kind":"image","inputs":{"kind":"image","architecture":"x86_64"}})
    bound={"schema":ca.BINDING,"generation_id":base.generation,
        "generation_kind":"image","status":
            "independent-compiler-capability-observed-not-job-authorization"}
    verified=SimpleNamespace(generation="b"*64,root=tmp_path/"fonts",
           manifest={"kind":"image","build_record":{"record":"sha256:"+"c"*64}})
    original={
        "kind":"image","inputs":{"kind":"image","toolchain":base.generation,
             "architecture":"x86_64","targets":list(gc.FONTS)},
        "verification_execution":{"exit_code":0,"cleanup_complete":True},
        "build_record":{"record":"sha256:"+"c"*64},
    }
    calls=[]
    monkeypatch.setattr(gc,"_canonical_selection",lambda *_:verified)
    monkeypatch.setattr(gc,"_verified",lambda _b,_selected,_base,_targets:
                        (calls.append(_base.generation),original)[1])
    fake=SimpleNamespace(state=tmp_path,provenance=None)
    # Never infer acceptance from kind=image alone.
    with pytest.raises(ImageBuildError,match="separately accepted compiler base"):
        gc.validate(fake,base,verified.generation,list(gc.XCB))
    result=gc.validate(fake,base,verified.generation,list(gc.XCB),
                       compiler_base=bound)
    assert result["stage"]=="fonts"
    assert result["generation"]==verified.generation
    assert base.manifest["kind"]=="image"
    assert calls==[base.generation]
    assert result["manifest_sha256"].startswith("sha256:")

"""First Fonts read-only producer-side base/receipt contract, source-only."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zog.image_build.errors import ImageBuildError
from zog.image_build import first_fonts_producer_contract as p

REPO = Path(__file__).resolve().parents[1]

def test_selected_source_has_fixed_original_pin_and_build_order():
    assert p.source_plan(REPO)=={
        "task":"graphics-fonts-image-v1",
        "source_repository":"zog144/image-build",
        "source_revision":"1f07e83dbd80dacb9bed0d6494c697375f0e26cd",
        "monthly_pin_identity":"sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36",
        "source_plan_path":"project/bootstrap/graphics-fonts.py",
        "stage_order":["libpng-final","freetype-final","fontconfig-final"],
        "targets":["libpng-final","freetype-final","fontconfig-final"],
        "source_only":True,"native_compiler_authorized":False,
    }

@pytest.mark.parametrize("kind",["pin","stage","targets"])
def test_pin_stage_and_target_mutation_denied(tmp_path,kind):
    source=tmp_path/"source"
    (source/"project/pins/2026-10-01").mkdir(parents=True)
    (source/"project/bootstrap").mkdir(parents=True)
    raw=(REPO/p.PIN_PATH).read_bytes()
    (source/p.PIN_PATH).write_bytes(raw if kind!="pin" else raw+b"\n# substitution")
    original=p.literal(REPO/p.PLAN_PATH)
    if kind=="stage":
        original["stages"][0]["project"]="libssl"
    if kind=="targets":
        original["targets"].reverse()
    (source/p.PLAN_PATH).write_text(repr(original))
    with pytest.raises(ImageBuildError,match="pin bytes differ|recipe stage"):
        p.source_plan(source)

@pytest.mark.parametrize("bad",["e"*63,"e"*65,"e"*64+"x",None,42,"unknown"])
def test_fabricated_noncanonical_generation_denied_before_any_record_read(bad):
    with pytest.raises(ImageBuildError,match="canonical identity"):
        p.observe_base(None,repository_root=REPO,selected_generation_id=bad)

def test_no_canonical_provenance_is_not_accepted_even_with_plausible_sha():
    with pytest.raises(ImageBuildError,match="provenance"):
        p.observe_base(SimpleNamespace(provenance=None),repository_root=REPO,
                       selected_generation_id="e"*64)

def _fake_base(tmp_path, kind="image", stage=2, *, canonical_record=True):
    state=tmp_path/"state"
    generation="a"*64
    directory=state/"image-build/generations"/generation
    directory.mkdir(parents=True)
    manifest={
        "kind":kind,"stage":stage,"self_hosted":True,
        "inputs":{"kind":kind,"stage":stage},"outputs":[],
        "build_record":{"generation":generation,
             "record":"sha256:"+"b"*64} if canonical_record else {},
    }
    (directory/"manifest.json").write_text(json.dumps(manifest))
    pin={"month":p.MONTH,"repository":p.REPOSITORY,
         "revision":p.SOURCE_REVISION,"path":p.PIN_PATH,"digest":p.PIN_SHA256}
    provenance=SimpleNamespace(pin=pin,host_id="synthetic-host",
        project_id="synthetic-project",generation_contract="rootfs-v1")
    builder=SimpleNamespace(state=state,provenance=provenance)
    return builder,generation,manifest

@pytest.mark.parametrize("kind,stage",[
 ("image",2),("toolchain",1),("toolchain",0),
])
def test_wrong_kind_or_unaccepted_toolchain_stage_denied_without_provenance(monkeypatch,tmp_path,kind,stage):
    b,gen,manifest=_fake_base(tmp_path,kind,stage)
    called=[]
    monkeypatch.setattr(p,"read_selection",lambda path:
        SimpleNamespace(generation=gen,manifest=copy.deepcopy(manifest)))
    monkeypatch.setattr(p,"verify_generation",lambda *_:called.append(True))
    with pytest.raises(ImageBuildError,match="second-stage compiler"):
        p.observe_base(b,repository_root=REPO,selected_generation_id=gen)
    assert called==[]

def test_self_consistent_stage_two_without_real_build_record_closure_denied(monkeypatch,tmp_path):
    b,gen,manifest=_fake_base(tmp_path,kind="toolchain")
    monkeypatch.setattr(p,"read_selection",lambda path:
        SimpleNamespace(generation=gen,manifest=copy.deepcopy(manifest)))
    def protected_verify(*_):
        raise ImageBuildError("canonical build-record root absent")
    monkeypatch.setattr(p,"verify_generation",protected_verify)
    with pytest.raises(ImageBuildError,match="canonical build-record"):
        p.observe_base(b,repository_root=REPO,selected_generation_id=gen)

def test_forged_toolchain_manifest_root_record_denied_before_canonical_verify(monkeypatch,tmp_path):
    b,gen,manifest=_fake_base(tmp_path,kind="toolchain",canonical_record=False)
    monkeypatch.setattr(p,"read_selection",lambda path:
        SimpleNamespace(generation=gen,manifest=copy.deepcopy(manifest)))
    monkeypatch.setattr(p,"verify_generation",
                        lambda *_:pytest.fail("canonical provenance must not be read"))
    with pytest.raises(ImageBuildError,match="canonical generation root"):
        p.observe_base(b,repository_root=REPO,selected_generation_id=gen)

def test_manifest_mutation_during_observation_denied(monkeypatch,tmp_path):
    b,gen,manifest=_fake_base(tmp_path,kind="toolchain")
    monkeypatch.setattr(p,"read_selection",lambda path:
        SimpleNamespace(generation=gen,manifest=copy.deepcopy(manifest)))
    def mutate(*_):
        file=b.state/"image-build/generations"/gen/"manifest.json"
        changed=json.loads(file.read_text())
        changed["new_field"]="injected"
        file.write_text(json.dumps(changed))
        return {"records":{}}
    monkeypatch.setattr(p,"verify_generation",mutate)
    with pytest.raises(ImageBuildError,match="changed during read-only"):
        p.observe_base(b,repository_root=REPO,selected_generation_id=gen)

@pytest.mark.parametrize("wrong",[
 {"task":"graphics-xcb-core-image-v1"},
 {"task":"graphics-fonts-image-v1","source_repository":"attacker/image-build"},
 {"task":"graphics-fonts-image-v1","source_repository":"zog144/image-build",
  "source_revision":"f"*40},
])
def test_output_verification_denies_wrong_original_task_source_before_any_builder_read(wrong):
    with pytest.raises(ImageBuildError,match="protected Fonts output task|selected original|not the selected"):
        p.verify_fonts_output(None,repository_root=REPO,
                              trusted_context=wrong,observed_base={})

def test_native_wrappers_refuse_nonroot_before_evidence_or_controller(monkeypatch):
    monkeypatch.setattr(p.os,"geteuid",lambda:1000)
    with pytest.raises(PermissionError):
        p.observe_base_native(None,repository_root="/untrusted",
                              selected_generation_id="f"*64)
    with pytest.raises(PermissionError):
        p.verify_fonts_output_native(None,repository_root="/untrusted",
                        trusted_context={},observed_base={})

def test_producer_contract_does_not_authorize_dispatch_or_acceptance():
    source=(REPO/"src/zog/image_build/first_fonts_producer_contract.py").read_text()
    for forbidden in ("import boto3","import botocore","send_command(",
                      "send_message(","publish_generation(","install_native(",
                      "toolchain.submit(","pipeline.submit("):
        assert forbidden not in source
    assert 'native_compiler_authorized": False' in source
    assert 'status": "canonical-base-observed-not-native-admission"' in source

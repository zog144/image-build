"""Synthetic dual-kind compiler-base acceptance, actual immutable-byte and execution gates.

All Ed25519 keys, generation files, compiler bytes and probe results here are
disposable test data; these tests cannot produce a native acceptance receipt.
"""
import base64
import copy
import hashlib
import json
import platform
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from zog.image_build import compiler_base_acceptance as ca
from zog.image_build import compiler_base_probe as cp
from zog.image_build.engine import ImageBuild
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory
from zog.image_build.metadata import identity
from zog.image_build import engine as engine_module

ROLES={
    "compiler":"usr/bin/gcc","linker":"usr/bin/ld","assembler":"usr/bin/as",
    "libc_header":"usr/include/stdio.h","abi_header":"usr/include/features.h",
    "crt":"usr/lib/crt1.o","libc":"usr/lib/libc.so",
}
PROBE={
    "schema":ca.PROBE,"status":"passed",
    "compiler_target":"x86_64-linux-gnu",
    "source_sha256":cp.SOURCE_SHA256,
    "command_sha256":cp.COMMAND_SHA256,
    "elapsed_seconds":5,
    "controller_execution":{"runtime_id":"fixture-runtime","invocation_id":"fixture-invocation",
        "journal_reference":"fixture-journal","exit_code":0,"cleanup_complete":True},
    "isolation":{"read_only_root":True,"network_access":False,"pivot_root":True,
        "host_mounts_visible":False,"host_include_fallback":False,
        "host_library_fallback":False},
    "include_paths":["/usr/include/stdio.h"],
    "library_paths":["/usr/lib/crt1.o","/usr/lib/libc.so"],
    "linked_executable_sha256":"sha256:"+"e"*64,
}
def materialize(tmp_path,kind="image"):
    state=tmp_path/"state"
    proto=state/"image-build/generations"
    root=tmp_path/"temporary-root"
    for name in ROLES.values():
        target=root/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(("synthetic-only:"+name).encode())
    inputs={"schema":2,"kind":kind,"architecture":"x86_64"}
    if kind=="toolchain":inputs.update(stage=2)
    gid=identity(inputs)
    dest=proto/gid
    dest.mkdir(parents=True,exist_ok=True)
    import shutil
    shutil.copytree(root,dest/"root")
    outputs=inventory(dest/"root")
    record={"schema":1,"generation":gid,"record":"sha256:"+"f"*64} if kind=="toolchain" else None
    manifest={
        "schema":2,"kind":kind,"generation":gid,"inputs":inputs,
        "outputs":outputs,
    }
    if kind=="toolchain":manifest.update(stage=2,self_hosted=True,build_record=record)
    (dest/"manifest.json").write_text(json.dumps(manifest))
    return state,gid,record

def signed_fixture(tmp_path,kind="image"):
    state,gid,record=materialize(tmp_path,kind=kind)
    key=Ed25519PrivateKey.generate()
    pub=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    root=state/"image-build/generations"/gid
    manifest=json.loads((root/"manifest.json").read_text())
    files={}
    for role,path in ROLES.items():
        files[role]={"path":path,"sha256":ca.digest((root/"root"/path).read_bytes())}
    cfg={"project_root":"/isolated-native-fixture","sandbox_mode":"pivot-root"}
    claim={
        "schema":ca.SCHEMA,
        "status":"independently-accepted-for-compiler-use",
        "generation_id":gid,"generation_kind":kind,
        "generation_manifest_sha256":ca.digest((root/"manifest.json").read_bytes()),
        "generation_inventory_sha256":"sha256:"+identity(manifest["outputs"]),
        "generation_record_sha256":record["record"] if record else None,
        "host_id":"fixture-host","installation_id":"fixture-install",
        "state_volume_id":"fixture-state","project_id":"fixture-project",
        "execution_environment_sha256":ca.digest(ca.canonical(cfg)),
        "target_abi":"x86_64-linux-gnu",
        "installed_paths":files,
        "historical_provenance":(
            {"status":"complete","missing":[],"retained_evidence_sha256":None}
            if kind=="toolchain" else
            {"status":"historical-gap-declared",
             "missing":["missing original stage-two compiler build chain"],
             "retained_evidence_sha256":"sha256:"+"b"*64}),
        "native_probe":{**copy.deepcopy(PROBE),"base_generation_id":gid},
        "required_probe_command_sha256":cp.COMMAND_SHA256,
    }
    authority={
        "schema":"zog-protected-compiler-base-issuer-v1",
        "host_id":claim["host_id"],"installation_id":claim["installation_id"],
        "state_volume_id":claim["state_volume_id"],
        "project_id":claim["project_id"],
        "key_id":"synthetic-issuer","ed25519_public_key":pub,
        "receipt_directory":str(tmp_path/"independent-test-receipts"),
        "execution_environment_sha256":claim["execution_environment_sha256"],
    }
    rdir=Path(authority["receipt_directory"]);rdir.mkdir()
    runner=SimpleNamespace(execute=SimpleNamespace(configuration=lambda:cfg))
    prov=SimpleNamespace(generation_contract="rootfs-v1")
    builder=SimpleNamespace(state=state,compiler_base_authority=authority,
                            runner=runner,provenance=prov)
    selection=SimpleNamespace(generation=gid,root=root/"root",manifest=manifest)
    def sign():
        signed={
            "schema":ca.SCHEMA,"key_id":authority["key_id"],
            "claim":claim,
            "signature":base64.b64encode(
                key.sign(ca.DOMAIN+ca.canonical(claim))).decode(),
        }
        raw=ca.canonical(signed)
        (rdir/(gid+".json")).write_bytes(raw)
        return ca.digest(raw)
    return builder,selection,claim,authority,sign

def test_independently_signed_image_preserves_kind_and_historical_gap(tmp_path):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path)
    result=ca.resolve(builder,selection,sign())
    assert result["generation_kind"]=="image"
    assert result["generation_id"]==selection.generation
    assert result["historical_provenance"]["status"]=="historical-gap-declared"
    assert "missing original stage-two" in result["historical_provenance"]["missing"][0]
    assert result["status"]=="independent-compiler-capability-observed-not-job-authorization"
    assert "accepted" not in result["status"]

def test_stage_two_kind_keeps_canonical_provenance(monkeypatch,tmp_path):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path,kind="toolchain")
    seen=[]
    import zog.image_build.generation_provenance as provenance
    monkeypatch.setattr(provenance,"verify",lambda p,s:seen.append(s.generation))
    result=ca.resolve(builder,selection,sign())
    assert result["generation_kind"]=="toolchain"
    assert result["historical_provenance"]["status"]=="complete"
    assert seen==[selection.generation]

def test_signed_looking_but_untrusted_image_not_accepted(tmp_path):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path)
    trusted=sign()
    builder.compiler_base_authority["ed25519_public_key"]="f"*64
    with pytest.raises(ImageBuildError,match="signature invalid"):
        ca.resolve(builder,selection,trusted)

@pytest.mark.parametrize("mutation",[
    "historical_gap","wrong_kind","compiler_binary","host_header",
    "unsigned_ack","host_identity","ambient_host_path","probe_timeout",
    "wrong_abi","wrong_controller","replaced_environment","forged_manifest",
])
def test_resigned_but_incomplete_or_substituted_claim_fails(tmp_path,mutation):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path)
    if mutation=="historical_gap":claim["historical_provenance"]["missing"]=[]
    elif mutation=="wrong_kind":claim["generation_kind"]="toolchain"
    elif mutation=="compiler_binary":claim["installed_paths"]["compiler"]["sha256"]="sha256:"+"0"*64
    elif mutation=="host_header":claim["installed_paths"]["libc_header"]["path"]="usr/local/include/stdio.h"
    elif mutation=="unsigned_ack":claim["native_probe"]["controller_execution"]["cleanup_complete"]=False
    elif mutation=="host_identity":claim["installation_id"]="other-installation"
    elif mutation=="ambient_host_path":claim["native_probe"]["library_paths"]=["/host/usr/lib/libc.so"]
    elif mutation=="probe_timeout":claim["native_probe"]["elapsed_seconds"]=121
    elif mutation=="wrong_abi":claim["target_abi"]="aarch64-linux-gnu"
    elif mutation=="wrong_controller":claim["native_probe"]["isolation"]["pivot_root"]=False
    elif mutation=="replaced_environment":claim["execution_environment_sha256"]="sha256:"+"0"*64
    elif mutation=="forged_manifest":claim["generation_manifest_sha256"]="sha256:"+"0"*64
    with pytest.raises(ImageBuildError,match="NOT ACCEPTED"):
        ca.resolve(builder,selection,sign())

def test_actual_selected_binary_changes_are_detected(tmp_path):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path)
    original=sign()
    (selection.root/"usr/bin/gcc").write_bytes(b"replaced compiler after signed observation")
    with pytest.raises(ImageBuildError):
        ca.resolve(builder,selection,original)

def test_generation_with_missing_receipt_or_bare_hash_does_not_run(tmp_path):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path)
    with pytest.raises(ImageBuildError,match="receipt"):
        ca.resolve(builder,selection,"sha256:"+"0"*64)
    with pytest.raises(ImageBuildError,match="receipt"):
        ca.resolve(builder,selection,"f"*64)

def test_noncanonical_original_manifest_rejected(tmp_path):
    builder,selection,claim,auth,sign=signed_fixture(tmp_path)
    saved=sign()
    manifest=builder.state/"image-build/generations"/selection.generation/"manifest.json"
    contents=json.loads(manifest.read_text())
    contents["kind"]="toolchain"
    manifest.write_text(json.dumps(contents))
    with pytest.raises(ImageBuildError):
        ca.resolve(builder,selection,saved)

def test_probe_artefacts_are_observed_not_native_acceptance(tmp_path):
    root=tmp_path/"probe-output";root.mkdir()
    for name,data in {
        "target.txt":b"x86_64-linux-gnu\n",
        "includes.txt":b"#include <...> search starts here:\n /usr/include\n /usr/include/stdio.h\n",
        "links.txt":b"/usr/lib/crt1.o\n/usr/lib/libc.so\n",
        "probe":b"\x7fELF\x02\x01"+b"\0"*12+(62).to_bytes(2,"little")+b"\0"*40,
        "probe.o":b"\x7fELF\x02\x01"+b"\0"*64,
        "probe.i":b"# 1 \"/usr/include/stdio.h\"\nint main(){};\n",
        "runtime.txt":b"zog-compiler-probe\n",
    }.items():
        (root/name).write_bytes(data)
    execution={"runtime_id":"synthetic-r","invocation_id":"synthetic-i","exit_code":0,
        "cleanup_complete":True,"journal_reference":"synthetic-j"}
    report=cp.inspect_completed_probe(root,generation="a"*64,completion=execution,seconds=4)
    assert report["status"]=="observed-not-accepted"
    assert report["isolation"]["host_library_fallback"] is False
    (root/"links.txt").write_bytes(b"/host/usr/lib/libc.so\n")
    with pytest.raises(ImageBuildError,match="Host include/library"):
        cp.inspect_completed_probe(root,generation="a"*64,completion=execution,seconds=4)

def test_native_probe_requires_box_control_before_attempt_write(tmp_path):
    with pytest.raises(ImageBuildError,match="box-control"):
        cp.execute_native_probe(SimpleNamespace(runner=SimpleNamespace(execute=None)),
          SimpleNamespace(root=tmp_path,generation="a"*64),tmp_path/"attempt")
    assert not (tmp_path/"attempt").exists()

def test_actual_engine_image_requires_acceptance_and_propagates_binding(monkeypatch,tmp_path):
    # Exercise the real _ensure path without issuing a real compiler command.
    b=ImageBuild.__new__(ImageBuild)
    b.state=tmp_path
    b.package_dir=tmp_path/"packages"
    b.provenance=None
    b.dependency_replacements={}
    b.runner=SimpleNamespace()
    b.compiler_base_authority=None
    b.source_mirror=None
    base=SimpleNamespace(generation="a"*64,
        root=tmp_path/"base"/"root",
        manifest={"kind":"image","inputs":{"architecture":platform.machine()}})
    base.root.mkdir(parents=True)
    monkeypatch.setattr(engine_module,"read_selection",lambda _:base)
    with pytest.raises(ImageBuildError,match="requires independently accepted"):
        b._ensure(["fixture-final"],toolchain=base)
    from zog.image_build import compiler_base_acceptance as acceptance
    bound={"schema":ca.BINDING,"generation_id":base.generation,
           "generation_kind":"image","status":
           "independent-compiler-capability-observed-not-job-authorization"}
    calls=[]
    monkeypatch.setattr(acceptance,"resolve",
                        lambda _builder,_selection,_id:copy.deepcopy(bound))
    monkeypatch.setattr(engine_module,"load_packages",lambda _:{"fixture-final":SimpleNamespace(fingerprint="fixture")})
    monkeypatch.setattr(engine_module,"order",lambda *a,**k:["fixture-final"])
    attempt=tmp_path/"attempt"
    attempt.mkdir()
    b._candidate=lambda _:attempt
    def build(*args,**kwargs):
        calls.append(kwargs["compiler_base"])
        return {}
    b._build_set=build
    b._compose=lambda *a,**k:{}
    output=SimpleNamespace(generation="b"*64)
    def publish(root,inputs,kind,details):
        calls.append(inputs["compiler_base"])
        assert inputs["toolchain"]==base.generation
        assert kind=="image"
        return output
    b._publish=publish
    b._activate=lambda *a:None
    assert b._ensure(["fixture-final"],toolchain=base,
                      compiler_base="sha256:"+"1"*64).generation==output.generation
    assert calls==[bound,bound]

def test_native_probe_does_not_expose_direct_ssm_or_host_execute():
    source=(Path(__file__).resolve().parents[1]/
            "src/zog/image_build/compiler_base_probe.py").read_text()
    for dangerous in ("import boto3","subprocess.run(","send_command(","SendCommand(",
                      "os.system(","shell=True"):
        assert dangerous not in source
    assert cp.MAX_SECONDS==120
    assert cp.SOURCE_SHA256.startswith("sha256:")

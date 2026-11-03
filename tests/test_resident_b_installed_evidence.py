"""Synthetic installed-byte and protected-receipt tests; no native generation is accepted."""
import base64
import copy
import csv
import hashlib
import io
import json
import os
import stat
from pathlib import Path
import importlib.util
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "resident_native",ROOT/"tools/verify_resident_b_installed_evidence.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def digest(data):return hashlib.sha256(data).hexdigest()
def elf():
    result=bytearray(64)
    result[:6]=b"\x7fELF\x02\x01"
    result[18:20]=(62).to_bytes(2,"little")
    return bytes(result)
def fake_root(tmp):
    root=tmp/"rootfs"
    required=m.required_files()
    required.update({
        "usr/lib/libssl.so","usr/lib/libcrypto.so","usr/lib/libsqlite3.so",
        "usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/entry_points.txt",
        "usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/entry_points.txt",
    })
    def content(name):
        if name=="usr/bin/python3.12" or name.endswith(".so") or ".so." in name:
            return elf()
        if name in ("usr/bin/box-control","usr/bin/root-control"):
            return b"#!/usr/bin/python3.12\n# synthetic entry\n"
        if name.endswith("/METADATA"):
            label="box-control" if "box_control-" in name else "root-control"
            return ("Metadata-Version: 2.3\nName: "+label+"\nVersion: 0.1.0\n").encode()
        if name.endswith("/entry_points.txt"):
            label="box-control" if "box_control-" in name else "root-control"
            return ("[console_scripts]\n"+label+" = "+m.PROGRAMS[label]+"\n").encode()
        if name=="usr/lib/systemd/system/zog-root-control.service":
            cmd=m.literal(m.PKG/"root-control/stages/final/build.py")["install"][0][-1]
            return (cmd.split("<<'ZOG_ROOT_CONTROL_UNIT'\n",1)[1]
                    .split("\nZOG_ROOT_CONTROL_UNIT",1)[0]+"\n").encode()
        return ("synthetic-not-native-file "+name+"\n").encode()
    for name in sorted(required):
        if name.endswith("/RECORD"):continue
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(content(name))
        p.chmod(0o755 if name.startswith("usr/bin/") else 0o644)
    for label in ("box-control","root-control"):
        dist=label.replace("-","_")+"-0.1.0.dist-info"
        parent="usr/lib/python3.12/site-packages/"
        native=[
            parent+dist+"/METADATA",
            parent+dist+"/entry_points.txt",
            parent+"zog/"+label.replace("-","_")+"/__init__.py",
            "usr/bin/"+label,
        ]
        out=io.StringIO()
        writer=csv.writer(out,lineterminator="\n")
        for name in native:
            raw=(root/name).read_bytes()
            b64=base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
            rel="../../../bin/"+label if name.startswith("usr/bin/") else name[len(parent):]
            writer.writerow([rel,"sha256="+b64,str(len(raw))])
        writer.writerow([dist+"/RECORD","",""])
        path=root/parent/dist/"RECORD"
        path.write_text(out.getvalue());path.chmod(0o644)
    assert all((root/name).is_file() for name in required)
    return root

def make_claim(root):
    files={}
    for file in root.rglob("*"):
        if file.is_file():
            rel=file.relative_to(root).as_posix()
            data=file.read_bytes()
            info=file.stat()
            kind=("elf" if data.startswith(b"\x7fELF")
                  else "script" if rel.startswith("usr/bin/") else "data")
            files[rel]={"sha256":digest(data),"size":len(data),
                "mode":stat.S_IMODE(info.st_mode),"uid":info.st_uid,
                "gid":info.st_gid,"kind":kind}
    bindings={"host_id":"synthetic-host-01","installation_id":"synthetic-install-01",
        "state_volume_id":"synthetic-state-01","operation_id":"synthetic-operation-01",
        "rootfs_generation_id":"a"*64,"rootfs_manifest_sha256":"b"*64}
    preds={}
    for stage in m.STAGES:
        package,_=stage.rsplit("-",1)
        source=m.literal(m.PKG/package/"stages/final/sources.py")[0]
        preds[stage]={"source_sha256":source["sha256"],"generation_id":"c"*64,
            "manifest_sha256":"d"*64,"receipt_sha256":"e"*64}
    soabi=m.SOABI
    modulepaths={key:f"usr/lib/python3.12/lib-dynload/{key}.{soabi}.so"
                 for key in m.MODULES}
    modulepaths.update({"zog.box_control":"usr/lib/python3.12/site-packages/zog/box_control/__init__.py",
                        "zog.root_control":"usr/lib/python3.12/site-packages/zog/root_control/__init__.py"})
    critical=[key for key,item in files.items() if item["kind"]=="elf"]
    receipt={
        "schema":"zog-resident-b-installed-generation-evidence-v1",
        "purpose":"REVIEW_ONLY_NOT_GENERATION_ADMISSION",
        "source_review":m.SOURCE_REVIEW,
        "binding":bindings,
        "predecessors":preds,"files":files,
        "python_probe":{"invocation_id":bindings["operation_id"],
            "program":"/usr/bin/python3.12","version":"3.12.16",
            "soabi":soabi,"exit_code":0,
            "ssl_version":"OpenSSL 3.5.0","sqlite_version":"3.47.2",
            "module_paths":modulepaths,
            "imported":["ssl","sqlite3","_ssl","_sqlite3","_hashlib",
                        "zog.box_control","zog.root_control"]},
        "elf_probe":{"invocation_id":bindings["operation_id"],"checked":critical,
            "loader_closure":[{"needed":"libpython3.12.so.1.0",
                "resolved_path":"usr/lib/libpython3.12.so.1.0",
                "sha256":files["usr/lib/libpython3.12.so.1.0"]["sha256"]}]},
        "installation_probe":{"invocation_id":bindings["operation_id"],
            "state_is_mountpoint":True,"state_device":1,"state_root_uid":0,
            "state_root_gid":0,"state_root_mode":0o700,
            "root_service_enabled":False,"box_service_installed":False,
            "root_socket_authorized":False,
            "root_unit_path":"usr/lib/systemd/system/zog-root-control.service"},
        "witnesses":{"native_worker":{"key_id":"synthetic-worker","signature":""},
            "accepted_generation_owner":{"key_id":"synthetic-issuer","signature":""}},
    }
    worker=Ed25519PrivateKey.generate()
    issuer=Ed25519PrivateKey.generate()
    def raw_pub(key):
        return key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw).hex()
    policy={"schema":"zog-host-install-protected-resident-b-pins-v1",
        "binding":copy.deepcopy(bindings),"state_device":1,
        "native_worker_key":raw_pub(worker),"generation_owner_key":raw_pub(issuer),
        "native_worker_key_id":"synthetic-worker",
        "generation_owner_key_id":"synthetic-issuer"}
    return receipt,policy,worker,issuer

def sign(receipt,worker,issuer):
    payload={k:v for k,v in receipt.items() if k!="witnesses"}
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    for label,key,domain in (
        ("native_worker",worker,b"ZOG_RESIDENT_B_NATIVE_WORKER_V1\x00"),
        ("accepted_generation_owner",issuer,b"ZOG_RESIDENT_B_GENERATION_OWNER_V1\x00")):
        receipt["witnesses"][label]["signature"]=base64.b64encode(
            key.sign(domain+canonical)).decode()

@pytest.fixture
def scenario(tmp_path):
    root=fake_root(tmp_path)
    claim,policy,w,i=make_claim(root)
    sign(claim,w,i)
    return root,claim,policy,w,i

def test_synthetic_real_file_bytes_and_wheel_record_still_never_grant_acceptance(scenario,tmp_path):
    root,claim,policy,_,_=scenario
    assert m.receipt_shape(claim)["native_admission"] is False
    assert m.file_bytes(root,claim,synthetic=True).endswith("NOT_ACCEPTED")
    assert m.wheel_record(root,claim).endswith("NOT_ACCEPTED")
    report=m.inspect(root,tmp_path/"STATE",claim,policy,synthetic=True)
    assert report["inspection"]=="SYNTHETIC_EVIDENCE_CONSISTENT"
    assert report["generation_accepted"] is False
    assert report["service_activation_authorized"] is False

@pytest.mark.parametrize("field",["predecessors","python_probe","elf_probe",
                                   "installation_probe","files","witnesses"])
def test_missing_evidence_section_rejected(scenario,field):
    _,claim,_,_,_=scenario
    del claim[field]
    with pytest.raises(m.EvidenceRefused):m.receipt_shape(claim)

def test_fabricated_approval_or_missing_predecessor_fails_even_if_fields_look_signed(scenario):
    _,claim,_,_,_=scenario
    claim["native_success"]=True
    with pytest.raises(m.EvidenceRefused):m.receipt_shape(claim)
    del claim["native_success"]
    del claim["predecessors"]["resident312-dbus-next-final"]
    with pytest.raises(m.EvidenceRefused):m.receipt_shape(claim)

@pytest.mark.parametrize("mutation",[
    "wrong_source","missing_ssl","wrong_soabi","missing_record",
    "bad_unit","state_not_mount","unapproved_service","no_loader","host_elf"])
def test_critical_evidence_missing_or_source_substituted(scenario,mutation):
    _,c,_,_,_=scenario
    if mutation=="wrong_source":c["predecessors"]["root-control-final"]["source_sha256"]="f"*64
    if mutation=="missing_ssl":del c["python_probe"]["module_paths"]["_ssl"]
    if mutation=="wrong_soabi":c["python_probe"]["soabi"]="cpython-315-x86_64-linux-gnu"
    if mutation=="missing_record":del c["files"]["usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/RECORD"]
    if mutation=="bad_unit":c["installation_probe"]["root_unit_path"]="usr/lib/systemd/system/evil.service"
    if mutation=="state_not_mount":c["installation_probe"]["state_is_mountpoint"]=False
    if mutation=="unapproved_service":c["installation_probe"]["root_service_enabled"]=True
    if mutation=="no_loader":c["elf_probe"]["loader_closure"]=[]
    if mutation=="host_elf":c["elf_probe"]["loader_closure"][0]["resolved_path"]="usr/local/lib/libpython3.12.so.1.0"
    with pytest.raises(m.EvidenceRefused):m.receipt_shape(c)

def test_changed_actual_bytes_rejected_even_when_signed_manifest_unchanged(scenario):
    root,c,_,_,_=scenario
    p=root/"usr/lib/python3.12/site-packages/zog/root_control/__init__.py"
    p.write_bytes(b"synthetic adversarial content\n")
    with pytest.raises(m.EvidenceRefused,match="differs"):
        m.file_bytes(root,c,synthetic=True)

def test_installed_wheel_RECORD_tamper_and_console_entry_point_rejected(scenario):
    root,c,_,_,_=scenario
    p=root/"usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/RECORD"
    p.write_text("zog/box_control/__init__.py,sha256=AAAA,1\n")
    with pytest.raises(m.EvidenceRefused):
        m.wheel_record(root,c)
    ep=root/"usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/entry_points.txt"
    ep.write_text("[console_scripts]\nroot-control = run.unsafe:main\n")
    with pytest.raises(m.EvidenceRefused):
        m.wheel_record(root,c)

def test_untrusted_key_or_mutation_after_signature_rejected(scenario):
    root,c,policy,_,_=scenario
    altered=copy.deepcopy(c)
    altered["python_probe"]["ssl_version"]="OpenSSL 0.0.0"
    with pytest.raises(m.EvidenceRefused,match="signature"):
        m.verify_external_signatures(altered,policy)
    bad=copy.deepcopy(policy)
    bad["generation_owner_key"]="00"*32
    with pytest.raises(m.EvidenceRefused,match="signature"):
        m.verify_external_signatures(c,bad)

def test_runtime_native_mode_requires_actual_protected_mount_and_root_owner(scenario,tmp_path):
    root,c,policy,_,_=scenario
    with pytest.raises(m.EvidenceRefused,match="owner/mode"):
        m.inspect(root,tmp_path/"state",c,policy)

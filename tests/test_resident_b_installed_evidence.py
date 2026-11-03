"""Synthetic *unaccepted* Resident B installed-generation witness regression."""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest
from tools import verify_resident_b_installed_evidence as v

GEN="a"*64
STATE="resident-b-state-identity-00001"

def sha(x): return hashlib.sha256(x).hexdigest()
def record_line(path,data):
    h=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return (path,"sha256="+h,str(len(data)))

def fixture(tmp_path):
    root=tmp_path/"image";root.mkdir(parents=True)
    src=json.loads(v.SOURCE_EXPECTED.read_text())
    paths=set(sum(src["expected_installed_outputs"].values(),[]))
    source={}
    for name in paths:
        if name.endswith(".service"):
            data=b"[Unit]\nRequiresMountsFor=/state\n[Service]\nType=exec\nUser=root\nGroup=root\nExecStart=/usr/bin/root-control\n"
        elif name in ("usr/bin/box-control","usr/bin/root-control"):
            data=b"#!/usr/bin/python3.12\nimport sys\n"
        elif name.endswith("/RECORD"):
            continue
        elif name.endswith("/METADATA"):
            app="box-control" if "box_control" in name else "root-control"
            data=("Metadata-Version: 2.4\nName: "+app+"\nVersion: 0.1.0\n").encode()
        else: data=("synthetic:"+name).encode()
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if name.startswith("usr/bin/") else 0o644)
        source[name]=data
    wheels={}
    prefix="usr/lib/python3.12/site-packages/"
    for app in ("box_control-0.1.0","root_control-0.1.0"):
        dist=app+".dist-info"
        members=[x for x in source if x.startswith(prefix+"zog/"+app.split("_")[0]+"_control/") or
                 x.startswith(prefix+dist+"/")]
        # Need exact names matching RECORD, plus RECORD itself.
        members=[x[len(prefix):] for x in members]
        record=dist+"/RECORD"
        lines=[record_line(p,source[prefix+p]) for p in members]
        lines.append((record,"",""))
        buf=io.StringIO();csv.writer(buf,lineterminator="\n").writerows(lines)
        raw=buf.getvalue().encode()
        path=prefix+record
        (root/path).write_bytes(raw)
        source[path]=raw
        wheels[app]={"record_sha256":sha(raw),"record_members":sorted(members+[record])}
    modules={}
    elf=bytearray(64);elf[:4]=b"\x7fELF";elf[4]=2;elf[5]=1
    struct.pack_into("<H",elf,16,3);struct.pack_into("<H",elf,18,62)
    for name in v.MODULES:
        path="usr/lib/python3.12/lib-dynload/"+name+".cpython-312-x86_64-linux-gnu.so"
        dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(elf)
        modules[name]=path
    files=[]
    for name in sorted(paths):
        target=root/name;raw=target.read_bytes()
        kind="script" if name.startswith("usr/bin/") else "text"
        files.append(dict(path=name,sha256=sha(raw),size=len(raw),
                          mode=stat.S_IMODE(target.stat().st_mode),kind=kind))
    claim=dict(generation_id=GEN,state_volume_id=STATE,source_pins=v.SOURCE_PINS,
        files=files,modules=modules,python_version="3.12",
        wheels=wheels,
        native_observation={"rootfs_slot":"HOST-B","rootfs_readonly":True,
            "state_mount_id":STATE,"source_generation_receipt_sha256":"f"*64,
            "observed_by":"synthetic independent test witness",
            "observation_id":"synthetic-1"},
        state_permissions={"state_mode":0o700,"private_uid":0,"state_authenticated":True},
        service_permissions={"unit_mode":0o644,"socket_mode":0o660,"socket_uid":0,
            "socket_gid_provisioned":True,"service_enabled":False},
        status="observed",accepted=False)
    key=Ed25519PrivateKey.generate()
    def sign(value):
        return {"schema":v.SCHEMA,"claim":value,
                "signature":base64.b64encode(key.sign(
                    b"zog-resident-b-installed-evidence-v1\0"+v.canonical(value))).decode()}
    upstream_key=Ed25519PrivateKey.generate()
    selected={"generation_id":GEN,"source_generation_receipt_sha256":"f"*64,
              "selection_status":"accepted-as-input","native_boot_authorized":False,
              "root_control_activation_authorized":False}
    selection={"schema":"zog-resident-b-selected-input-generation-v1",
               "selection":selected,
               "signature":base64.b64encode(upstream_key.sign(
                    b"zog-resident-b-selected-input-generation-v1\0"+v.canonical(selected))).decode()}
    return root,claim,key,sign,selection,upstream_key

def run(root,claim,key,sign,selection,upstream_key,*,generation=GEN,state=STATE):
    return v.verify(root,sign(claim),key.public_key(),
        expected_generation=generation,expected_state=state,
        selected_generation_receipt=selection,
        trusted_generation_public_key=upstream_key.public_key())

def test_synthetic_complete_receipt_is_never_native_acceptance(tmp_path):
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path)
    result=run(root,claim,key,sign,selection,upstream_key)
    assert result["status"]=="EVIDENCE_COHERENT_UNACCEPTED"
    assert result["accepted_generation"] is None
    assert result["native_install_authorized"] is False

@pytest.mark.parametrize("change",[
    lambda c:c.update(status="accepted"),
    lambda c:c.update(accepted=True),
    lambda c:c.update(python_version="3.15"),
    lambda c:c.update(state_volume_id="moved-state"),
    lambda c:c["native_observation"].update(rootfs_readonly=False),
    lambda c:c["native_observation"].update(rootfs_slot="HOST-C"),
    lambda c:c["state_permissions"].update(state_authenticated=False),
    lambda c:c["service_permissions"].update(service_enabled=True),
    lambda c:c["service_permissions"].update(socket_gid_provisioned=False),
    lambda c:c["modules"].pop("_ssl"),
    lambda c:c["files"].pop(),
    lambda c:c["files"][0].update(sha256="0"*64),
    lambda c:c["wheels"]["box_control-0.1.0"].update(record_sha256="0"*64),
    lambda c:c.update(source_pins={**c["source_pins"],"root-control":"0"*40}),
])
def test_fabricated_success_or_incomplete_receipt_denied(tmp_path,change):
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path)
    change(claim)
    with pytest.raises(v.EvidenceDenied):
        run(root,claim,key,sign,selection,upstream_key)

def test_wrong_signature_source_or_generation_denied(tmp_path):
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path)
    forged=sign(claim)
    forged["signature"]=base64.b64encode(b"x"*64).decode()
    with pytest.raises(v.EvidenceDenied):
        v.verify(root,forged,key.public_key(),expected_generation=GEN,expected_state=STATE,
            selected_generation_receipt=selection,
            trusted_generation_public_key=upstream_key.public_key())
    with pytest.raises(v.EvidenceDenied):
        run(root,claim,key,sign,selection,upstream_key,generation="b"*64)
    with pytest.raises(v.EvidenceDenied):
        run(root,claim,key,sign,selection,upstream_key,state="other-state-identity")

def test_bytes_permissions_elf_and_wheel_record_are_independently_inspected(tmp_path):
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path)
    exe=root/"usr/bin/root-control"
    exe.write_bytes(b"#!/usr/bin/python3.15\n")
    with pytest.raises(v.EvidenceDenied):run(root,claim,key,sign,selection,upstream_key)
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path/"second")
    path=root/claim["modules"]["_ssl"];path.write_bytes(b"fake-elf")
    with pytest.raises(v.EvidenceDenied):run(root,claim,key,sign,selection,upstream_key)
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path/"third")
    path=root/"usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/RECORD"
    path.write_text("forged,sha256=bad,1\n")
    with pytest.raises(v.EvidenceDenied):run(root,claim,key,sign,selection,upstream_key)
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path/"fourth")
    (root/"usr/bin/box-control").chmod(0o777)
    with pytest.raises(v.EvidenceDenied):run(root,claim,key,sign,selection,upstream_key)

def test_symlink_or_missing_executable_denied(tmp_path):
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path)
    p=root/"usr/bin/box-control";p.unlink();p.symlink_to("/bin/true")
    with pytest.raises(v.EvidenceDenied):run(root,claim,key,sign,selection,upstream_key)

def test_independent_generation_selection_must_be_signed_and_distinct(tmp_path):
    root,claim,key,sign,selection,upstream_key=fixture(tmp_path)
    fake={**selection,"signature":base64.b64encode(b"0"*64).decode()}
    with pytest.raises(v.EvidenceDenied):
        run(root,claim,key,sign,fake,upstream_key)
    with pytest.raises(v.EvidenceDenied):
        run(root,claim,key,sign,selection,key)
    changed={**selection,"selection":{**selection["selection"],
                                  "native_boot_authorized":True}}
    with pytest.raises(v.EvidenceDenied):
        run(root,claim,key,sign,changed,upstream_key)

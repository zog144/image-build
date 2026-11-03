#!/usr/bin/env python3
"""Read-only Resident B installed-root evidence verifier (NOT an acceptor).

Signed receipts are only claims by an independently selected witness. This
module additionally inspects exact installed bytes in a supplied disposable
root and never mounts, executes controllers, enables services or selects a
generation. No caller-provided success flag can turn this into acceptance.
"""
from __future__ import annotations
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct

from cryptography.exceptions import InvalidSignature

SCHEMA="zog-resident-b-installed-generation-evidence-v1"
REQUIRED_CONTROLLERS=("box-control","root-control")
MODULES=("_ssl","_sqlite3","_hashlib")
SHA=re.compile(r"[a-f0-9]{64}\Z")
HEX128=re.compile(r"[0-9a-f]{128}\Z")
SOURCE_PINS={"box-control":"b513a9bde79135c7569adc7cadb4d45a163c7841",
             "root-control":"0c217182d25f05b9cc0f7528ee614bb5669370d3"}
SOURCE_EXPECTED=Path(__file__).resolve().parents[1]/"project/host/resident-b-pr14-pr15-combined-source-review.json"

class EvidenceDenied(ValueError): pass

def deny(msg): raise EvidenceDenied(msg)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()

def _keys(obj, expected, name):
    if type(obj) is not dict or set(obj)!=set(expected): deny("bad "+name)

def _digest(data):
    return hashlib.sha256(data).hexdigest()

def _path(value):
    if type(value) is not str or not value or value.startswith("/") or "\\" in value:
        deny("absolute/unsafe path")
    p=PurePosixPath(value)
    if any(x in (".","..") for x in value.split("/")) or str(p)!=value:
        deny("noncanonical path")
    return value

def _file(root, rel, *, max_size=16*1024*1024):
    rel=_path(rel)
    cur=root
    for piece in rel.split("/"):
        cur=cur/piece
        if cur.is_symlink(): deny("symlink in evidence path: "+rel)
    try: info=cur.lstat()
    except FileNotFoundError: deny("missing installed path: "+rel)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>max_size:
        deny("unsafe installed inode: "+rel)
    return cur, info

def _attestation(receipt, public_key, *, expected_generation, expected_state):
    _keys(receipt,("schema","claim","signature"),"attestation")
    if receipt["schema"]!=SCHEMA: deny("wrong evidence schema")
    claim=receipt["claim"]
    _keys(claim,("generation_id","state_volume_id","source_pins","files",
                 "modules","python_version","state_permissions","service_permissions",
                 "wheels","native_observation","status","accepted"),"claim")
    if claim["status"]!="observed" or claim["accepted"] is not False:
        deny("fabricated native acceptance")
    if (claim["generation_id"]!=expected_generation or
        claim["state_volume_id"]!=expected_state or
        claim["source_pins"]!=SOURCE_PINS):
        deny("unselected generation, STATE or source")
    if type(expected_generation) is not str or not SHA.fullmatch(expected_generation):
        deny("untrusted generation argument")
    if type(expected_state) is not str or len(expected_state)<16:
        deny("missing expected STATE")
    if claim["python_version"]!="3.12":
        deny("wrong python ABI")
    if (type(claim["native_observation"]) is not dict or
        set(claim["native_observation"])!={"rootfs_slot","rootfs_readonly","state_mount_id",
            "source_generation_receipt_sha256","observed_by","observation_id"}):
        deny("incomplete native observation")
    n=claim["native_observation"]
    if (n["rootfs_slot"] not in ("HOST-A","HOST-B") or
        n["rootfs_readonly"] is not True or
        n["state_mount_id"]!=expected_state or
        type(n["observed_by"]) is not str or not n["observed_by"] or
        type(n["observation_id"]) is not str or not n["observation_id"] or
        not SHA.fullmatch(n["source_generation_receipt_sha256"])):
        deny("untrusted native observation fields")
    try:
        raw=base64.b64decode(receipt["signature"],validate=True)
        if len(raw)!=64 or base64.b64encode(raw).decode()!=receipt["signature"]:
            deny("invalid detached witness signature")
        public_key.verify(raw,b"zog-resident-b-installed-evidence-v1\0"+canonical(claim))
    except (InvalidSignature,ValueError,TypeError,AttributeError) as exc:
        raise EvidenceDenied("unverified independent witness signature") from exc
    return claim

def _verified_generation_selection(selection, key, witness_key, generation, source_receipt):
    """Separate signed upstream generation admission is a PRECONDITION, not a result."""
    _keys(selection,("schema","selection","signature"),"selected generation")
    if selection["schema"]!="zog-resident-b-selected-input-generation-v1":
        deny("invalid independent generation source")
    fields=("generation_id","source_generation_receipt_sha256","selection_status",
            "native_boot_authorized","root_control_activation_authorized")
    proof=selection["selection"]
    _keys(proof,fields,"upstream selection")
    if (proof["generation_id"]!=generation or
        proof["source_generation_receipt_sha256"]!=source_receipt or
        proof["selection_status"]!="accepted-as-input" or
        proof["native_boot_authorized"] is not False or
        proof["root_control_activation_authorized"] is not False):
        deny("missing independently accepted source generation")
    # Reusing the same signing authority for both evidence and source selection
    # silently destroys the cross-owner acceptance boundary.
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    if key.public_bytes(Encoding.Raw,PublicFormat.Raw)==witness_key.public_bytes(Encoding.Raw,PublicFormat.Raw):
        deny("generation authority is not independent of native witness")
    try:
        signature=base64.b64decode(selection["signature"],validate=True)
        if len(signature)!=64 or base64.b64encode(signature).decode()!=selection["signature"]:
            deny("invalid independent selection signature")
        key.verify(signature,b"zog-resident-b-selected-input-generation-v1\0"+canonical(proof))
    except (ValueError,InvalidSignature,TypeError,AttributeError) as exc:
        raise EvidenceDenied("unverified selected generation signature") from exc

def _elf(raw):
    if len(raw)<64 or raw[:4]!=b"\x7fELF" or raw[4]!=2 or raw[5]!=1:
        deny("not 64-bit little-endian ELF")
    if struct.unpack_from("<H",raw,18)[0]!=62:
        deny("wrong ELF machine (x86_64 expected)")
    if struct.unpack_from("<H",raw,16)[0] not in (2,3):
        deny("unsupported ELF type")

def _wheel_record(root, dist, expected):
    prefix="usr/lib/python3.12/site-packages/"
    record=prefix+dist+".dist-info/RECORD"
    file,_=_file(root,record)
    raw=file.read_bytes()
    if _digest(raw)!=expected["record_sha256"]:
        deny("wheel RECORD digest mismatch")
    seen=set()
    for path,hashpart,sizepart in csv.reader(io.StringIO(raw.decode("utf-8"))):
        path=_path(path)
        if path in seen: deny("duplicate wheel RECORD member")
        seen.add(path)
        if not path.startswith(("zog/",dist+".dist-info/","../../../bin/")):
            deny("unexpected RECORD member path")
        if not hashpart:
            if path!=dist+".dist-info/RECORD": deny("unchecked wheel member")
            continue
        if not hashpart.startswith("sha256=") or not sizepart.isdecimal():
            deny("incomplete RECORD member")
        member=(prefix+path) if not path.startswith("../../../bin/") else ("usr/bin/"+path.split("/")[-1])
        installed,_=_file(root,member)
        data=installed.read_bytes()
        encoded=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        if encoded!=hashpart[7:] or len(data)!=int(sizepart):
            deny("installed wheel RECORD byte mismatch")
    for mandatory in (dist+".dist-info/METADATA",dist+".dist-info/RECORD"):
        if mandatory not in seen: deny("wheel metadata absent from RECORD")
    if seen!=set(expected["record_members"]):
        deny("wheel RECORD inventory differs from independently selected receipt")

def verify(root, receipt, trusted_public_key, *, expected_generation, expected_state,
           selected_generation_receipt, trusted_generation_public_key):
    root=Path(root)
    if root.is_symlink() or not root.is_dir(): deny("invalid rootfs evidence directory")
    claim=_attestation(receipt,trusted_public_key,
                       expected_generation=expected_generation,expected_state=expected_state)
    _verified_generation_selection(selected_generation_receipt,
        trusted_generation_public_key, trusted_public_key, expected_generation,
        claim["native_observation"]["source_generation_receipt_sha256"])
    source=json.loads(SOURCE_EXPECTED.read_text())
    expected=set(sum(source["expected_installed_outputs"].values(),[]))
    records=claim["files"]
    if type(records) is not list or len(records)!=len(expected) or len(records)!=len(set(expected)):
        deny("incomplete installed inventory")
    observed=set()
    for rec in records:
        _keys(rec,("path","sha256","size","mode","kind"),"installed file")
        name=_path(rec["path"])
        if name not in expected or name in observed: deny("unexpected/duplicate installed output")
        observed.add(name)
        path,info=_file(root,name)
        data=path.read_bytes()
        if (type(rec["size"]) is not int or rec["size"]!=len(data)
            or type(rec["mode"]) is not int or rec["mode"]!=stat.S_IMODE(info.st_mode)
            or type(rec["sha256"]) is not str or not SHA.fullmatch(rec["sha256"])
            or rec["sha256"]!=_digest(data)):
            deny("installed file evidence mismatch")
        if rec["kind"] not in ("text","python","script","elf"):
            deny("bad installed file classification")
        if name in ("usr/bin/root-control","usr/bin/box-control"):
            if rec["kind"]!="script" or not data.startswith(b"#!/usr/bin/python3.12"):
                deny("unreviewed controller console script")
            if rec["mode"]!=0o755: deny("controller executable permissions")
        if name.endswith("zog-root-control.service"):
            if rec["mode"]!=0o644 or b"User=root" not in data or b"Group=root" not in data:
                deny("root service privilege mismatch")
            if b"[Install]" in data or b"RequiresMountsFor=/state" not in data:
                deny("service activation or missing STATE mount gate")
    if observed!=expected: deny("missing selected native outputs")
    modules=claim["modules"]
    if type(modules) is not dict or set(modules)!=set(MODULES):
        deny("missing Python runtime SSL SQLite hashlib")
    for name,path in modules.items():
        if type(path) is not str or not path.startswith(
                "usr/lib/python3.12/lib-dynload/"+name+"."):
            deny("wrong Python native module path")
        file,_=_file(root,path)
        _elf(file.read_bytes())
    wheels=claim["wheels"]
    if type(wheels) is not dict or set(wheels)!={"box_control-0.1.0","root_control-0.1.0"}:
        deny("missing exact controller wheels")
    for dist,value in wheels.items():
        _keys(value,("record_sha256","record_members"),"wheel attestation")
        if type(value["record_members"]) is not list or len(value["record_members"])!=len(set(value["record_members"])):
            deny("bad wheel inventory")
        _wheel_record(root,dist,value)
    if claim["state_permissions"]!={"state_mode":0o700,"private_uid":0,"state_authenticated":True}:
        deny("STATE provenance/permission witness missing")
    if claim["service_permissions"]!={"unit_mode":0o644,"socket_mode":0o660,"socket_uid":0,
                                     "socket_gid_provisioned":True,"service_enabled":False}:
        deny("root-control authority/socket claim incomplete")
    # SOURCE/RECEIPT consistency only. No native authority or acceptance.
    return {"status":"EVIDENCE_COHERENT_UNACCEPTED","accepted_generation":None,
            "native_install_authorized":False,"service_activation_authorized":False}

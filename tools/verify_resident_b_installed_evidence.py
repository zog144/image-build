#!/usr/bin/env python3
"""Read-only Resident B installed-root evidence verifier (NOT an acceptor).

Signed receipts are only claims by an independently selected witness. This
module additionally inspects exact installed bytes in a supplied disposable
root and never mounts, executes controllers, enables services or selects a
generation. No caller-provided success flag can turn this into acceptance.
"""
from __future__ import annotations
import ast
import base64
import configparser
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
from email.parser import BytesParser

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
    if claim["python_version"]!="3.12.16":
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
    """Verify actual wheel member bytes, metadata, entry points and tag."""
    prefix="usr/lib/python3.12/site-packages/"
    label=dist.split("-0.1.0",1)[0].replace("_","-")
    if label not in REQUIRED_CONTROLLERS:deny("unexpected wheel distribution")
    info_path=prefix+dist+".dist-info/"
    record=info_path+"RECORD"
    raw=_file(root,record)[0].read_bytes()
    if _digest(raw)!=expected["record_sha256"]:
        deny("wheel RECORD digest mismatch")
    metadata=BytesParser().parsebytes(_file(root,info_path+"METADATA")[0].read_bytes())
    if (metadata.get("Name","").replace("_","-").lower()!=label or
        metadata.get("Version")!="0.1.0"):
        deny("installed wheel Name/Version differs from selected source")
    selected={"image-build==0.2.0.dev5","dbus-next==0.2.3"}
    if label=="root-control":selected.add("box-control==0.1.0")
    deps={x.lower().replace(" ","") for x in (metadata.get_all("Requires-Dist") or [])}
    if deps!=selected or len(metadata.get_all("Requires-Dist") or [])!=len(selected):
        deny("installed wheel Requires-Dist does not match selected runtime graph")
    cfg=configparser.ConfigParser(interpolation=None)
    cfg.read_string(_file(root,info_path+"entry_points.txt")[0].read_text())
    if (set(cfg.sections())!={"console_scripts"} or
        dict(cfg.items("console_scripts"))!={label:
            "zog."+label.replace("-","_")+
            (".cli:main" if label=="box-control" else ".daemon:main")}):
        deny("wheel console script entry-point origin mismatched")
    wheel=BytesParser().parsebytes(_file(root,info_path+"WHEEL")[0].read_bytes())
    if (wheel.get("Root-Is-Purelib","").lower()!="true" or
        wheel.get_all("Tag")!=["py3-none-any"]):
        deny("wheel CPython ABI/tag unexpectedly changed")
    seen=set()
    for row in csv.reader(io.StringIO(raw.decode("utf-8"))):
        if len(row)!=3:deny("invalid wheel RECORD row")
        member,hashpart,sizepart=row
        if member in seen:deny("duplicate wheel RECORD member")
        seen.add(member)
        script="../../../bin/"+label
        if member==script:
            installed_path="usr/bin/"+label
        else:
            _path(member)
            if not member.startswith(("zog/",dist+".dist-info/")):
                deny("unexpected wheel RECORD path")
            installed_path=prefix+member
        installed,_=_file(root,installed_path)
        data=installed.read_bytes()
        if member==dist+".dist-info/RECORD":
            if hashpart or sizepart:deny("self-hashed wheel RECORD not supported")
        else:
            if not hashpart.startswith("sha256=") or not sizepart.isdecimal():
                deny("unhashed wheel member")
            actual=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            if actual!=hashpart[7:] or len(data)!=int(sizepart):
                deny("installed wheel RECORD byte mismatch")
    mandatory={dist+".dist-info/"+x for x in ("METADATA","RECORD","WHEEL","entry_points.txt")}
    mandatory|={"zog/"+label.replace("-","_")+"/__init__.py","../../../bin/"+label}
    if not mandatory.issubset(seen) or seen!=set(expected["record_members"]):
        deny("wheel RECORD omitted required metadata/executable or substituted inventory")

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
    python=ast.literal_eval((SOURCE_EXPECTED.parents[2]/
        "project/package/python-resident312/stages/final/produce-manifest.py").read_text())
    if python.get("trees")!=["usr"] or len(python.get("required",[]))!=5:
        deny("Python 3.12 source-native output manifest changed")
    expected.update(python["required"])
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
        if name in python["required"]:
            if rec["kind"]!="elf":
                deny("Python 3.12 installed interpreter/extension is not an ELF")
            _elf(data)
        if name in ("usr/bin/root-control","usr/bin/box-control"):
            if rec["kind"]!="script" or not data.startswith(b"#!/usr/bin/python3.12"):
                deny("unreviewed controller console script")
            if rec["mode"]!=0o755: deny("controller executable permissions")
        if name.endswith("zog-root-control.service"):
            if rec["mode"]!=0o644:
                deny("root service privilege mismatch")
            selected=ast.literal_eval((SOURCE_EXPECTED.parents[2]/
                "project/package/root-control/stages/final/build.py").read_text())["install"][0][-1]
            marker="<<'ZOG_ROOT_CONTROL_UNIT'\n"
            if selected.count(marker)!=1:
                deny("missing exact reviewed root service source")
            expected_unit=selected.split(marker,1)[1].split("\nZOG_ROOT_CONTROL_UNIT",1)[0]+"\n"
            if data!=expected_unit.encode():
                deny("privileged root service differs from exact reviewed disabled unit")
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

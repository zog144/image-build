#!/usr/bin/env python3
"""Resident B installed-byte and protected-evidence checker.

No authority installation, generation selection, signed-grant issuance,
compiler execution or service activation. Caller must independently
authenticate the protected host-install policy; a supplied policy is NOT
proof it came from host-install.
"""
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

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"project/host/resident-b-pr14-pr15-combined-source-review.json"
PKG=ROOT/"project/package"
STAGES=("python-resident312-final","resident312-flit-core-final",
        "resident312-installer-final","resident312-packaging-final",
        "resident312-wheel-final","resident312-setuptools-final",
        "resident312-dbus-next-final","resident312-image-build-final",
        "box-control-final","root-control-final","openssl-final",
        "sqlite-final","systemd-final")
HEX64=re.compile(r"[0-9a-f]{64}\Z")
SOURCE_REVIEW="02fdd2f6b374322dd902ec58b982bbbf64d4b013"
SOABI="cpython-312-x86_64-linux-gnu"
MODULES=("_ssl","_sqlite3","_hashlib")
PROGRAMS={"box-control":"zog.box_control.cli:main",
          "root-control":"zog.root_control.daemon:main"}
SITE=PurePosixPath("usr/lib/python3.12/site-packages")

class EvidenceRefused(ValueError):pass
def reject(message):raise EvidenceRefused("Resident B installed evidence NO-GO: "+message)
def exact(obj,keys,where):
    if type(obj) is not dict or set(obj)!=set(keys):reject("unexpected/missing fields: "+where)
def sha(value):
    if type(value) is not str or HEX64.fullmatch(value) is None:reject("missing authentic SHA-256")
    return value
def path(value):
    if type(value) is not str or not value.startswith("usr/") or len(value)>512:
        reject("unselected installed path")
    p=PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "." in p.parts or p.as_posix()!=value:
        reject("unsafe installed path")
    return p
def literal(p):return ast.literal_eval(p.read_text())
def required_files():
    src=json.loads(SOURCE.read_text())
    if src["status"]!="SOURCE_ONLY_NATIVE_NOT_READY" or src["accepted_generation"] is not None:
        reject("source proposal was promoted")
    files=set()
    for name in PROGRAMS:
        files.update(src["expected_installed_outputs"][name])
    files.update(literal(PKG/"python-resident312/stages/final/produce-manifest.py")["required"])
    return files

def receipt_shape(receipt):
    exact(receipt,("schema","purpose","source_review","binding","predecessors","files",
                   "python_probe","elf_probe","installation_probe","witnesses"),"receipt")
    if (receipt["schema"]!="zog-resident-b-installed-generation-evidence-v1" or
        receipt["purpose"]!="REVIEW_ONLY_NOT_GENERATION_ADMISSION" or
        receipt["source_review"]!=SOURCE_REVIEW):
        reject("stale source or fabricated admission purpose")
    bind=receipt["binding"]
    exact(bind,("host_id","installation_id","state_volume_id",
                "rootfs_generation_id","rootfs_manifest_sha256","operation_id"),"binding")
    for k in ("rootfs_generation_id","rootfs_manifest_sha256"):
        sha(bind[k])
    for k in ("host_id","installation_id","state_volume_id","operation_id"):
        if (type(bind[k]) is not str or
            not re.fullmatch(r"[A-Za-z0-9_.:-]{6,160}",bind[k])):
            reject("missing protected Host/install/STATE/operation binding")
    preds=receipt["predecessors"]
    if type(preds) is not dict or set(preds)!=set(STAGES):
        reject("required authentic generation predecessor absent/extra")
    for name,entry in preds.items():
        exact(entry,("source_sha256","generation_id","manifest_sha256","receipt_sha256"),name)
        for value in entry.values():sha(value)
        package,stage=name.rsplit("-",1)
        if stage!="final":
            reject("unreviewed predecessor stage")
        original=literal(PKG/package/"stages/final/sources.py")
        if (type(original) is not list or len(original)!=1 or
            original[0]["sha256"]!=entry["source_sha256"]):
            reject("stale/unpinned predecessor original source SHA: "+name)
    manifest=receipt["files"]
    if type(manifest) is not dict or not required_files().issubset(set(manifest)):
        reject("missing required installed output or module")
    if len(manifest)!=len(set(manifest)):reject("duplicated file")
    for f,info in manifest.items():
        path(f)
        exact(info,("sha256","size","mode","uid","gid","kind"),"file")
        sha(info["sha256"])
        if (type(info["size"]) is not int or info["size"]<1 or
            type(info["mode"]) is not int or not 0<=info["mode"]<=0o777 or
            type(info["uid"]) is not int or info["uid"]<0 or
            type(info["gid"]) is not int or info["gid"]<0 or
            info["kind"] not in ("elf","script","data")):
            reject("impossible installed file identity")
    for p in required_files():
        if p not in manifest:reject("declared output omitted")
    py=receipt["python_probe"]
    exact(py,("invocation_id","program","version","soabi","exit_code","ssl_version",
              "sqlite_version","module_paths","imported"),"python-probe")
    if (py["invocation_id"]!=bind["operation_id"] or
        py["program"]!="/usr/bin/python3.12" or py["version"]!="3.12.16" or
        py["soabi"]!=SOABI or py["exit_code"]!=0 or
        not isinstance(py["ssl_version"],str) or not py["ssl_version"].startswith("OpenSSL ") or
        not isinstance(py["sqlite_version"],str) or not re.fullmatch(r"\d+\.\d+\.\d+",py["sqlite_version"]) or
        py["imported"]!=["ssl","sqlite3","_ssl","_sqlite3","_hashlib","zog.box_control","zog.root_control"]):
        reject("incomplete native Python SSL/SQLite/import probe")
    if (type(py["module_paths"]) is not dict or
        set(py["module_paths"])!={"_ssl","_sqlite3","_hashlib","zog.box_control","zog.root_control"}):
        reject("module path/ABI identity missing")
    for name,location in py["module_paths"].items():
        if name.startswith("_"):
            expected=f"usr/lib/python3.12/lib-dynload/{name}.{SOABI}.so"
        else:
            expected="usr/lib/python3.12/site-packages/"+name.replace(".","/")+"/__init__.py"
        if location!=expected or location not in manifest:
            reject("Python native module ABI path invalid")
    elf=receipt["elf_probe"]
    exact(elf,("invocation_id","checked","loader_closure"),"elf-probe")
    critical={x for x in required_files() if x.endswith(".so") or ".so." in x}
    critical.add("usr/bin/python3.12")
    if (elf["invocation_id"]!=bind["operation_id"] or
        type(elf["checked"]) is not list or len(elf["checked"])!=len(set(elf["checked"])) or
        not critical.issubset(set(elf["checked"]))):
        reject("incomplete ELF/header runtime closure")
    for p in elf["checked"]:
        if p not in manifest or manifest[p]["kind"]!="elf":
            reject("ELF receipt references missing/unverified file")
    if type(elf["loader_closure"]) is not list or not elf["loader_closure"]:
        reject("missing native link/loader observations")
    for item in elf["loader_closure"]:
        exact(item,("needed","resolved_path","sha256"),"ELF needed entry")
        if not isinstance(item["needed"],str) or "/" in item["needed"]:
            reject("invalid DT_NEEDED identity")
        file=item["resolved_path"];path(file)
        if file not in manifest or sha(item["sha256"])!=manifest[file]["sha256"]:
            reject("Host-library or forged loader identity")
    service=receipt["installation_probe"]
    exact(service,("invocation_id","state_is_mountpoint","state_device",
                   "state_root_uid","state_root_gid","state_root_mode",
                   "root_service_enabled","box_service_installed",
                   "root_socket_authorized","root_unit_path"),"installation probe")
    if (service["invocation_id"]!=bind["operation_id"] or
        service["state_is_mountpoint"] is not True or
        type(service["state_device"]) is not int or service["state_device"]<1 or
        service["state_root_uid"]!=0 or service["state_root_gid"]!=0 or
        service["state_root_mode"] not in (0o700,0o750) or
        service["root_service_enabled"] is not False or
        service["box_service_installed"] is not False or
        service["root_socket_authorized"] is not False or
        service["root_unit_path"]!="usr/lib/systemd/system/zog-root-control.service"):
        reject("unverified STATE mount or unauthorized service/socket grants")
    witness=receipt["witnesses"]
    exact(witness,("native_worker","accepted_generation_owner"),"signatures")
    for name,item in witness.items():
        exact(item,("key_id","signature"),name)
        if not isinstance(item["key_id"],str) or not item["key_id"] or not isinstance(item["signature"],str):
            reject("signed-looking but incomplete witness")
    if any(k in receipt for k in ("accepted","approved","native_success","grant","authorization")):
        reject("receipt tries to grant authority")
    return {"shape":"COMPLETE_UNTRUSTED_EVIDENCE","native_admission":False}

def file_bytes(root,receipt,*,synthetic=False):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():reject("immutable rootfs not mounted")
    for name,meta in receipt["files"].items():
        p=root / path(name)
        # Reject symlinks in every ancestor, not only the leaf.
        current=root
        for part in path(name).parts:
            current=current/part
            if stat.S_ISLNK(current.lstat().st_mode):
                reject("symlink in source installed path: "+name)
        before=p.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:
            reject("not an immutable regular file")
        if (stat.S_IMODE(before.st_mode)!=meta["mode"] or
            before.st_uid!=meta["uid"] or before.st_gid!=meta["gid"] or
            (not synthetic and (before.st_uid!=0 or before.st_gid!=0))):
            reject("filesystem owner/mode differs from protected observation")
        h=hashlib.sha256();size=0
        with p.open("rb") as fh:
            while part:=fh.read(1024*1024):
                h.update(part);size+=len(part)
        after=p.lstat()
        if (before.st_ino,before.st_dev,before.st_mtime_ns,before.st_size)!=(after.st_ino,after.st_dev,after.st_mtime_ns,after.st_size):
            reject("race/replaced installed file")
        if size!=meta["size"] or h.hexdigest()!=meta["sha256"]:
            reject("installed file differs from signed receipt")
        if meta["kind"]=="elf":
            with p.open("rb") as fh:header=fh.read(64)
            if len(header)<64 or header[:5]!=b"\x7fELF\x02" or header[5]!=1 or struct.unpack_from("<H",header,18)[0]!=62:
                reject("not a selected x86_64 ELF")
        if name=="usr/bin/python3.12" and meta["kind"]!="elf":
            reject("selected interpreter is not ELF")
        if name in ("usr/bin/box-control","usr/bin/root-control"):
            if meta["kind"]!="script" or not p.read_bytes().startswith(b"#!/usr/bin/python3.12"):
                reject("controller console entry point selects Host Python")
            if meta["mode"]!=0o755:reject("controller entry point permissions changed")
        if name=="usr/lib/systemd/system/zog-root-control.service":
            if meta["mode"]!=0o644 or meta["kind"]!="data":
                reject("privileged root service file permissions changed")
            selected=literal(PKG/"root-control/stages/final/build.py")["install"][0][-1]
            sentinel="<<'ZOG_ROOT_CONTROL_UNIT'\n"
            if selected.count(sentinel)!=1:
                reject("root-control service source cannot be authenticated")
            original=selected.split(sentinel,1)[1].split("\nZOG_ROOT_CONTROL_UNIT",1)
            if len(original)!=2 or p.read_bytes()!=(original[0]+"\n").encode():
                reject("installed privileged root service not equal to approved source")
    return "INSTALLED_BYTES_MATCH_RECEIPT_NOT_ACCEPTED"

def wheel_record(root,receipt):
    """Validate the *installed* RECORD including wheel member bytes and entry points."""
    root=Path(root).resolve(strict=True)
    for name,entry in PROGRAMS.items():
        dist=name.replace("-","_")+"-0.1.0.dist-info"
        prefix=SITE/dist
        info=root / prefix / "METADATA"
        record=root / prefix / "RECORD"
        ep=root / prefix / "entry_points.txt"
        wheel=root / prefix / "WHEEL"
        if (not ep.is_file() or ep.is_symlink() or
            not wheel.is_file() or wheel.is_symlink()):
            reject("missing/forged console entry or WHEEL metadata")
        wheel_info=BytesParser().parsebytes(wheel.read_bytes())
        if ("py3-none-any" not in wheel_info.get_all("Tag",[]) or
            wheel_info.get("Root-Is-Purelib","").lower()!="true"):
            reject("unexpected controller wheel ABI/tag")
        metadata=BytesParser().parsebytes(info.read_bytes())
        if metadata.get("Name","").lower().replace("_","-")!=name or metadata.get("Version")!="0.1.0":
            reject("wheel Name/Version differs from pinned source")
        expected_requires=["image-build==0.2.0.dev5","dbus-next==0.2.3"]
        if name=="root-control":
            expected_requires.append("box-control==0.1.0")
        observed=metadata.get_all("Requires-Dist",[]) or []
        if sorted(x.lower().replace(" ","") for x in observed)!=sorted(expected_requires):
            reject("installed Requires-Dist is not the selected controller source graph")
        cfg=configparser.ConfigParser(interpolation=None)
        cfg.read_string(ep.read_text())
        if set(cfg.sections())!={"console_scripts"} or dict(cfg.items("console_scripts"))!={name:entry}:
            reject("wheel generated console script target substituted")
        rows=list(csv.reader(io.StringIO(record.read_text())))
        if not rows or len(rows)!=len(set(r[0] for r in rows)) or any(len(r)!=3 for r in rows):
            reject("missing/duplicate wheel RECORD entries")
        listed=set()
        for rel,encoded,sz in rows:
            # Wheel installers may write ../../../bin relative to site-packages.
            parts=list(SITE.parts)
            for p in PurePosixPath(rel).parts:
                if p=="..":
                    if not parts:reject("wheel RECORD escapes installation root")
                    parts.pop()
                elif p not in ("", "."):
                    parts.append(p)
            resolved="/".join(parts)
            path(resolved)
            listed.add(resolved)
            if resolved not in receipt["files"]:
                reject("wheel RECORD references unobserved byte")
            if not encoded and not sz and resolved==str(prefix/"RECORD"):
                continue
            if not encoded.startswith("sha256=") or not sz.isdigit():
                reject("wheel RECORD lacks SHA256 or size")
            data=(root/resolved).read_bytes()
            digest=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            if encoded!="sha256="+digest or int(sz)!=len(data):
                reject("wheel RECORD byte hash or size mismatch")
        if not {str(prefix/"METADATA"),str(prefix/"RECORD"),str(prefix/"WHEEL"),
                str(prefix/"entry_points.txt"),"usr/bin/"+name,
                f"usr/lib/python3.12/site-packages/zog/{name.replace('-','_')}/__init__.py"}.issubset(listed):
            reject("wheel RECORD missing installed namespace/module metadata")
    return "WHEEL_RECORD_BYTES_MATCH_NOT_ACCEPTED"

def verify_external_signatures(receipt,protected_policy):
    """Pins originate OUTSIDE receipt from independently protected host-install."""
    exact(protected_policy,("schema","binding","state_device","rootfs_device",
         "native_worker_key","generation_owner_key","native_worker_key_id",
         "generation_owner_key_id"),"protected policy")
    if protected_policy["schema"]!="zog-host-install-protected-resident-b-pins-v1" or protected_policy["binding"]!=receipt["binding"]:
        reject("no independently selected exact host/STATE/rootfs generation")
    if (type(protected_policy["state_device"]) is not int or
        protected_policy["state_device"]!=receipt["installation_probe"]["state_device"]):
        reject("STATE mount identity differs from installed protected policy")
    if type(protected_policy["rootfs_device"]) is not int or protected_policy["rootfs_device"]<1:
        reject("missing selected immutable rootfs mount identity")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    payload={k:v for k,v in receipt.items() if k!="witnesses"}
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    for role,policy_key,policy_name,domain in (
        ("native_worker","native_worker_key","native_worker_key_id",b"ZOG_RESIDENT_B_NATIVE_WORKER_V1\x00"),
        ("accepted_generation_owner","generation_owner_key","generation_owner_key_id",b"ZOG_RESIDENT_B_GENERATION_OWNER_V1\x00")):
        witness=receipt["witnesses"][role]
        if witness["key_id"]!=protected_policy[policy_name]:reject("signer identity replaced")
        try:
            pub=bytes.fromhex(protected_policy[policy_key])
            if len(pub)!=32:reject("wrong protected signer key size")
            signature=base64.b64decode(witness["signature"],validate=True)
            Ed25519PublicKey.from_public_bytes(pub).verify(signature,domain+canonical)
        except (ValueError,InvalidSignature,base64.binascii.Error) as exc:
            reject("signature failed for unsigned or substituted installed-generation evidence: "+role)
    return "PROTECTED_KEYS_SIGNATURES_MATCH_EXTERNAL_POLICY"

def inspect(rootfs,state_mount,receipt,protected_policy,*,synthetic=False):
    receipt_shape(receipt)
    verify_external_signatures(receipt,protected_policy)
    file_bytes(rootfs,receipt,synthetic=synthetic)
    wheel_record(rootfs,receipt)
    if not synthetic:
        selected_root=Path(rootfs)
        if (selected_root.is_symlink() or not selected_root.is_mount() or
            selected_root.stat().st_dev!=protected_policy["rootfs_device"]):
            reject("rootfs must be a real selected protected installed-generation mount")
        state=Path(state_mount)
        if state.is_symlink() or not state.is_mount():
            reject("STATE was not independently mounted")
        s=state.stat()
        if (s.st_dev!=protected_policy["state_device"] or
            stat.S_IMODE(s.st_mode)!=receipt["installation_probe"]["state_root_mode"] or
            (s.st_uid,s.st_gid)!=(0,0)):
            reject("protected STATE mount ownership/identity mismatch")
    return {
        "inspection":"SYNTHETIC_EVIDENCE_CONSISTENT" if synthetic else "INSTALLED_EVIDENCE_CONSISTENT",
        "generation_accepted":False,
        "service_activation_authorized":False,
        "native_compilation_claimed":False,
        "authority":"NO_GRANT_OR_ROOTFS_ACCEPTANCE"
    }

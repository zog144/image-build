"""Protected compiler-base acceptance for immutable toolchains AND compiler images.

This is *not* a compiler promotion, generation publication, recovery/repair,
authorization to dispatch, or a source-only acceptance verdict. A trusted,
separately installed Host owner must provision the public key and the exact
signed receipt outside caller-supplied pipeline JSON. A current native probe
can show present capability; it never reconstructs an old stage-two build.
"""
import base64
import hashlib
import json
import os
import platform
import re
import stat
from pathlib import Path, PurePosixPath

from .engine import read_selection
from .errors import ImageBuildError
from .metadata import identity

SCHEMA = "image-build-compiler-base-acceptance-v1"
BINDING = "image-build-compiler-base-binding-v1"
PROBE = "image-build-compiler-linker-probe-v1"
DOMAIN = b"ZOG_IMAGE_BUILD_COMPILER_BASE_ACCEPTANCE_V1\x00"
TARGET = re.compile(r"x86_64(?:-[a-z0-9_.]+)*-linux-gnu\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SHA = re.compile(r"sha256:[0-9a-f]{64}\Z")
SLOTS = ("compiler","linker","assembler","libc_header","abi_header","crt","libc")
MAX_RECEIPT = 64 * 1024
EXPECTED_PROBE_SECONDS = 120

def deny(msg):
    raise ImageBuildError("compiler base NOT ACCEPTED: " + msg)

def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",",":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")

def _no_duplicates(pairs):
    out={}
    for k,v in pairs:
        if k in out:deny("duplicate signed receipt field")
        out[k]=v
    return out

def exact(obj, fields, where):
    if type(obj) is not dict or set(obj)!=set(fields):
        deny("missing/unrecognized "+where+" fields")

def _read_file(path):
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    except OSError as exc:
        raise ImageBuildError("compiler base NOT ACCEPTED: protected receipt missing") from exc
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_RECEIPT:
            deny("receipt is not a bounded regular file")
        raw=os.read(fd,MAX_RECEIPT+1)
    finally:
        os.close(fd)
    if len(raw)>MAX_RECEIPT:deny("protected receipt too large")
    try:
        value=json.loads(raw,object_pairs_hook=_no_duplicates,
                         parse_constant=lambda _v:deny("nonfinite receipt field"))
    except (ValueError,UnicodeDecodeError,TypeError) as exc:
        raise ImageBuildError("compiler base NOT ACCEPTED: invalid receipt JSON") from exc
    return value,raw

def _file_identity(root,path,expected):
    if type(path) is not str or not path.startswith("usr/") or len(path)>256:
        deny("unsafe compiler/header/library path")
    rel=PurePosixPath(path)
    if ".." in rel.parts or "." in rel.parts or rel.as_posix()!=path:
        deny("unsafe compiler/header/library component")
    current=root
    for part in rel.parts:
        current=current/part
        if not current.exists() and not current.is_symlink():
            deny("selected compiler/header/library path missing")
        if current.is_symlink():
            # Permit normal compiler symlinks ONLY within this selected root.
            try:link=current.resolve(strict=True)
            except OSError:deny("selected compiler symlink target missing")
            try:link.relative_to(root)
            except ValueError:deny("compiler path leaves selected root")
    try:resolved=current.resolve(strict=True)
    except OSError:deny("selected compiler/header/library not installed")
    try:resolved.relative_to(root)
    except ValueError:deny("compiler path escapes selected root")
    if not resolved.is_file():deny("compiler/header/library identity is not a file")
    h=hashlib.sha256()
    before=resolved.stat()
    if before.st_size>128*1024*1024 or before.st_size<=0:
        deny("compiler input too large/empty for bounded inspection")
    with resolved.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
    after=resolved.stat()
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(
        after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
        deny("selected compiler bytes changed during inspection")
    if expected!="sha256:"+h.hexdigest():
        deny("compiler/header/library installed-byte identity changed")

def native_authority(path):
    """Read a root-owned installed issuer policy; installation remains Work-only.

    A uid-0 file is not by itself proof of the selected Host/installation:
    host-install/root-control must authenticate and install this exact policy.
    """
    if os.geteuid()!=0:
        raise PermissionError("protected compiler issuer policy requires root")
    location=Path(path)
    if not location.is_absolute() or location.is_symlink():
        deny("installed issuer path must be absolute and non-symlink")
    st=location.stat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or
        stat.S_IMODE(st.st_mode)!=0o600):
        deny("independent issuer policy is not root-owned 0600")
    value,_=_read_file(location)
    exact(value,("schema","host_id","installation_id","state_volume_id",
                 "project_id","key_id","ed25519_public_key","receipt_directory",
                 "execution_environment_sha256"),"installed issuer policy")
    root=Path(value["receipt_directory"])
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        deny("issuer receipt directory is not installed")
    rights=root.stat()
    if (rights.st_uid!=0 or rights.st_gid!=0 or
        stat.S_IMODE(rights.st_mode) not in (0o700,0o750)):
        deny("issuer receipt directory is not protected")
    return value


def _protected(builder):
    policy=getattr(builder,"compiler_base_authority",None)
    exact(policy,("schema","host_id","installation_id","state_volume_id",
                  "project_id","key_id","ed25519_public_key","receipt_directory",
                  "execution_environment_sha256"),"protected Host compiler authority")
    if policy["schema"]!="zog-protected-compiler-base-issuer-v1":
        deny("no authenticated protected authority selection")
    for item in ("host_id","installation_id","state_volume_id","project_id","key_id"):
        if type(policy[item]) is not str or not policy[item] or len(policy[item])>256:
            deny("protected Host/installation/STATE identity invalid")
    if type(policy["ed25519_public_key"]) is not str or not HEX64.fullmatch(policy["ed25519_public_key"]):
        deny("missing independently pinned Ed25519 issuer key")
    if type(policy["execution_environment_sha256"]) is not str or not SHA.fullmatch(policy["execution_environment_sha256"]):
        deny("execution environment not independently selected")
    directory=Path(policy["receipt_directory"])
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        deny("protected compiler receipt directory is unavailable")
    # Source code cannot itself establish that this policy/directory was installed
    # by root-control. That separate native owner authenticity check is required.
    return policy,directory

def validate_probe(probe, claim):
    exact(probe,("schema","status","base_generation_id","compiler_target",
                 "source_sha256","command_sha256","elapsed_seconds",
                 "controller_execution","isolation","include_paths","library_paths",
                 "linked_executable_sha256"),"native compiler probe")
    if probe["schema"]!=PROBE or probe["status"]!="passed" or (
        probe["base_generation_id"]!=claim["generation_id"] or
        probe["compiler_target"]!=claim["target_abi"]):
        deny("native capability probe targets different compiler generation/ABI")
    if (probe["source_sha256"]!=digest(b'#include <stdio.h>\nint main(void){puts("zog-compiler-probe");return 0;}\n')
        or probe["command_sha256"]!=claim["required_probe_command_sha256"]
        or type(probe["elapsed_seconds"]) is not int or
        not 0<probe["elapsed_seconds"]<=EXPECTED_PROBE_SECONDS
        or type(probe["linked_executable_sha256"]) is not str or
        not SHA.fullmatch(probe["linked_executable_sha256"])):
        deny("bounded compile/linker proof missing")
    e=probe["controller_execution"]
    exact(e,("runtime_id","invocation_id","journal_reference","exit_code",
             "cleanup_complete"),"controller invocation")
    if (not all(type(e[k]) is str and e[k] for k in (
        "runtime_id","invocation_id","journal_reference")) or
        e["exit_code"]!=0 or e["cleanup_complete"] is not True):
        deny("native probe controller execution incomplete")
    iso=probe["isolation"]
    if iso!={"read_only_root":True,"network_access":False,
             "pivot_root":True,"host_mounts_visible":False,
             "host_include_fallback":False,"host_library_fallback":False}:
        deny("native probe did not establish selected root isolation")
    for key in ("include_paths","library_paths"):
        paths=probe[key]
        if type(paths) is not list or not paths or len(paths)>80:
            deny("no bounded compiler search trace")
        for path in paths:
            if (type(path) is not str or not path.startswith(("/usr/","/lib/"))
                or ".." in PurePosixPath(path).parts
                or any(x in path for x in ("/host/","/home/","/opt/","/mnt/","/usr/local/"))):
                deny("unexpected Host include/library fallback")
    return True

def resolve(builder, selection, receipt_sha256):
    """Inspect exact original generation + externally pinned signed acceptance.

    Used during remote selection, durable prepare, execution and verification.
    The SHA argument is *only* an identity; it carries no authority.
    """
    if type(receipt_sha256) is not str or not SHA.fullmatch(receipt_sha256):
        deny("missing original protected acceptance receipt digest")
    policy,receipts=_protected(builder)
    generation=selection.generation
    if type(generation) is not str or not HEX64.fullmatch(generation):
        deny("original generation identity is invalid")
    path=receipts/(generation+".json")
    if path.is_symlink():deny("receipt path follows a symlink")
    signed,raw=_read_file(path)
    if digest(raw)!=receipt_sha256:
        deny("source request receipt digest not equal to protected byte identity")
    exact(signed,("schema","key_id","claim","signature"),"signed acceptance envelope")
    if signed["schema"]!=SCHEMA or signed["key_id"]!=policy["key_id"]:
        deny("signed acceptance authority replaced")
    claim=signed["claim"]
    exact(claim,("schema","status","generation_id","generation_kind",
                 "generation_manifest_sha256","generation_inventory_sha256",
                 "generation_record_sha256","host_id","installation_id",
                 "state_volume_id","project_id","execution_environment_sha256",
                 "target_abi","installed_paths","historical_provenance",
                 "native_probe","required_probe_command_sha256"),"compiler-base claim")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        signature=base64.b64decode(signed["signature"],validate=True)
        if len(signature)!=64:deny("invalid signed acceptance signature length")
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(
            policy["ed25519_public_key"])).verify(signature,DOMAIN+canonical(claim))
    except ImportError as exc:
        raise ImageBuildError("compiler base NOT ACCEPTED: native Ed25519 verifier unavailable") from exc
    except (InvalidSignature,ValueError,TypeError,base64.binascii.Error) as exc:
        raise ImageBuildError("compiler base NOT ACCEPTED: independent issuer signature invalid") from exc
    if claim["schema"]!=SCHEMA or claim["status"]!="independently-accepted-for-compiler-use":
        deny("no independently selected compiler-base acceptance")
    for key in ("host_id","installation_id","state_volume_id","project_id",
                "execution_environment_sha256"):
        if claim[key]!=policy[key]:
            deny("Host/installation/STATE/environment acceptance mismatch")
    runner=getattr(builder,"runner",None)
    execute=getattr(runner,"execute",None)
    if not hasattr(execute,"configuration") or (
        digest(canonical(execute.configuration()))!=claim["execution_environment_sha256"]):
        deny("actual box-control execution configuration changed")
    root=Path(builder.state)/"image-build"/"generations"/generation
    if root.is_symlink() or not root.is_dir() or (root/"manifest.json").is_symlink():
        deny("canonical selected generation not present")
    reread=read_selection(root)
    if reread.generation!=generation or reread.manifest!=selection.manifest:
        deny("selected base is not the reopened canonical generation")
    manifest_raw=(root/"manifest.json").read_bytes()
    manifest=reread.manifest
    if (claim["generation_id"]!=generation or
        claim["generation_kind"]!=manifest.get("kind") or
        claim["generation_kind"] not in ("toolchain","image") or
        claim["generation_manifest_sha256"]!=digest(manifest_raw) or
        claim["generation_inventory_sha256"]!="sha256:"+identity(manifest["outputs"]) or
        claim["target_abi"] not in ("x86_64-linux-gnu","x86_64-pc-linux-gnu","x86_64-unknown-linux-gnu") or
        manifest.get("inputs",{}).get("architecture")!="x86_64" or
        platform.machine()!="x86_64"):
        deny("selected compiler generation bytes/kind/target ABI differ")
    record=manifest.get("build_record")
    historical=claim["historical_provenance"]
    exact(historical,("status","missing","retained_evidence_sha256"),"historical provenance")
    if manifest["kind"]=="toolchain":
        if (manifest.get("stage")!=2 or manifest.get("self_hosted") is not True
            or historical!={"status":"complete","missing":[],
                            "retained_evidence_sha256":None} or
            type(record) is not dict):
            deny("stage-two toolchain provenance or promotion incomplete")
        from .generation_provenance import verify
        if getattr(builder,"provenance",None) is None:
            deny("canonical toolchain Build Record owner unavailable")
        verify(builder.provenance,reread)
    else:
        # Independently accepted compiler images are not relabelled and must
        # carry precise historical gaps rather than fabricated stage-two proof.
        if historical["status"]!="historical-gap-declared" or (
            type(historical["missing"]) is not list or
            not historical["missing"] or len(historical["missing"])>32 or
            not all(type(x) is str and 0<len(x)<256 for x in historical["missing"]) or
            type(historical["retained_evidence_sha256"]) is not str or
            not SHA.fullmatch(historical["retained_evidence_sha256"])):
            deny("compiler image missing explicit historical provenance gap")
    record_digest=record.get("record") if isinstance(record,dict) else None
    if record_digest!=claim["generation_record_sha256"] or (
        record_digest is not None and not SHA.fullmatch(record_digest)):
        deny("original generation Build Record identity fabricated")
    files=claim["installed_paths"]
    exact(files,SLOTS,"compiler/header/library installed paths")
    if (files["compiler"]["path"]!="usr/bin/gcc" or
        files["linker"]["path"]!="usr/bin/ld" or
        files["assembler"]["path"]!="usr/bin/as" or
        files["libc_header"]["path"]!="usr/include/stdio.h"):
        deny("compiler role paths differ from fixed native probe executable and headers")
    for role in SLOTS:
        desc=files[role]
        exact(desc,("path","sha256"),"installed compiler role "+role)
        if type(desc["sha256"]) is not str or not SHA.fullmatch(desc["sha256"]):
            deny("missing compiler/header/library digest")
        _file_identity(reread.root,desc["path"],desc["sha256"])
    if type(claim["required_probe_command_sha256"]) is not str or not SHA.fullmatch(
        claim["required_probe_command_sha256"]):
        deny("native probe program not pinned")
    from .compiler_base_probe import COMMAND_SHA256
    if claim["required_probe_command_sha256"]!=COMMAND_SHA256:
        deny("native compile/link probe instructions substituted")
    validate_probe(claim["native_probe"],claim)
    included=claim["native_probe"]["include_paths"]
    linked=claim["native_probe"]["library_paths"]
    if (("/"+files["libc_header"]["path"] not in included or
         "/"+files["crt"]["path"] not in linked or
         "/"+files["libc"]["path"] not in linked)):
        deny("native compiler/header/library search traces disagree with inspected files")
    if (root/"manifest.json").read_bytes()!=manifest_raw:
        deny("original generation changed after verifier inspection")
    return {
        "schema":BINDING,
        "generation_id":generation,"generation_kind":manifest["kind"],
        "generation_manifest_sha256":claim["generation_manifest_sha256"],
        "generation_inventory_sha256":claim["generation_inventory_sha256"],
        "generation_record_sha256":record_digest,
        "host_id":claim["host_id"],"installation_id":claim["installation_id"],
        "state_volume_id":claim["state_volume_id"],
        "project_id":claim["project_id"],"execution_environment_sha256":
            claim["execution_environment_sha256"],
        "target_abi":claim["target_abi"],
        "compiler_files_sha256":digest(canonical(files)),
        "native_probe_sha256":digest(canonical(claim["native_probe"])),
        "historical_provenance":historical,
        "acceptance_receipt_sha256":receipt_sha256,
        "status":"independent-compiler-capability-observed-not-job-authorization",
    }

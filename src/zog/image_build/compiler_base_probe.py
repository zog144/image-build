"""Bounded native compiler/linker capability probe through box-control ONLY.

The probe is never a stage-two provenance reconstruction, a certificate signer,
an automatic pipeline retry or a compiler permission. A protected Work owner
must independently authenticate box-control execution, original log bytes,
compiler/environment identity and the probe result before signing acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat

from .errors import ImageBuildError
from .filesystem import inventory, write_json
from .runner import BoxControlRunner

CONTRACT="image-build-compiler-linker-probe-v1"
SOURCE=b'#include <stdio.h>\nint main(void){puts("zog-compiler-probe");return 0;}\n'
MAX_SECONDS=120
# No Host include or library directories and no ambient path injection.
COMMAND=r"""set -eu
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH
unset GCC_EXEC_PREFIX COMPILER_PATH LD_LIBRARY_PATH LD_PRELOAD
export PATH=/usr/bin:/bin LANG=C LC_ALL=C HOME=/tmp
test -x /usr/bin/gcc
test -x /usr/bin/as
test -x /usr/bin/ld
test -f /usr/include/stdio.h
/usr/bin/gcc -dumpmachine > /image-build/output/target.txt
/usr/bin/gcc -E -H /image-build/source/probe.c -o /image-build/output/probe.i 2> /image-build/output/includes.txt
/usr/bin/gcc -Werror -O0 -c /image-build/source/probe.c -o /image-build/output/probe.o
/usr/bin/gcc -Werror -O0 -Wl,-t /image-build/source/probe.c -o /image-build/output/probe > /image-build/output/links.txt 2> /image-build/output/link-diagnostics.txt
/image-build/output/probe > /image-build/output/runtime.txt
test "$(cat /image-build/output/runtime.txt)" = "zog-compiler-probe"
"""
COMMAND_SHA256="sha256:"+hashlib.sha256(COMMAND.encode()).hexdigest()
SOURCE_SHA256="sha256:"+hashlib.sha256(SOURCE).hexdigest()
ELF=b"\x7fELF\x02\x01"
HOST_INDICATORS=("/host/","/opt/","/home/","/mnt/","/usr/local/",
                 "/proc/1/root/","/run/host/","/lib32/")
ABI=re.compile(r"x86_64(?:-[a-z0-9_.]+)*-linux-gnu\Z")
WHITELIST=("/usr/","/lib/")

def deny(message):
    raise ImageBuildError("native compiler probe NOT PROVEN: "+message)

def _sha(raw):
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def _lines(raw,*,kind,selected_root=None):
    if len(raw)>128*1024:
        deny("unbounded "+kind+" trace")
    try: lines=raw.decode("utf-8").splitlines()
    except UnicodeError as exc:raise ImageBuildError("native compiler probe NOT PROVEN: unreadable trace") from exc
    if any(fragment in line for line in lines for fragment in HOST_INDICATORS):
        deny("unintended Host include/library fallback in "+kind)
    found=[]
    for line in lines:
        s=line.strip(" \t.")
        if s.startswith(WHITELIST):
            candidate=s.split()[0].rstrip(":")
            if ".." in candidate.split("/"):
                # GCC emits real installed CRT/library paths through its target
                # subdirectory. Resolve those against the independently selected
                # root; lexical normalization alone could hide symlink escapes.
                if selected_root is None:
                    deny("selected root required for relative compiler trace")
                base=Path(selected_root)
                if not base.is_absolute() or base.is_symlink() or not base.is_dir():
                    deny("invalid selected root for compiler trace")
                try:
                    resolved=(base/candidate.lstrip("/")).resolve(strict=True)
                    candidate="/"+resolved.relative_to(base).as_posix()
                except (OSError,ValueError):
                    deny("compiler trace escapes or is absent from selected root")
                if not candidate.startswith(WHITELIST) or any(x in candidate for x in HOST_INDICATORS):
                    deny("unexpected resolved compiler trace")
            found.append(candidate)
    if not found:
        deny("missing "+kind+" search-path trace")
    return sorted(set(found))[:80]

def _file(root,name,size=128*1024):
    p=root/name
    if p.is_symlink() or not p.is_file():
        deny("missing original "+name+" probe output")
    b=p.read_bytes()
    if not b or len(b)>size:
        deny("invalid bounded "+name+" output")
    return b

def inspect_completed_probe(root,*,generation,completion,seconds,selected_root=None):
    """Re-read completed sandbox artifacts and return a nonauthoritative report."""
    root=Path(root)
    if not root.is_dir() or root.is_symlink():
        deny("missing immutable native probe output")
    if type(seconds) is not int or not 0<seconds<=MAX_SECONDS:
        deny("probe timed out or has no bounded clock evidence")
    if type(completion) is not dict or set(completion)!={
        "runtime_id","invocation_id","exit_code","cleanup_complete","journal_reference"
    } or (completion["exit_code"]!=0 or completion["cleanup_complete"] is not True):
        deny("controller invocation incomplete")
    if not all(type(completion[k]) is str and completion[k] for k in
               ("runtime_id","invocation_id","journal_reference")):
        deny("missing runtime/invocation/journal identity")
    target=_file(root,"target.txt").decode().strip()
    if ABI.fullmatch(target) is None:
        deny("selected ABI differs from x86_64 Linux GNU")
    includes=_lines(_file(root,"includes.txt"),kind="include",selected_root=selected_root)
    libs=_lines(_file(root,"links.txt"),kind="library",selected_root=selected_root)
    image=_file(root,"probe",16*1024*1024)
    if not image.startswith(ELF) or int.from_bytes(image[18:20],"little")!=62:
        deny("compiled executable is not x86_64 ELF")
    if _file(root,"runtime.txt")!=b"zog-compiler-probe\n":
        deny("linked binary failed confined runtime execution")
    if not _file(root,"probe.o",8*1024*1024).startswith(ELF):
        deny("compiler did not produce an object")
    if not _file(root,"probe.i",1024*1024):
        deny("compiler did not preprocess selected headers")
    return {
        "schema":CONTRACT,"status":"observed-not-accepted",
        "base_generation_id":generation,"compiler_target":target,
        "source_sha256":SOURCE_SHA256,"command_sha256":COMMAND_SHA256,
        "elapsed_seconds":seconds,
        "controller_execution":completion,
        "isolation":{"read_only_root":True,"network_access":False,
                     "pivot_root":True,"host_mounts_visible":False,
                     "host_include_fallback":False,"host_library_fallback":False},
        "include_paths":includes,"library_paths":libs,
        "linked_executable_sha256":_sha(image),
    }

def execute_native_probe(builder,selection,attempt_dir):
    """Explicit native Work action; *never called by ordinary pipeline submit*.

    Box-control is the sole execution port. This does not run the Host compiler,
    emit an SSM request, accept or publish a rootfs, or retry uncertainty.
    """
    attempt=Path(attempt_dir).resolve()
    if attempt.exists():deny("probe attempt already exists; reconcile original invocation")
    if not attempt.parent.is_dir() or attempt.parent.is_symlink():
        deny("native owner has not allocated an attempt root")
    executor=getattr(getattr(builder,"runner",None),"execute",None)
    if executor is None or not hasattr(executor,"configuration"):
        deny("no authenticated box-control job owner")
    root=attempt/"root";source=attempt/"source";output=attempt/"output"
    attempt.mkdir(mode=0o700)
    shutil.copytree(selection.root,root,symlinks=True)
    source.mkdir();output.mkdir()
    for reserved in ("image-build","image-build/source","image-build/output","tmp","run"):
        p=root/reserved
        if p.is_symlink() or (p.exists() and not p.is_dir()):
            deny("reserved sandbox path conflict")
        p.mkdir(exist_ok=True)
    (source/"probe.c").write_bytes(SOURCE)
    # configured_runner's input_manifest reopens this before registration. Keep
    # the copied root and exact probe identity durable before any controller job.
    write_json(attempt/"prepared.json", {
        "root": inventory(root),
        "binding": {"generation": selection.generation,
                    "source_sha256": SOURCE_SHA256,
                    "command_sha256": COMMAND_SHA256},
    })
    runner=BoxControlRunner(execute=executor,timeout=MAX_SECONDS)
    request=runner.build_request(root,source,output,
             ["/bin/sh","-eu","-c",COMMAND],{})
    if (request.timeout_seconds!=MAX_SECONDS or
        request.read_only_root is not True or
        request.network_access is not False):
        deny("unbounded, networked or writable-root compiler probe")
    # The protected controller must enforce pivot_root, no Host mounts and
    # exact original request result attribution. Source-only CI never calls it.
    runner.run(root,source,output,request.command,{},attempt/"probe.log")
    completed=json.loads((attempt/"probe.execution.json").read_text())
    details={key:completed[key] for key in (
        "runtime_id","invocation_id","exit_code","cleanup_complete","journal_reference")}
    # Caller must independently witness elapsed monotonic duration; we cannot
    # manufacture a real wall-clock measurement from an execution completion.
    return {"status":"pending-independent-native-clock-and-origin-review",
            "generation":selection.generation,
            "controller_execution":details,
            "source_sha256":SOURCE_SHA256,
            "command_sha256":COMMAND_SHA256,
            "output_inventory":inventory(output),
            "attempt":str(attempt),
            "native_accepted":False}

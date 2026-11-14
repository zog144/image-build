"""Synthetic native-capture fixtures; do not treat test objects as genuine builds."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures/mesa-native-evidence"


def module():
    spec = importlib.util.spec_from_file_location(
        "mesa_native_evidence", ROOT / "tools/verify_mesa_native_evidence.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_elf(*, soname, needed=(), runpath=()):
    """Tiny real ELF64/LE dynamic section with no executable machine code."""
    strings = bytearray(b"\x00")
    def add(s):
        pos = len(strings)
        strings.extend(s.encode() + b"\x00")
        return pos
    sname = add(soname)
    wants = [add(n) for n in needed]
    path = add(":".join(runpath)) if runpath else None
    entries = [(5, 0x400300), (10, len(strings)), (14, sname)]
    entries.extend((1, n) for n in wants)
    if path is not None:
        entries.append((29, path))
    entries.append((0, 0))
    data = bytearray(1024)
    ident = b"\x7fELF" + b"\x02\x01\x01" + b"\x00" * 9
    struct.pack_into("<16sHHIQQQIHHHHHH", data, 0, ident, 3, 62, 1,
                     0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0x400000, 0, 1024, 1024, 4096)
    struct.pack_into("<IIQQQQQQ", data, 120, 2, 6, 0x100, 0x400100,
                     0, len(entries) * 16, len(entries) * 16, 8)
    for i, entry in enumerate(entries):
        struct.pack_into("<qQ", data, 0x100 + 16 * i, *entry)
    data[0x300:0x300 + len(strings)] = strings
    return bytes(data)


def record(root, name, content):
    file = root / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(content)
    return sha(content)


def fixture(tmp_path):
    testroot = tmp_path / "native-synthetic"
    roots = {k: testroot / k for k in ("source", "build", "destdir", "software")}
    for directory in roots.values():
        directory.mkdir(parents=True)
    src = "src/demo.c"
    obj = "obj/demo.o"
    compiled = b"int demo(void) { return 1; }\n"
    record(roots["source"], src, compiled)
    object_hash = record(roots["build"], obj, b"synthetic object")
    header = "include/demo.h"
    header_bytes = b"#define DEMO_VALUE 1\n"
    record(roots["source"], header, header_bytes)
    dep_path = "dep/demo.d"
    dep_bytes = (str(roots["build"] / obj) + ": " + str(roots["source"] / src) +
                 " " + str(roots["source"] / header) + "\n").encode()
    dep_sha = record(roots["build"], dep_path, dep_bytes)
    compiler = roots["software"] / "bin/cc"
    compiler.parent.mkdir()
    compiler.write_bytes(b"synthetic compiler")
    compiler_hash = sha(compiler.read_bytes())
    record(roots["software"], "lib/libzog.so.1", make_elf(soname="libzog.so.1"))
    so = make_elf(soname="libdemo.so", needed=("libzog.so.1",))
    sohash = record(roots["destdir"], "usr/lib/libdemo.so", so)
    link_output = "lib/libdemo.so"
    link_sha = record(roots["build"], link_output, so)
    notice = b"Original synthetic terms and copyright.\n"
    nsha = record(roots["destdir"], "usr/share/licenses/mesa/terms.txt", notice)
    drafts = tmp_path / "drafts"
    mesa = drafts / "mesa"
    (mesa / "stages/final").mkdir(parents=True)
    upstream_sha = "a" * 64
    (mesa / "upstream.py").write_text(repr({"sha256": upstream_sha}))
    (mesa / "license.py").write_text(repr({
        "status": "unresolved",
        "evidence": [{"path": "mesa-25.3.0/LICENSE",
                      "sha256": nsha, "source_sha256": upstream_sha}]}))
    (mesa / "stages/final/produce-manifest.py").write_text(repr({
        "required": ["usr/lib/libdemo.so", "usr/share/licenses/mesa/terms.txt"]}))
    (drafts / "rights-admission-evidence.json").write_text(json.dumps({
        "rights_approved": False, "canonical_admitted": False,
        "components": {"mesa": {"original_member_delivery_plan": [{
            "original_member": "mesa-25.3.0/LICENSE",
            "installed_path": "usr/share/licenses/mesa/terms.txt"}]}}}))
    source_file = str(roots["source"] / src)
    object_file = str(roots["build"] / obj)
    sidecars = {
        "compile_commands": [{
            "directory": str(roots["build"]), "file": source_file,
            "output": object_file,
            "arguments": [str(compiler), "-MD", "-MF",
                          str(roots["build"] / dep_path),
                          "-c", source_file, "-o", object_file,
                          "-I", str(roots["source"])]}],
        "source_objects": [{
            "source_root": "source", "source": src, "source_sha256": sha(compiled),
            "object": obj, "object_sha256": object_hash, "generated_inputs": []}],
        "implicit_inputs": [{
            "object": obj, "depfile": dep_path, "depfile_sha256": dep_sha,
            "inputs": [
                {"root":"source", "path":src, "sha256":sha(compiled)},
                {"root":"source", "path":header, "sha256":sha(header_bytes)},
            ],
        }],
        "link_commands": [{
            "installed_path": "usr/lib/libdemo.so", "output": link_output,
            "output_sha256": link_sha,
            "arguments": [str(compiler), "-shared", object_file,
                          "-o", str(roots["build"] / link_output)],
            "inputs": [{"root":"build", "path":obj, "sha256":object_hash}],
        }],
        "installed_inventory": [{
            "path": "usr/lib/libdemo.so", "type": "file", "sha256": sohash
        }, {"path": "usr/share/licenses/mesa/terms.txt",
            "type": "file", "sha256": nsha}],
        "elf_dependencies": [{
            "path": "usr/lib/libdemo.so", "soname": "libdemo.so",
            "needed": ["libzog.so.1"], "rpath": [], "runpath": []}],
        "library_provenance": [{
            "consumer": "usr/lib/libdemo.so", "needed": "libzog.so.1",
            "root": "software", "path": "lib/libzog.so.1",
            "sha256": sha((roots["software"] / "lib/libzog.so.1").read_bytes())}],
        "delivered_notices": [{
            "path": "usr/share/licenses/mesa/terms.txt",
            "original_member": "mesa-25.3.0/LICENSE", "sha256": nsha}],
    }
    envelope = {
        "schema": "zog-mesa-native-evidence-v1",
        "component": "mesa", "source_archive_sha256": upstream_sha,
        "capture_status": "untrusted-observation",
        "roots": {k: str(v) for k, v in roots.items()},
        "compilers": [{"path": str(compiler), "sha256": compiler_hash}],
        "evidence": {},
    }
    def save():
        for key, payload in sidecars.items():
            name = key + ".json"
            envelope["evidence"][key] = {
                "file": name, "sha256": record(testroot, name,
                    json.dumps(payload, sort_keys=True).encode())}
        record(testroot, "evidence.json", json.dumps(envelope, sort_keys=True).encode())
    save()
    return {"root": testroot, "roots": roots, "drafts": drafts,
            "sidecars": sidecars, "envelope": envelope, "save": save}


@pytest.fixture
def native(tmp_path):
    return fixture(tmp_path)


def test_synthetic_positive_is_consistency_only(native):
    result = module().verify(native["root"], native["drafts"])
    assert result["compile_units"] == 1
    assert result["installed_files"] == 2
    assert result["elf_objects"] == 1
    assert result["linked_dependencies"] == 1
    assert result["original_notices"] == 1
    assert result["status"] == "evidence-consistent-not-native-accepted"
    assert result["native_accepted"] is False
    assert result["source_archives_independently_accepted"] is False
    assert result["redistribution_authorized"] is False


def test_actual_elf_dynamic_parser_never_uses_claimed_report(native):
    elf = native["roots"]["destdir"] / "usr/lib/libdemo.so"
    assert module().elf_dynamic(elf) == {
        "needed": ["libzog.so.1"], "soname": "libdemo.so",
        "runpath": [], "rpath": []}


@pytest.mark.parametrize("tamper", json.loads((FIXTURES / "tamper-cases.json").read_text()))
def test_tampered_synthetic_bundle_fails_closed(native, tamper):
    sc = native["sidecars"]
    env = native["envelope"]
    roots = native["roots"]
    if tamper == "wrong-archive":
        env["source_archive_sha256"] = "b" * 64
    elif tamper == "missing-compiler-unit":
        sc["compile_commands"][:] = []
    elif tamper == "changed-object-byte":
        (roots["build"] / "obj/demo.o").write_bytes(b"tampered")
    elif tamper == "host-include":
        sc["compile_commands"][0]["arguments"].extend(["-I/usr/include"])
    elif tamper == "host-compiler":
        sc["compile_commands"][0]["arguments"][0] = "/usr/bin/cc"
    elif tamper == "mismatched-compile-object":
        sc["source_objects"][0]["object"] = "obj/wrong.o"
    elif tamper == "missing-source-map":
        sc["source_objects"].clear()
    elif tamper == "extra-destdir-file":
        record(roots["destdir"], "usr/lib/hidden.so", b"hidden")
    elif tamper == "missing-installed-file":
        sc["installed_inventory"].pop()
    elif tamper == "changed-installed-byte":
        (roots["destdir"] / "usr/lib/libdemo.so").write_bytes(b"modified")
    elif tamper == "unlisted-elf":
        sc["elf_dependencies"].clear()
    elif tamper == "forged-needed":
        sc["elf_dependencies"][0]["needed"] = ["libhost.so"]
    elif tamper == "host-library":
        sc["library_provenance"][0]["root"] = "host"
    elif tamper == "wrong-library-soname":
        record(roots["software"], "lib/libzog.so.1", make_elf(soname="libevil.so"))
        sc["library_provenance"][0]["sha256"] = sha(
            (roots["software"] / "lib/libzog.so.1").read_bytes())
    elif tamper == "wrong-notice":
        record(roots["destdir"], "usr/share/licenses/mesa/terms.txt", b"altered rights")
        changed = sha((roots["destdir"] / "usr/share/licenses/mesa/terms.txt").read_bytes())
        sc["installed_inventory"][1]["sha256"] = changed
        sc["delivered_notices"][0]["sha256"] = changed
    elif tamper == "missing-notice":
        sc["delivered_notices"].clear()
    elif tamper == "self-authorized":
        env["native_accepted"] = True
    elif tamper == "bad-sidecar":
        native["save"]()
        (native["root"] / "source_objects.json").write_bytes(b"forged")
        with pytest.raises((module().EvidenceError, KeyError, ValueError, OSError)):
            module().verify(native["root"], native["drafts"])
        return
    else:
        raise AssertionError("missing test implementation: " + tamper)
    # Resign every synthetic sidecar after mutations: forged SHA references
    # cannot hide semantic inconsistencies from the verifier.
    native["save"]()
    with pytest.raises((module().EvidenceError, KeyError, ValueError, OSError)):
        module().verify(native["root"], native["drafts"])


def test_destdir_symlink_escape(native):
    root = native["roots"]["destdir"]
    notice = root / "usr/share/licenses/mesa/terms.txt"
    notice.unlink()
    notice.symlink_to("/etc/passwd")
    native["sidecars"]["installed_inventory"][1] = {
        "path": "usr/share/licenses/mesa/terms.txt",
        "type": "symlink", "target": "/etc/passwd"}
    native["save"]()
    verifier = module()
    with pytest.raises(verifier.EvidenceError):
        verifier.verify(native["root"], native["drafts"])


def test_generated_source_needs_generator_provenance(native):
    source = native["sidecars"]["source_objects"][0]
    source["source_root"] = "build"
    source["generated_inputs"] = []
    native["save"]()
    verifier = module()
    with pytest.raises(verifier.EvidenceError, match="generated source"):
        verifier.verify(native["root"], native["drafts"])


def test_evidence_consistency_does_not_authorize_approval(native):
    native["envelope"]["approved"] = True
    native["save"]()
    verifier = module()
    with pytest.raises(verifier.EvidenceError, match="assert authorization"):
        verifier.verify(native["root"], native["drafts"])


def test_realistic_compilation_database_relative_paths_and_optional_output(native):
    import os
    cmd = native["sidecars"]["compile_commands"][0]
    directory = native["roots"]["build"]
    cmd.pop("output")
    cmd["file"] = os.path.relpath(cmd["file"], directory)
    cmd["arguments"] = [
        cmd["arguments"][0], "-MD", "-MF", "dep/demo.d",
        "-c", cmd["file"], "-o", "obj/demo.o",
        "-I", os.path.relpath(native["roots"]["source"], directory)]
    native["save"]()
    report = module().verify(native["root"], native["drafts"])
    assert report["compile_units"] == 1
    assert report["native_accepted"] is False


def test_compilation_database_wrong_optional_output_rejected(native):
    cmd = native["sidecars"]["compile_commands"][0]
    cmd["output"] = str(native["roots"]["build"] / "obj/another.o")
    native["save"]()
    verifier = module()
    with pytest.raises((verifier.EvidenceError, FileNotFoundError)):
        verifier.verify(native["root"], native["drafts"])


def test_library_runpath_escape_is_rejected_from_actual_elf_bytes(native):
    binary = native["roots"]["destdir"] / "usr/lib/libdemo.so"
    altered = make_elf(soname="libdemo.so", needed=("libzog.so.1",),
                       runpath=("/usr/lib",))
    binary.write_bytes(altered)
    linkfile = native["roots"]["build"] / "lib/libdemo.so"
    linkfile.write_bytes(altered)
    native["sidecars"]["link_commands"][0]["output_sha256"] = sha(altered)
    native["sidecars"]["installed_inventory"][0]["sha256"] = sha(altered)
    native["sidecars"]["elf_dependencies"][0]["runpath"] = ["/usr/lib"]
    native["save"]()
    verifier = module()
    with pytest.raises(verifier.EvidenceError, match="RPATH/RUNPATH"):
        verifier.verify(native["root"], native["drafts"])

"""Independent adversarial read-through of source-only Mesa native evidence checks.

Forged evidence is deliberately *untrusted*, including when self-consistent.
"""
import hashlib
import importlib.util
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "mesa_native_fixture", ROOT / "tests/test_mesa_native_evidence.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


@pytest.fixture
def capture(tmp_path):
    return base.fixture(tmp_path)


def check_reject(capture, match=None):
    v = base.module()
    capture["save"]()
    with pytest.raises(v.EvidenceError, match=match):
        v.verify(capture["root"], capture["drafts"])


def test_forged_self_consistent_source_is_not_authenticated(capture):
    """A liar can update ALL supplied hashes. It must never obtain admission."""
    source = capture["roots"]["source"] / "src/demo.c"
    source.write_bytes(b"int demo(void) { /* not pinned upstream */ return 99; }\n")
    changed = base.sha(source.read_bytes())
    capture["sidecars"]["source_objects"][0]["source_sha256"] = changed
    capture["sidecars"]["implicit_inputs"][0]["inputs"][0]["sha256"] = changed
    # The archive SHA, compiler output and native identity were only assertions
    # in this forged capture. We cannot authenticate them here.
    capture["save"]()
    report = base.module().verify(capture["root"], capture["drafts"])
    assert report["status"] == "evidence-consistent-not-native-accepted"
    assert report["native_accepted"] is False
    assert report["source_archives_independently_accepted"] is False
    assert report["redistribution_authorized"] is False


def test_unreported_object_even_with_consistent_json_is_rejected(capture):
    base.record(capture["roots"]["build"], "obj/unreported.o", b"hidden object")
    check_reject(capture, "unreported or missing build object")


def test_depfile_omitted_header_not_sufficient(capture):
    capture["sidecars"]["implicit_inputs"][0]["inputs"].pop()
    check_reject(capture, "depfile/input digest inventory")


def test_host_header_hidden_in_depfile_is_rejected(capture):
    roots = capture["roots"]
    object_path = str(roots["build"] / "obj/demo.o")
    file_path = str(roots["source"] / "src/demo.c")
    header = str(roots["source"] / "include/demo.h")
    dep = f"{object_path}: {file_path} {header} /etc/passwd\n".encode()
    digest = base.record(roots["build"], "dep/demo.d", dep)
    capture["sidecars"]["implicit_inputs"][0]["depfile_sha256"] = digest
    check_reject(capture, "Host implicit compiler dependency")


def test_mmd_excludes_system_headers_and_is_rejected(capture):
    cmd = capture["sidecars"]["compile_commands"][0]["arguments"]
    cmd[cmd.index("-MD")] = "-MMD"
    check_reject(capture, "system-inclusive -MD")


@pytest.mark.parametrize("option", ["-include", "-imacros", "--sysroot",
                                    "-Xclang", "-fplugin=/tmp/code.so",
                                    "-Wp,-I/usr/include", "-save-temps"])
def test_unsupported_implicit_compiler_input_is_rejected(capture, option):
    capture["sidecars"]["compile_commands"][0]["arguments"].append(option)
    check_reject(capture, "unsupported implicit")


def test_additional_unmapped_compiler_source_is_rejected(capture):
    arg = str(capture["roots"]["source"] / "src/demo.c")
    capture["sidecars"]["compile_commands"][0]["arguments"].append(arg)
    check_reject(capture, "additional unreviewed compiler input")


@pytest.mark.parametrize("option", [
    "-Wl,-rpath,/usr/lib", "-Xlinker", "@response.rsp",
    "-T/tmp/ldscript", "-L/usr/lib", "-lhost", "-fuse-ld=host"])
def test_unsupported_linker_flags_do_not_disappear_from_capture(capture, option):
    capture["sidecars"]["link_commands"][0]["arguments"].append(option)
    check_reject(capture, "unsupported opaque linker input")


def test_archive_input_needs_independent_member_expansion(capture):
    archive = capture["roots"]["build"] / "lib/libhidden.a"
    archive.write_bytes(b"fake static archive")
    capture["sidecars"]["link_commands"][0]["arguments"].insert(3, str(archive))
    check_reject(capture, "archive/linker script/opaque library input")


def test_linker_object_omission_is_detected(capture):
    capture["sidecars"]["link_commands"][0]["inputs"].clear()
    check_reject(capture, "unreported/missing linker inputs")


def test_non_reachable_claimed_library_provider_is_rejected(capture):
    roots = capture["roots"]
    original = roots["software"] / "lib/libzog.so.1"
    base.record(roots["software"], "hidden/libzog.so.1", original.read_bytes())
    capture["sidecars"]["library_provenance"][0]["path"] = "hidden/libzog.so.1"
    check_reject(capture, "outside modeled loader search")


def replace_installed_elf(capture, payload):
    roots = capture["roots"]
    (roots["destdir"] / "usr/lib/libdemo.so").write_bytes(payload)
    (roots["build"] / "lib/libdemo.so").write_bytes(payload)
    digest = base.sha(payload)
    capture["sidecars"]["installed_inventory"][0]["sha256"] = digest
    capture["sidecars"]["link_commands"][0]["output_sha256"] = digest


def test_dt_needed_absolute_host_path_is_forbidden(capture):
    raw = base.make_elf(soname="libdemo.so", needed=("/usr/lib/libhost.so",))
    replace_installed_elf(capture, raw)
    check_reject(capture, "DT_NEEDED contains a path")


def test_elf_filter_dependency_tag_is_forbidden(capture):
    raw = bytearray(base.make_elf(soname="libdemo.so", needed=("libzog.so.1",)))
    # In the fixture's PT_DYNAMIC, the fourth entry is DT_NEEDED.
    struct.pack_into("<q", raw, 0x100 + 3 * 16, 0x7fffffff)
    replace_installed_elf(capture, bytes(raw))
    check_reject(capture, "ELF audit/filter dependency")


def test_explicit_unreviewed_elf_interpreter_is_forbidden(capture):
    raw = bytearray(base.make_elf(soname="libdemo.so", needed=("libzog.so.1",)))
    struct.pack_into("<I", raw, 120, 3)  # second program header: PT_INTERP
    replace_installed_elf(capture, bytes(raw))
    check_reject(capture, "PT_INTERP")


def test_nested_capture_root_is_not_independent(capture):
    nested = capture["roots"]["build"] / "compiler-root"
    nested.mkdir()
    capture["envelope"]["roots"]["software"] = str(nested)
    check_reject(capture, "overlapping native capture roots")


def test_link_command_forgery_cannot_set_native_acceptance(capture):
    capture["envelope"]["native_accepted"] = True
    check_reject(capture, "assert authorization")

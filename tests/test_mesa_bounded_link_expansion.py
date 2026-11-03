"""Bounded ar member and hashed linker response-file source checks.

All fixtures are synthetic untrusted observations. No native authority is issued.
"""
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "mesa_link_test_fixture", HERE / "test_mesa_native_evidence.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


@pytest.fixture
def capture(tmp_path):
    return base.fixture(tmp_path)


def ar_bytes(members):
    """Create a minimal classic ar archive containing actual object bytes."""
    result = bytearray(b"!<arch>\n")
    for name, contents in members:
        fields = ((name + "/", 16), ("0", 12), ("0", 6), ("0", 6),
                  ("100644", 8), (str(len(contents)), 10))
        header = "".join(f"{value:<{width}}" for value, width in fields).encode()
        assert len(header) == 58 and len(name) <= 15
        result.extend(header + bytes((96, 10)) + contents)
        if len(contents) & 1:
            result.extend(b"\n")
    return bytes(result)


def with_archive(capture):
    roots = capture["roots"]
    link = capture["sidecars"]["link_commands"][0]
    obj = (roots["build"] / "obj/demo.o").read_bytes()
    data = ar_bytes([("demo.o", obj)])
    ash = base.record(roots["build"], "lib/libobjects.a", data)
    link["inputs"] = []
    link["archives"] = [{
        "path": "lib/libobjects.a", "sha256": ash,
        "members": [{"name": "demo.o", "sha256": base.sha(obj),
                     "object": "obj/demo.o", "object_sha256": base.sha(obj),
                     "selected": True}],
    }]
    link["response_files"] = []
    link["arguments"] = [str(roots["software"] / "bin/cc"),
                         "-shared", str(roots["build"] / "lib/libobjects.a"),
                         "-o", str(roots["build"] / "lib/libdemo.so")]
    return link


def with_response(capture, link):
    raw = link["arguments"]
    response_args = raw[1:]
    content = " ".join(response_args).encode()
    sha = base.record(capture["roots"]["build"], "rsp/link.rsp", content)
    link["arguments"] = [raw[0], "@rsp/link.rsp"]
    link["response_files"] = [{
        "path": "rsp/link.rsp", "sha256": sha,
        "arguments": response_args,
    }]
    return link


def check(capture):
    capture["save"]()
    return base.module().verify(capture["root"], capture["drafts"])


def reject(capture, message):
    verifier = base.module()
    capture["save"]()
    with pytest.raises(verifier.EvidenceError, match=message):
        verifier.verify(capture["root"], capture["drafts"])


def test_selected_static_archive_members_and_response_file_positive(capture):
    with_response(capture, with_archive(capture))
    result = check(capture)
    assert result["status"] == "evidence-consistent-not-native-accepted"
    assert (result["native_accepted"], result["redistribution_authorized"],
            result["source_archives_independently_accepted"]) == (False, False, False)


def test_direct_archive_without_response_positive(capture):
    with_archive(capture)
    assert check(capture)["compile_units"] == 1


def test_existing_direct_object_link_without_expansions(capture):
    assert check(capture)["native_accepted"] is False


def test_unreported_archive_member_rejected_even_with_rehashed_archive(capture):
    link = with_archive(capture)
    raw = ar_bytes([("demo.o", (capture["roots"]["build"] / "obj/demo.o").read_bytes()),
                    ("hidden.o", b"hidden unreviewed object")])
    link["archives"][0]["sha256"] = base.record(
        capture["roots"]["build"], "lib/libobjects.a", raw)
    reject(capture, "incomplete archive member inventory")


def test_archive_member_bytes_must_match_source_derived_object(capture):
    link = with_archive(capture)
    altered = ar_bytes([("demo.o", b"malicious code")])
    link["archives"][0]["sha256"] = base.record(
        capture["roots"]["build"], "lib/libobjects.a", altered)
    reject(capture, "archive member lacks source-object provenance|static archive contents")


@pytest.mark.parametrize("bad", [
    "missing-archive-record", "wrong-member-hash", "unknown-object",
    "unselected-only", "thin-archive", "duplicate-archive-member",
    "unused-archive-record",
])
def test_bad_archive_provenance_rejected(capture, bad):
    link = with_archive(capture)
    archive = link["archives"][0]
    if bad == "missing-archive-record":
        link["archives"].clear()
    elif bad == "wrong-member-hash":
        archive["members"][0]["sha256"] = "0" * 64
    elif bad == "unknown-object":
        archive["members"][0]["object"] = "rsp/unknown.o"
    elif bad == "unselected-only":
        archive["members"][0]["selected"] = False
    elif bad == "thin-archive":
        archive["sha256"] = base.record(
            capture["roots"]["build"], "lib/libobjects.a", b"!<thin>\n")
    elif bad == "duplicate-archive-member":
        raw = ar_bytes([("demo.o", b"synthetic object"),
                        ("demo.o", b"synthetic object")])
        archive["sha256"] = base.record(
            capture["roots"]["build"], "lib/libobjects.a", raw)
        archive["members"].append(dict(archive["members"][0]))
    elif bad == "unused-archive-record":
        link["arguments"].remove(str(capture["roots"]["build"] / "lib/libobjects.a"))
    reject(capture, "archive|source-object|missing or cyclic captured path|link has no source-derived input|invalid linker command")


@pytest.mark.parametrize("bad", [
    "tampered-file", "forged-expanded-args", "missing-record", "unused-record",
    "nested-response", "absolute-host-response", "duplicate-reference",
])
def test_response_file_capture_rejected_when_tampered(capture, bad):
    link = with_response(capture, with_archive(capture))
    rsp = link["response_files"][0]
    if bad == "tampered-file":
        path = capture["roots"]["build"] / rsp["path"]
        path.write_bytes(path.read_bytes() + b" -lhost")
    elif bad == "forged-expanded-args":
        rsp["arguments"].append("-lhost")
    elif bad == "missing-record":
        link["response_files"].clear()
    elif bad == "unused-record":
        link["arguments"] = [link["arguments"][0]] + rsp["arguments"]
    elif bad == "nested-response":
        rsp["sha256"] = base.record(capture["roots"]["build"],
                                    rsp["path"], b"@rsp/nested.rsp")
        rsp["arguments"] = ["@rsp/nested.rsp"]
    elif bad == "absolute-host-response":
        link["arguments"][1] = "@/etc/passwd"
    elif bad == "duplicate-reference":
        link["arguments"].append("@rsp/link.rsp")
    reject(capture, "response|unsupported opaque|Host linker|content digest mismatch")


def test_forged_missing_implicit_header_is_still_consistency_only(capture):
    """A submitter can forge both depfile and inputs. Native witness required."""
    implicit = capture["sidecars"]["implicit_inputs"][0]
    path = capture["roots"]["build"] / implicit["depfile"]
    source = capture["roots"]["source"] / "src/demo.c"
    obj = capture["roots"]["build"] / "obj/demo.o"
    new_bytes = f"{obj}: {source}\n".encode()
    implicit["depfile_sha256"] = base.record(
        capture["roots"]["build"], implicit["depfile"], new_bytes)
    implicit["inputs"] = implicit["inputs"][:1]
    result = check(capture)
    assert result["status"] == "evidence-consistent-not-native-accepted"
    assert result["native_accepted"] is False
    assert result["source_archives_independently_accepted"] is False


def test_forged_linker_archive_selection_is_not_native_proof(capture):
    link = with_response(capture, with_archive(capture))
    result = check(capture)
    # Consistent claims about selected archive members are NOT authenticated
    # linker trace evidence; the source verifier can never grant approval.
    assert result["native_accepted"] is False
    assert result["redistribution_authorized"] is False

"""Offline tests of pinned XCB archive inspection behavior."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("xcb_inspector", ROOT / "tools/inspect_xcb_cursor_archives.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic(name):
    root = name + "-" + mod.SOURCES[name]["version"] + "/"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:xz") as tar:
        for filename, data in (("COPYING", b"synthetic notice"), ("configure.ac", b"synthetic configure")):
            item = tarfile.TarInfo(root + filename)
            item.size = len(data)
            tar.addfile(item, io.BytesIO(data))
    return buffer.getvalue()


def test_archives_are_exact_upstream_sha256_pinned():
    assert all(len(v["sha256"]) == 64 and v["url"].startswith(
        "https://xorg.freedesktop.org/archive/individual/lib/") for v in mod.SOURCES.values())


def test_original_notice_and_configure_are_hashed_without_execution(monkeypatch):
    name = "xcb-util-cursor"
    archive = synthetic(name)
    monkeypatch.setitem(mod.SOURCES[name], "sha256", hashlib.sha256(archive).hexdigest())
    record = mod.inspect(name, archive)
    assert record["members"]["COPYING"] == hashlib.sha256(b"synthetic notice").hexdigest()
    assert record["status"].endswith("not-redistribution-approved")


def test_wrong_original_archive_fails_closed():
    try:
        mod.inspect("xcb-util-renderutil", b"not an archive")
    except ValueError as exc:
        assert "archive digest mismatch" in str(exc)
    else:
        assert False, "wrong original archive was accepted"

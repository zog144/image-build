"""No network required: author-to-mirror failover must never change xterm identity."""
import importlib.util
from pathlib import Path
import urllib.error
import io
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("xterm_inspector", ROOT / "tools/inspect_xterm_archive.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Response(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.close()


def test_transport_403_tries_explicit_mirror_and_rejects_wrong_source():
    seen = []
    def opener(req, timeout):
        seen.append(req.full_url)
        if req.full_url == mod.UPSTREAM:
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
        return Response(b"not the pinned original")
    with pytest.raises(ValueError, match="identity mismatch.*refusing fallback"):
        mod.fetch_archive(opener)
    assert seen == [mod.UPSTREAM, mod.FALLBACK]


def test_wrong_primary_bytes_cannot_be_replaced_by_mirror():
    seen = []
    def opener(req, timeout):
        seen.append(req.full_url)
        return Response(b"wrong upstream bytes")
    with pytest.raises(ValueError, match="identity mismatch"):
        mod.fetch_archive(opener)
    assert seen == [mod.UPSTREAM]


def test_both_transports_fail_with_explicit_diagnostic():
    def opener(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
    with pytest.raises(RuntimeError, match="author URL and.*upstream mirror; source identity and notice checks were NOT run"):
        mod.fetch_archive(opener)


def test_oversized_response_denied_without_fallback():
    seen = []
    def opener(req, timeout):
        seen.append(req.full_url)
        return Response(b"x" * (mod.MAX_BYTES + 1))
    with pytest.raises(ValueError, match="exceeds inspection bound"):
        mod.fetch_archive(opener)
    assert seen == [mod.UPSTREAM]

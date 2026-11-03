#!/usr/bin/env python3
"""Hash original xterm 412 archive notice and configure members. No build."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 4 * 1024 * 1024


def inspect(archive):
    spec = ast.literal_eval((ROOT / "project/package/xterm/sources.py").read_text())[0]
    source_sha = hashlib.sha256(archive).hexdigest()
    if source_sha != spec["sha256"]:
        raise ValueError("xterm 412 original source archive mismatch")
    members = {}
    configure_bytes = None
    makefile_bytes = None
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for item in tar.getmembers():
            if item.name.startswith("/") or ".." in item.name.split("/"):
                raise ValueError("unsafe xterm member pathname")
            stripped = item.name.removeprefix("xterm-412/")
            if stripped in ("COPYING", "configure", "MANIFEST", "Makefile.in"):
                if not item.isfile() or item.size > 2 * 1024 * 1024:
                    raise ValueError("unsafe original xterm metadata member")
                opened = tar.extractfile(item)
                if opened is None:
                    raise ValueError("unreadable original member")
                content = opened.read()
                members[stripped] = hashlib.sha256(content).hexdigest()
                if stripped == "configure":
                    configure_bytes = content
                elif stripped == "Makefile.in":
                    makefile_bytes = content
    if "COPYING" not in members or configure_bytes is None or makefile_bytes is None:
        raise ValueError("missing original xterm notice or build metadata")
    # These are literal options present in the original immutable configure,
    # not an assertion that the source will build on a native Host.
    needed = (b"--with-app-defaults", b"--disable-setuid",
              b"--disable-setgid", b"--enable-256-color")
    for option in needed:
        if option not in configure_bytes:
            raise ValueError("unsupported selected xterm option: " + option.decode())
    if b"install-ti" not in makefile_bytes:
        raise ValueError("xterm terminfo install target unconfirmed")
    return {"package": "xterm", "version": "412", "original_source_sha256": source_sha,
            "archive_members": members,
            "selected_build_options_confirmed": [x.decode() for x in needed],
            "terminfo_install_target_seen": True,
            "status": "source-observed-not-canonical-or-redistribution-approved"}


# The author-published archive is the authoritative *identity*.  The alternate
# is an independently listed xterm upstream mirror (Homebrew and BLFS, 2026-11-02).
# A fallback is a transport recovery, never a release or checksum substitution.
UPSTREAM = "https://invisible-island.net/archives/xterm/xterm-412.tgz"
FALLBACK = "https://invisible-mirror.net/archives/xterm/xterm-412.tgz"


def fetch_archive(opener=None):
    opener = opener or urllib.request.urlopen
    spec = ast.literal_eval((ROOT / "project/package/xterm/sources.py").read_text())[0]
    if spec["url"] != UPSTREAM or spec["sha256"] != (
        "b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6"
    ):
        raise ValueError("xterm 412 canonical release identity changed")
    failures = []
    for url in (UPSTREAM, FALLBACK):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Zog-source-evidence/1"})
            with opener(req, timeout=90) as response:
                payload = response.read(MAX_BYTES + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            # No fallback on identity or archive validation failures.
            failures.append(f"{url}: {type(exc).__name__}: {getattr(exc, 'code', str(exc))}")
            continue
        if len(payload) > MAX_BYTES:
            raise ValueError(f"xterm 412 archive exceeds inspection bound at {url}")
        actual = hashlib.sha256(payload).hexdigest()
        if actual != spec["sha256"]:
            raise ValueError(
                f"xterm 412 source identity mismatch at {url}: expected {spec['sha256']}, got {actual}; "
                "refusing fallback or release substitution"
            )
        return payload, url
    raise RuntimeError(
        "xterm 412 original archive acquisition failed at the author URL and "
        "the independently listed upstream mirror; source identity and notice "
        "checks were NOT run. Transport failures: " + "; ".join(failures)
    )


if __name__ == "__main__":
    data, acquisition_url = fetch_archive()
    result = inspect(data)
    result["acquisition_url"] = acquisition_url
    result["canonical_release_url"] = UPSTREAM
    print(json.dumps(result, sort_keys=True))

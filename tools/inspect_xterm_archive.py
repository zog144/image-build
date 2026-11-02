#!/usr/bin/env python3
"""Hash original xterm 412 archive notice and configure members. No build."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 4 * 1024 * 1024


def inspect(archive):
    spec = ast.literal_eval((ROOT / "project/package/xterm/sources.py").read_text())[0]
    source_sha = hashlib.sha256(archive).hexdigest()
    if source_sha != spec["sha256"]:
        raise ValueError("xterm 412 original source archive mismatch")
    members = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for item in tar.getmembers():
            if item.name.startswith("/") or ".." in item.name.split("/"):
                raise ValueError("unsafe xterm member pathname")
            stripped = item.name.removeprefix("xterm-412/")
            if stripped in ("COPYING", "configure", "MANIFEST"):
                if not item.isfile() or item.size > 2 * 1024 * 1024:
                    raise ValueError("unsafe original xterm metadata member")
                opened = tar.extractfile(item)
                if opened is None:
                    raise ValueError("unreadable original member")
                members[stripped] = hashlib.sha256(opened.read()).hexdigest()
    if "COPYING" not in members or "configure" not in members:
        raise ValueError("missing original xterm notice or configure evidence")
    return {"package": "xterm", "version": "412", "original_source_sha256": source_sha,
            "archive_members": members,
            "status": "source-observed-not-canonical-or-redistribution-approved"}


if __name__ == "__main__":
    url = "https://invisible-island.net/archives/xterm/xterm-412.tgz"
    request = urllib.request.Request(url, headers={"User-Agent": "Zog-source-evidence/1"})
    with urllib.request.urlopen(request, timeout=90) as stream:
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("xterm archive exceeds inspection bound")
    print(json.dumps(inspect(payload), sort_keys=True))

"""Protect independently checked xterm 412 source notice pins without admitting build."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "project/package/xterm"


def test_xterm_412_source_notice_identity():
    s = ast.literal_eval((ROOT / "sources.py").read_text())[0]
    upstream = ast.literal_eval((ROOT / "upstream.py").read_text())
    rights = ast.literal_eval((ROOT / "license.py").read_text())
    assert s["sha256"] == upstream["sha256"]
    assert rights["source"]["sha256"] == s["sha256"]
    assert rights["evidence"][0]["sha256"] == (
        "f272fa007de2cffdb22b4df09e9a3aaec3555d5a6913229b70006ee137ab22b5")
    assert all(x["source_sha256"] == s["sha256"] for x in rights["evidence"])
    assert rights["components"][0]["status"] == "unresolved"
    assert ast.literal_eval((ROOT / "package.py").read_text())["status"] == "catalogue-only"

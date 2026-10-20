#!/usr/bin/env python3
"""Fail-closed static preflight of the exact proposed public image-build source tree.

Source inspection only. This is NOT secret clearance, copyright approval,
native-test acceptance or proof that binary/compiled redistribution is permitted.
Run against the complete candidate after applying all reviewed overlays.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

PROHIBITED_PATHS = {
    "AGENTS.md", "COPYRIGHT", "version-share-handoff.json",
    "private-stage-manifest.json",
    "public-first-party-pins.json",
}
PATTERNS = {
    "deployment_instance_literal": re.compile(rb"\bi-[0-9a-f]{17}\b"),
    "private_repository_url": re.compile(
        rb"(?:github\.com|api\.github\.com)/"
        rb"(?:repos/)?zog144/(?:know-file|[\w-]+-old)\b", re.I
    ),
    "historical_private_grant": re.compile(
        rb"LicenseRef-Zog-" rb"Private|private development" rb" material|"
        rb"no public redistribution" rb" grant|Private :: Do Not" rb" Upload", re.I
    ),
    "private_cross_repo_secret": re.compile(
        rb"ZOG_CROSS_REPO_" rb"READ_TOKEN|secrets\.[A-Za-z_][A-Za-z0-9_]*"
    ),
    "known_sensitive_literals": re.compile(
        rb"-----BEGIN\s+[A-Z ]*PRIVATE KEY-----|"
        rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|"
        rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b|github_pat_[A-Za-z0-9_]{30,}"
    ),
    "obvious_private_network": re.compile(
        rb"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|"
        rb"192\.168\.(?:\d{1,3}\.)\d{1,3}|"
        rb"172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b|"
        rb"\b[\w.-]+\.(?:internal|lan|local)\b", re.I
    ),
    "deprecated_double_namespace": re.compile(rb"\bzog\.zog\.image_build\b"),
    "legacy_direct_companion_import": re.compile(
        rb"(?m)^\s*(?:from|import)\s+"
        rb"(?:box_control|root_control|build_record|build_trace)\b"
    ),
}
REQUIRED_ROOT = [
    "LICENSE",
    "LICENSES/BSD-3-Clause.txt",
    "LICENSES/GPL-3.0-only.txt",
    "THIRD-PARTY-NOTICES.md",
    "src/zog/image_build/__init__.py",
    "pyproject.toml",
    "zog-component.json",
]
LICENSE_EXP = b"BSD-3-Clause OR GPL-3.0-only"
APPROVED_MONTHLY_PINS = {
    "2026-10-01": "d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36",
}


def monthly_pin_issues(root: Path, paths):
    """Validate only producer-reviewed public monthly locks; no moving/external pin."""
    issues = []
    current_name = "project/pins/current.py"
    if current_name not in paths:
        return [{"path": current_name, "finding": "required_monthly_pin_selector_missing"}]
    current = root / current_name
    try:
        selected = ast.literal_eval(current.read_text("utf-8"))
    except (OSError, ValueError, SyntaxError, UnicodeError):
        return [{"path": current_name, "finding": "invalid_monthly_pin_selector"}]
    if (
        not isinstance(selected, dict)
        or set(selected) != {"date"}
        or selected["date"] not in APPROVED_MONTHLY_PINS
    ):
        return [{"path": current_name, "finding": "unreviewed_monthly_pin_selection"}]
    date = selected["date"]
    pin_name = f"project/pins/{date}/commit-pin.py"
    pin = root / pin_name
    if pin_name not in paths or pin.is_symlink() or not pin.is_file():
        return [{"path": pin_name, "finding": "reviewed_monthly_pin_missing"}]
    digest = hashlib.sha256(pin.read_bytes()).hexdigest()
    if digest != APPROVED_MONTHLY_PINS[date]:
        issues.append({"path": pin_name, "finding": "reviewed_monthly_pin_digest_mismatch"})
    return issues

def included_paths(root: Path):
    # For a Git working tree, prefer the *indexed* tracked objects and reject
    # any untracked source payloads before allowing a candidate export.
    if (root / ".git").exists():
        tracked = subprocess.check_output(["git", "-C", str(root),
                                           "ls-files", "-z"])
        paths = [p.decode("utf-8", "surrogateescape") for p in tracked.split(b"\0") if p]
        extras = [str(p.relative_to(root)) for p in root.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(root).parts
                  and str(p.relative_to(root)) not in paths]
        if extras:
            raise ValueError("Untracked files in export tree: " + ", ".join(extras[:10]))
        return paths
    return [str(p.relative_to(root)) for p in root.rglob("*")
            if p.is_file() or p.is_symlink()]

def scan(root: Path):
    paths = included_paths(root)
    issues = []
    for name in sorted(set(paths)):
        p = root / name
        parts = Path(name).parts
        if name in PROHIBITED_PATHS or (parts and parts[0] in ("handoffs", "review", "_deps", ".version-share")):
            issues.append({"path": name, "finding": "private_or_unreviewed_path"})
            continue
        if p.is_symlink():
            issues.append({"path": name, "finding": "unreviewed_symlink"})
            continue
        if not p.is_file():
            issues.append({"path": name, "finding": "path_not_regular"})
            continue
        if p.suffix.lower() in {'.tar', '.gz', '.xz', '.bz2', '.zip', '.whl', '.egg', '.pyc', '.so', '.a', '.o'}:
            issues.append({'path': name, 'finding': 'generated_or_binary_payload'})
        content = p.read_bytes()
        for category, pattern in PATTERNS.items():
            if pattern.search(content):
                issues.append({"path": name, "finding": category})
        if name.endswith((".py", ".sh", ".md", ".yml", ".yaml", ".toml", ".json", ".txt")):
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                issues.append({"path": name, "finding": "unreviewed_non_utf8_text"})
    for name in REQUIRED_ROOT:
        if name not in paths:
            issues.append({"path": name, "finding": "required_file_missing"})
    license_path = root / "LICENSE"
    if license_path.is_file() and LICENSE_EXP not in license_path.read_bytes():
        issues.append({"path": "LICENSE", "finding": "public_dual_grant_missing"})
    project_metadata = root / "pyproject.toml"
    if project_metadata.is_file() and LICENSE_EXP not in project_metadata.read_bytes():
        issues.append({"path": "pyproject.toml", "finding": "public_spdx_missing"})
    component = root / "zog-component.json"
    if component.is_file():
        try:
            import json
            component_obj = json.loads(component.read_text("utf-8"))
            expected_notices = ["LICENSE", "LICENSES/BSD-3-Clause.txt",
                                "LICENSES/GPL-3.0-only.txt", "THIRD-PARTY-NOTICES.md"]
            if (component_obj.get("schema") != 2
                or component_obj.get("program") != "image-build"
                or component_obj.get("license_notice_paths") != expected_notices):
                issues.append({"path": "zog-component.json",
                               "finding": "incorrect_public_component_license_manifest"})
        except (ValueError, UnicodeError, TypeError):
            issues.append({"path": "zog-component.json",
                           "finding": "invalid_component_manifest"})
    if (root / "src/zog/__init__.py").exists():
        issues.append({"path": "src/zog/__init__.py", "finding": "top_level_zog_owned_by_release_build"})
    issues.extend(monthly_pin_issues(root, paths))
    return {"schema": "zog-image-build-public-source-preflight-v1",
            "file_count": len(paths), "issue_count": len(issues),
            "issues": issues, "source_export_preflight": "PASS" if not issues else "FAIL",
            "compiled_artifact_redistribution": "NOT_ASSESSED",
            "semantic_review": "NOT_ASSESSED",
            "external_secret_detection": "NOT_ASSESSED"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = scan(args.root.resolve())
    if args.report is not None:
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"file_count": result["file_count"],
                      "issue_count": result["issue_count"],
                      "preflight": result["source_export_preflight"],
                      "issue_paths": [x["path"] for x in result["issues"]][:30]}, sort_keys=True))
    return 0 if result["issue_count"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

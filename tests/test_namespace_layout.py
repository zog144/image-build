import importlib.util
from pathlib import Path
import re

import zog.image_build


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_namespace_and_version():
    assert zog.image_build.__version__ == "0.2.0.dev5"
    assert importlib.util.find_spec("image_build") is None


def test_source_tree_is_release_build_assemblable():
    component = ROOT / "src" / "zog" / "image_build"
    assert (component / "__init__.py").is_file()
    assert (component / "application_software.py").is_file()
    assert not (ROOT / "src" / "zog" / "__init__.py").exists()
    assert not (ROOT / "image_build").exists()


def test_legacy_component_imports_do_not_return_in_maintained_code():
    patterns = (
        re.compile(r"\bfrom\s+image_build\b"),
        re.compile(r"\bimport\s+image_build\b"),
        re.compile(r"\bpython(?:3(?:\.\d+)?)?\s+-m\s+image_build\b"),
        re.compile(r"['\"]image_build\.[A-Za-z_]"),
    )
    roots = [
        ROOT / "src",
        ROOT / "tests",
        ROOT / "acceptance",
        ROOT / "examples",
        ROOT / "jobs",
    ]
    files = [ROOT / "README.md", ROOT / "docs" / "image-build" / "CONTROLLER-INTEGRATION.md"]
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    offenders = []
    for path in files:
        if path.suffix not in {".py", ".md", ".sh", ".toml", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in patterns):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_component_uses_migrated_sibling_namespaces():
    patterns = (
        re.compile(r"\bfrom\s+(?:build_record|box_control|host_identify|root_control)\b"),
        re.compile(r"\bimport\s+(?:build_record|box_control|host_identify|root_control)\b"),
    )
    offenders = []
    for path in (ROOT / "src" / "zog" / "image_build").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in patterns):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []

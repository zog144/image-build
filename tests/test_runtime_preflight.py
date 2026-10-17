import json
import os
from pathlib import Path
import subprocess
import shutil
import sys

from zog.image_build.runtime_requirements import (
    CONTRACT,
    PREFLIGHT_CONTRACT,
    requirements_for,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _run(*arguments, pythonpath=None):
    env = dict(os.environ)
    python = str(Path(sys.executable).resolve())
    entries = [str(REPOSITORY / "src")]
    if pythonpath:
        entries.extend(str(path) for path in pythonpath)
    if env.get("PYTHONPATH"):
        entries.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(entries)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            python,
            "-B",
            "-m",
            "zog.image_build.runtime_preflight",
            "--repository-root",
            str(REPOSITORY),
            "--python-executable",
            python,
            *arguments,
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return result, json.loads(result.stdout)


def _fake_build_record(root):
    package = root / "src/zog/build_record"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        """
__version__ = "0.8.2"

class Store:
    def __init__(self, *args, **kwargs):
        pass

def verify_artifacts(*args, **kwargs):
    return {}

def make_record(kind, data, gaps=None):
    return {"schema_version": 1, "kind": kind, "data": data, "gaps": gaps or []}
"""
    )
    (package / "model.py").write_text(
        """
ENVIRONMENT = {"PATH", "LANG", "LC_ALL"}

def digest(value):
    assert isinstance(value, str) and value.startswith("sha256:")
    return value

def artifact_references(record):
    return record["data"]["archives"] + [
        {"name": "commit-pin.py", "digest": record["data"]["pin"]["digest"], "size": None}
    ]
"""
    )


def test_runtime_requirements_are_operation_aware():
    external = requirements_for(
        "pipeline.inspect",
        provenance=True,
        external_observed_state=True,
    )
    assert external["contract"] == CONTRACT
    assert [item["component"] for item in external["components"]] == [
        "build-record"
    ]
    build_record = external["components"][0]
    assert build_record["validated_revision"] == (
        "a866c9c4b0dd385045f00ce2de7d809f5b67c104"
    )
    assert build_record["version"] == "0.8.2"
    assert build_record["source_subdir"] == "src"
    assert external["external"] == []

    controller = requirements_for(
        "pipeline.submit",
        provenance=True,
        controller=True,
    )
    assert [item["component"] for item in controller["components"]] == [
        "build-record",
        "box-control",
    ]
    box_control = controller["components"][1]
    assert box_control["validated_revision"] == (
        "644170fc441863307092f329bf7e23cb64eb33e2"
    )
    assert box_control["version"] == "0.1.0"
    assert box_control["source_subdir"] == "box-control/src"
    assert box_control["required_api"] == [
        "BoxControl",
        "Project",
        "runtime.root_control.RootControlSystemdTransport",
        "build_jobs.BuildJobs",
    ]
    assert controller["external"] == [
        {
            "distribution": "dbus-next",
            "python_module": "dbus_next",
            "version": "0.2.3",
        }
    ]


def test_missing_build_record_fails_before_remote_cli_state_exists(tmp_path):
    result, report = _run(
        "--operation",
        "pipeline.inspect",
        "--provenance",
        "--external-observed-state",
    )
    assert result.returncode == 3
    assert report["contract"] == PREFLIGHT_CONTRACT
    assert report["ready"] is False
    assert report["mutation"] is False
    assert report["checks"] == []
    assert report["failures"] == [
        {
            "kind": "component-root",
            "component": "build-record",
            "reason": "required component root was not supplied",
        }
    ]
    assert list(tmp_path.iterdir()) == []


def test_build_record_api_smoke_succeeds_from_supplied_exact_source_root(tmp_path):
    companion = tmp_path / "build-record"
    _fake_build_record(companion)
    result, report = _run(
        "--operation",
        "pipeline.inspect",
        "--provenance",
        "--external-observed-state",
        "--component-root",
        "build-record=" + str(companion),
        pythonpath=[companion / "src"],
    )
    assert result.returncode == 0, result.stderr
    assert report["ready"] is True
    assert report["mutation"] is False
    assert report["failures"] == []
    assert report["requirements"]["components"][0]["validated_revision"] == (
        "a866c9c4b0dd385045f00ce2de7d809f5b67c104"
    )
    check = report["checks"][0]
    assert check["component"] == "build-record"
    assert check["version"] == "0.8.2"
    assert check["api_evidence"]["record_kind"] == "source-selection"
    assert check["api_evidence"]["artifact_reference_count"] == 2
    assert not list(companion.rglob("__pycache__"))


def test_component_import_outside_supplied_root_fails_closed(tmp_path):
    companion = tmp_path / "build-record"
    wrong = tmp_path / "wrong-build-record"
    _fake_build_record(companion)
    wrong.mkdir()
    result, report = _run(
        "--operation",
        "pipeline.inspect",
        "--provenance",
        "--external-observed-state",
        "--component-root",
        "build-record=" + str(wrong),
        pythonpath=[companion / "src"],
    )
    assert result.returncode == 3
    assert report["ready"] is False
    assert report["failures"][0]["component"] == "build-record"


def test_invalid_external_observed_operation_is_bounded_failure():
    result, report = _run(
        "--operation",
        "pipeline.submit",
        "--external-observed-state",
    )
    assert result.returncode == 3
    assert report["ready"] is False
    assert "external observed state permits only pipeline.inspect" in (
        report["failures"][0]["reason"]
    )


def test_real_remote_cli_provenance_smoke_uses_disposable_state(tmp_path):
    companion = tmp_path / "build-record"
    _fake_build_record(companion)
    checkout = tmp_path / "image-build-public-smoke"
    shutil.copytree(REPOSITORY / "src", checkout / "src")
    (checkout / "project/package").mkdir(parents=True)
    pin = checkout / "runtime-companion-pin.py"
    pin.write_text(
        "# Inactive source-publication smoke pin; not a historical monthly pin.\n"
        + repr({"schema": 1, "date": "2000-01-01", "packages": {}})
        + "\n"
    )
    digest = "sha256:" + __import__("hashlib").sha256(pin.read_bytes()).hexdigest()
    python = str(Path(sys.executable).resolve())
    env = dict(os.environ)
    env["PYTHONPATH"] = str(checkout / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            python,
            "-B",
            "-m",
            "zog.image_build.runtime_companion_smoke",
            "--repository-root",
            str(checkout),
            "--python-executable",
            python,
            "--source-repository",
            "zog144/image-build",
            "--source-revision",
            "a" * 40,
            "--build-record-root",
            str(companion),
            "--provenance-pin",
            str(pin),
            "--expected-pin-digest",
            digest,
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    report = json.loads(result.stdout)
    assert result.returncode == 0, result.stderr
    assert report["ready"] is True
    assert report["preflight"]["ready"] is True
    assert report["remote"]["status"] == "completed"
    assert report["remote"]["operation_type"] == "capabilities.inspect"
    assert report["pipeline_created"] is False
    assert report["temporary_state"] == "discarded"
    assert not list(companion.rglob("__pycache__"))

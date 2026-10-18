"""Disposable exact-companion smoke for the real remote CLI provenance path."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .runtime_requirements import SMOKE_CONTRACT


def _real(path, label):
    value = Path(path)
    if not value.is_absolute() or value.is_symlink() or not value.is_dir():
        raise ValueError(label + " must be an absolute real directory")
    return value.resolve(strict=True)


def _run_json(argv, env):
    result = subprocess.run(
        argv, text=True, capture_output=True, env=env, check=False
    )
    try:
        payload = json.loads(result.stdout)
    except Exception as error:
        raise RuntimeError(
            "runtime smoke child did not return bounded JSON"
        ) from error
    return result.returncode, payload


def smoke(
    *,
    repository_root,
    python_executable,
    source_repository,
    source_revision,
    build_record_root,
    provenance_pin,
    expected_pin_digest,
):
    repository_root = _real(repository_root, "repository root")
    build_record_root = _real(build_record_root, "build-record root")
    python = Path(python_executable)
    if not python.is_absolute() or python.is_symlink() or not python.is_file():
        raise ValueError("python executable must be an absolute real file")
    pin = Path(provenance_pin).resolve(strict=True)
    pin.relative_to(repository_root)
    observed = "sha256:" + hashlib.sha256(pin.read_bytes()).hexdigest()
    if observed != expected_pin_digest:
        raise ValueError("provenance pin digest differs from smoke binding")

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(repository_root / "src"),
            str(build_record_root / "src"),
        ]
    )

    preflight_argv = [
        str(python),
        "-B",
        "-m",
        "zog.image_build.runtime_preflight",
        "--repository-root",
        str(repository_root),
        "--python-executable",
        str(python),
        "--operation",
        "capabilities.inspect",
        "--provenance",
        "--component-root",
        "build-record=" + str(build_record_root),
    ]
    preflight_code, preflight = _run_json(preflight_argv, env)
    if preflight_code != 0 or not preflight.get("ready"):
        return {
            "contract": SMOKE_CONTRACT,
            "ready": False,
            "preflight": preflight,
            "remote": None,
            "pipeline_created": False,
        }

    with tempfile.TemporaryDirectory(
        prefix="image-build-runtime-companion-smoke-"
    ) as temporary:
        root = Path(temporary)
        request = root / "request.json"
        request.write_text(
            json.dumps(
                {
                    "schema": "image-build-remote-operation-v1",
                    "operation_id": "runtime-companion-smoke",
                    "operation": "capabilities.inspect",
                    "source": {
                        "repository": source_repository,
                        "revision": source_revision,
                    },
                    "arguments": {},
                },
                sort_keys=True,
            )
        )
        remote_argv = [
            str(python),
            "-B",
            "-m",
            "zog.image_build.remote_operations",
            "--repository-root",
            str(repository_root),
            "--source-repository",
            source_repository,
            "--source-revision",
            source_revision,
            "--package-dir",
            str(repository_root / "project/package"),
            "--state-dir",
            str(root / "state"),
            "--provenance-host-id",
            "runtime-companion-smoke",
            "--provenance-project-id",
            "runtime-companion-smoke",
            "--provenance-pin",
            str(pin),
            "--expected-pin-digest",
            expected_pin_digest,
            str(request),
        ]
        remote_code, remote = _run_json(remote_argv, env)
        ready = (
            remote_code == 0
            and remote.get("status") == "completed"
            and remote.get("operation_type") == "capabilities.inspect"
            and remote.get("pipeline_id") is None
        )
        pipeline_root = root / "state/image-build/pipelines"
        pipeline_created = pipeline_root.exists() and any(
            pipeline_root.iterdir()
        )
        if pipeline_created:
            ready = False

    return {
        "contract": SMOKE_CONTRACT,
        "ready": ready,
        "preflight": {
            "contract": preflight.get("contract"),
            "ready": preflight.get("ready"),
        },
        "remote": {
            "schema": remote.get("schema"),
            "status": remote.get("status"),
            "operation_type": remote.get("operation_type"),
            "source_revision": remote.get("source_revision"),
        },
        "pipeline_created": pipeline_created,
        "temporary_state": "discarded",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--build-record-root", required=True)
    parser.add_argument("--provenance-pin", required=True)
    parser.add_argument("--expected-pin-digest", required=True)
    args = parser.parse_args(argv)
    try:
        report = smoke(
            repository_root=args.repository_root,
            python_executable=args.python_executable,
            source_repository=args.source_repository,
            source_revision=args.source_revision,
            build_record_root=args.build_record_root,
            provenance_pin=args.provenance_pin,
            expected_pin_digest=args.expected_pin_digest,
        )
    except Exception as error:
        report = {
            "contract": SMOKE_CONTRACT,
            "ready": False,
            "failure": str(error),
            "pipeline_created": False,
        }
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("ready") else 4


if __name__ == "__main__":
    raise SystemExit(main())

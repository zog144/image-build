"""Read-only pre-provenance runtime readiness check for remote image-build.

This entrypoint is deliberately safe to execute before a gateway marks a prepared
dispatch as submitting.  It creates no image-build state, opens no controller, and
does not capture provenance artifacts.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

# Companion imports must not mutate staged source trees with __pycache__ files.
# The advertised CLI also requires Python -B so this applies to this module's own
# import, before its code begins executing.
sys.dont_write_bytecode = True

from .runtime_requirements import (
    PREFLIGHT_CONTRACT,
    requirements_for,
)


def _real_directory(path, label):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError(label + " must be absolute")
    if path.is_symlink() or not path.is_dir():
        raise ValueError(label + " must be a real directory")
    return path.resolve(strict=True)


def _parse_component_roots(values):
    result = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("component root must be NAME=/absolute/path")
        name, value = raw.split("=", 1)
        if not name or name in result:
            raise ValueError("duplicate or empty component root")
        result[name] = _real_directory(
            value, "component root " + name
        )
    return result


def _module_path(module):
    value = getattr(module, "__file__", None)
    if not isinstance(value, str):
        raise RuntimeError("module has no source path")
    return Path(value).resolve(strict=True)


def _inside(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _build_record_smoke(module):
    model = importlib.import_module("zog.build_record.model")
    required = {
        "make_record": getattr(module, "make_record", None),
        "Store": getattr(module, "Store", None),
        "verify_artifacts": getattr(module, "verify_artifacts", None),
        "model.digest": getattr(model, "digest", None),
        "model.artifact_references": getattr(
            model, "artifact_references", None
        ),
        "model.ENVIRONMENT": getattr(model, "ENVIRONMENT", None),
    }
    missing = [
        name for name, value in required.items()
        if value is None or (
            name != "model.ENVIRONMENT"
            and not callable(value)
            and name != "Store"
        )
    ]
    if missing:
        raise RuntimeError(
            "build-record API missing: " + ", ".join(sorted(missing))
        )

    digest = "sha256:" + "0" * 64
    pin = {
        "month": "2026-10-01",
        "repository": "zog144/image-build",
        "revision": "0" * 40,
        "path": "project/pins/2026-10-01/commit-pin.py",
        "digest": digest,
    }
    record = module.make_record(
        "source-selection",
        {
            "package": "runtime-preflight",
            "pin": pin,
            "upstream": [
                {"repository": "unknown", "revision": None}
            ],
            "archives": [
                {"name": "runtime-preflight", "digest": digest, "size": 0}
            ],
        },
        gaps=["read-only runtime preflight"],
    )
    model.digest(digest)
    references = model.artifact_references(record)
    if not isinstance(references, list) or not references:
        raise RuntimeError(
            "build-record provenance artifact API returned invalid evidence"
        )
    if not isinstance(model.ENVIRONMENT, (set, frozenset, tuple, list)):
        raise RuntimeError(
            "build-record ENVIRONMENT allowlist has unexpected type"
        )
    return {
        "record_kind": record["kind"],
        "artifact_reference_count": len(references),
    }


def _box_control_smoke(module):
    for name in ("BoxControl", "Project"):
        if not callable(getattr(module, name, None)):
            raise RuntimeError("box-control API missing: " + name)
    root_control = importlib.import_module(
        "zog.box_control.runtime.root_control"
    )
    build_jobs = importlib.import_module("zog.box_control.build_jobs")
    if not callable(
        getattr(root_control, "RootControlSystemdTransport", None)
    ):
        raise RuntimeError(
            "box-control API missing: RootControlSystemdTransport"
        )
    if not callable(getattr(build_jobs, "BuildJobs", None)):
        raise RuntimeError("box-control API missing: BuildJobs")
    return {
        "controller_transport": "RootControlSystemdTransport",
        "build_jobs": "BuildJobs",
    }


def inspect_runtime(
    *,
    repository_root,
    python_executable,
    operation,
    provenance=False,
    controller=False,
    external_observed_state=False,
    component_roots=(),
):
    if not sys.flags.dont_write_bytecode:
        raise ValueError(
            "runtime preflight must be invoked with Python -B"
        )
    repository_root = _real_directory(
        repository_root, "repository root"
    )
    executable = Path(python_executable)
    if (
        not executable.is_absolute()
        or executable.is_symlink()
        or not executable.is_file()
        or not os.access(executable, os.X_OK)
    ):
        raise ValueError("python executable must be an executable real file")
    if os.path.realpath(sys.executable) != os.path.realpath(str(executable)):
        raise ValueError("selected Python executable differs from running interpreter")
    if sys.version_info < (3, 11):
        raise ValueError("Python >=3.11 required")

    roots = (
        _parse_component_roots(component_roots)
        if not isinstance(component_roots, dict)
        else {
            name: _real_directory(path, "component root " + name)
            for name, path in component_roots.items()
        }
    )
    image_build_module = _module_path(
        importlib.import_module("zog.image_build.runtime_preflight")
    )
    expected_source = repository_root / "src"
    if not _inside(image_build_module, expected_source):
        raise ValueError("image-build runtime preflight module is outside repository source")

    requirements = requirements_for(
        operation,
        provenance=provenance,
        controller=controller,
        external_observed_state=external_observed_state,
    )
    checks = []
    failures = []

    for component in requirements["components"]:
        name = component["component"]
        root = roots.get(name)
        if root is None:
            failures.append(
                {
                    "kind": "component-root",
                    "component": name,
                    "reason": "required component root was not supplied",
                }
            )
            continue
        expected_source = root / component["source_subdir"]
        if not expected_source.is_dir():
            failures.append(
                {
                    "kind": "component-source",
                    "component": name,
                    "reason": "required source subdirectory is missing",
                }
            )
            continue
        try:
            module = importlib.import_module(component["python_module"])
            module_path = _module_path(module)
            if not _inside(module_path, expected_source.resolve(strict=True)):
                raise RuntimeError(
                    "imported module is outside supplied component source"
                )
            if getattr(module, "__version__", None) != component["version"]:
                raise RuntimeError(
                    "component version differs from producer compatibility contract"
                )
            if name == "build-record":
                evidence = _build_record_smoke(module)
            elif name == "box-control":
                evidence = _box_control_smoke(module)
            else:
                evidence = {}
            checks.append(
                {
                    "kind": "component",
                    "component": name,
                    "status": "ready",
                    "version": component["version"],
                    "module": component["python_module"],
                    "source": str(module_path),
                    "validated_revision": component[
                        "validated_revision"
                    ],
                    "api_evidence": evidence,
                }
            )
        except Exception as error:
            failures.append(
                {
                    "kind": "component",
                    "component": name,
                    "reason": str(error),
                }
            )

    for dependency in requirements["external"]:
        try:
            module = importlib.import_module(
                dependency["python_module"]
            )
            observed = importlib.metadata.version(
                dependency["distribution"]
            )
            if observed != dependency["version"]:
                raise RuntimeError(
                    "external dependency version differs from producer contract"
                )
            checks.append(
                {
                    "kind": "external",
                    "distribution": dependency["distribution"],
                    "status": "ready",
                    "version": observed,
                    "module": dependency["python_module"],
                    "source": str(_module_path(module)),
                }
            )
        except Exception as error:
            failures.append(
                {
                    "kind": "external",
                    "distribution": dependency["distribution"],
                    "reason": str(error),
                }
            )

    return {
        "contract": PREFLIGHT_CONTRACT,
        "ready": not failures,
        "mutation": False,
        "python": {
            "executable": str(executable),
            "resolved_executable": os.path.realpath(sys.executable),
            "version": list(sys.version_info[:3]),
        },
        "image_build": {
            "repository_root": str(repository_root),
            "module": str(image_build_module),
        },
        "requirements": requirements,
        "checks": checks,
        "failures": failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--provenance", action="store_true")
    parser.add_argument("--controller", action="store_true")
    parser.add_argument(
        "--external-observed-state", action="store_true"
    )
    parser.add_argument(
        "--component-root",
        action="append",
        default=[],
        metavar="NAME=/ABSOLUTE/PATH",
    )
    args = parser.parse_args(argv)

    try:
        report = inspect_runtime(
            repository_root=args.repository_root,
            python_executable=args.python_executable,
            operation=args.operation,
            provenance=args.provenance,
            controller=args.controller,
            external_observed_state=args.external_observed_state,
            component_roots=args.component_root,
        )
    except Exception as error:
        report = {
            "contract": PREFLIGHT_CONTRACT,
            "ready": False,
            "mutation": False,
            "checks": [],
            "failures": [
                {
                    "kind": "preflight",
                    "reason": str(error),
                }
            ],
        }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

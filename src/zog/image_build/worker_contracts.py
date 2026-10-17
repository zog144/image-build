"""Machine-readable semantics for maintained image-build worker identities.

These names are public task identities, but they are not aliases for generic
pipeline.submit target lists. Their modules own additional durable state,
composition, probes, recovery, or publication semantics.
"""
from __future__ import annotations

import json

from .errors import ImageBuildError

CONTRACT = "image-build-maintained-worker-v1"

_WORKERS = {
    "stages": {
        "module": "zog.image_build.stages",
        "required_options": [
            "project",
            "package-dir",
            "plan",
            "controller-config",
            "seed",
        ],
        "optional_options": ["restart-incomplete-stage"],
        "semantics": [
            "materialize-reviewed-stage-plan",
            "seed-verification-pipeline",
            "cross-bootstrap-assembly",
            "link-probe",
            "runtime-generation-publication",
        ],
    },
    "native-stage": {
        "module": "zog.image_build.native_stage",
        "required_options": [
            "project",
            "catalogue",
            "plan",
            "controller",
            "selection",
            "work",
        ],
        "optional_options": [],
        "semantics": [
            "materialize-reviewed-stage-plan",
            "native-stage-durable-operation",
            "native-pipeline",
        ],
    },
    "glibc-final": {
        "module": "zog.image_build.glibc_final",
        "required_options": [
            "project",
            "attempt",
            "base-generation",
            "previous-package",
            "work",
        ],
        "optional_options": [
            "recover-empty-mount-directories",
            "base-directory",
        ],
        "semantics": [
            "recover-prior-attempt",
            "normalize-glibc-package",
            "compose-candidate-root",
            "cache-and-runtime-probes",
            "native-final-libc-publication",
        ],
    },
    "glibc-publish": {
        "module": "zog.image_build.glibc_publish",
        "required_options": [
            "project",
            "previous",
            "work",
            "controller",
        ],
        "optional_options": [],
        "semantics": [
            "verify-retained-glibc-evidence",
            "runtime-probe",
            "native-final-libc-publication",
        ],
    },
    "final-math": {
        "module": "zog.image_build.final_math",
        "required_options": [
            "project",
            "catalogue",
            "controller",
            "selection",
            "work",
        ],
        "optional_options": [],
        "semantics": [
            "require-native-final-libc",
            "materialize-final-math-plan",
            "durable-arithmetic-build",
            "generation-publication",
        ],
    },
    "final-compiler": {
        "module": "zog.image_build.final_compiler",
        "required_options": [
            "project",
            "catalogue",
            "controller",
            "selection",
            "arithmetic",
            "ownership",
            "work",
        ],
        "optional_options": [],
        "semantics": [
            "require-final-libc-and-arithmetic",
            "materialize-multiple-reviewed-plans",
            "replace-temporary-binutils-and-gcc",
            "three-stage-compiler-comparison",
            "acceptance-probes",
            "self-hosted-toolchain-publication",
        ],
    },
}


def names():
    return tuple(sorted(_WORKERS))


def modules():
    return {
        name: value["module"]
        for name, value in sorted(_WORKERS.items())
    }


def describe(worker=None):
    if worker is None:
        selected = _WORKERS
    else:
        if not isinstance(worker, str) or worker not in _WORKERS:
            raise ImageBuildError("unknown maintained worker identity")
        selected = {worker: _WORKERS[worker]}
    return {
        "contract": CONTRACT,
        "workers": {
            name: {
                "task": name,
                "dispatch_interface": "maintained-worker",
                "entrypoint": (
                    "python -m zog.image_build.worker " + name
                ),
                "generic_pipeline_submit_equivalent": False,
                "required_options": list(value["required_options"]),
                "optional_options": list(value["optional_options"]),
                "semantics": list(value["semantics"]),
            }
            for name, value in sorted(selected.items())
        },
    }


def validate(value):
    try:
        copy = json.loads(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    except (TypeError, ValueError) as error:
        raise ImageBuildError(
            "maintained worker contract must be JSON data"
        ) from error
    if copy != describe():
        raise ImageBuildError("maintained worker contract differs")
    return copy

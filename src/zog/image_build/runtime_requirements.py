"""Operation-aware companion requirements for the remote image-build CLI.

This module is intentionally dependency-light.  It may be imported before provenance,
controller configuration, or image-build mutable state is initialized.
"""
from __future__ import annotations

from .remote_contract import SUPPORTED_OPERATIONS

CONTRACT = "image-build-runtime-dependencies-v1"
PREFLIGHT_CONTRACT = "image-build-runtime-preflight-v1"
SMOKE_CONTRACT = "image-build-runtime-companion-smoke-v1"

DECLARED_COMPONENT_DEPENDENCIES = (
    "box-control",
    "build-record",
    "host-identify",
)

BUILD_RECORD = {
    "component": "build-record",
    "repository": "zog144/build-record",
    "validated_revision": "a866c9c4b0dd385045f00ce2de7d809f5b67c104",
    "python_module": "zog.build_record",
    "version": "0.8.2",
    "source_subdir": "src",
    "component_dependencies": [],
    "external_dependencies": [],
    "required_api": [
        "make_record",
        "Store",
        "verify_artifacts",
        "model.digest",
        "model.artifact_references",
        "model.ENVIRONMENT",
    ],
}

BOX_CONTROL = {
    "component": "box-control",
    "repository": "zog144/box-control",
    "validated_revision": "644170fc441863307092f329bf7e23cb64eb33e2",
    "python_module": "zog.box_control",
    "version": "0.1.0",
    "source_subdir": "box-control/src",
    "component_dependencies": ["image-build"],
    "external_dependencies": ["dbus-next==0.2.3"],
    "required_api": [
        "BoxControl",
        "Project",
        "runtime.root_control.RootControlSystemdTransport",
        "build_jobs.BuildJobs",
    ],
}

DBUS_NEXT = {
    "distribution": "dbus-next",
    "python_module": "dbus_next",
    "version": "0.2.3",
}


def _copy(value):
    import json
    return json.loads(json.dumps(value, sort_keys=True))


def requirements_for(
    operation,
    *,
    provenance=False,
    controller=False,
    external_observed_state=False,
):
    if operation not in SUPPORTED_OPERATIONS:
        raise ValueError("unsupported remote operation")
    if controller and external_observed_state:
        raise ValueError(
            "controller and external observed state are mutually exclusive"
        )
    if external_observed_state and operation != "pipeline.inspect":
        raise ValueError(
            "external observed state permits only pipeline.inspect"
        )

    components = []
    external = []
    if provenance:
        components.append(_copy(BUILD_RECORD))
    if controller:
        components.append(_copy(BOX_CONTROL))
        external.append(_copy(DBUS_NEXT))

    return {
        "contract": CONTRACT,
        "operation": operation,
        "bindings": {
            "provenance": bool(provenance),
            "controller": bool(controller),
            "external_observed_state": bool(external_observed_state),
        },
        "components": components,
        "external": external,
    }


def describe():
    return {
        "contract": CONTRACT,
        "preflight_contract": PREFLIGHT_CONTRACT,
        "preflight_entrypoint": "python -B -m zog.image_build.runtime_preflight",
        "smoke_contract": SMOKE_CONTRACT,
        "smoke_entrypoint": "python -B -m zog.image_build.runtime_companion_smoke",
        "declared_component_dependencies": list(
            DECLARED_COMPONENT_DEPENDENCIES
        ),
        "profiles": {
            "provenance": {
                "enabled_by": "provenance CLI binding",
                "components": [_copy(BUILD_RECORD)],
                "external": [],
            },
            "controller": {
                "enabled_by": "controller-config CLI binding",
                "components": [_copy(BOX_CONTROL)],
                "external": [_copy(DBUS_NEXT)],
            },
            "external_observed_state": {
                "enabled_by": "observed-state-dir CLI binding",
                "operations": ["pipeline.inspect"],
                "controller": False,
            },
        },
        "notes": [
            "Declared component dependencies describe the aggregate image-build component closure; operation-specific requirements are narrower.",
            "The validated sibling revisions are compatibility checkpoints, not moving branch references. The consumer still freezes the exact staged source revision.",
            "The preflight is read-only and runs before provenance/controller initialization.",
        ],
    }

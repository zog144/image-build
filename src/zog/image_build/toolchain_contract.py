"""Machine-readable toolchain bootstrap, verification and artifact contracts.

This module does not execute a compiler build.  It defines the producer-owned graph
that maintained workers implement and the immutable contract a final self-hosted
toolchain generation may opt into.
"""
from __future__ import annotations

from .errors import ImageBuildError
from .metadata import identity

SPECIFICATION_CONTRACT = "image-build-toolchain-specification-v1"
BOOTSTRAP_CONTRACT = "image-build-toolchain-bootstrap-pipeline-v1"
VERIFICATION_CONTRACT = "image-build-toolchain-verification-v1"
ARTIFACT_CONTRACT = "image-build-toolchain-artifact-v1"
FINAL_PROFILE = "self-hosted-c-cxx-toolchain-v1"

FINAL_CHECKS = (
    "compiler-version",
    "linker-version",
    "glibc-version",
    "c-compile-and-run",
    "cxx-threads-exceptions-and-lto",
    "dynamic-loader",
    "no-rpath-or-runpath",
    "host-search-paths",
    "installed-m4",
)

_PHASES = (
    {
        "id": "cross-bootstrap",
        "producers": ["zog.image_build.stages"],
        "input_kinds": ["host-bootstrap"],
        "output_kinds": ["bootstrap-runtime"],
        "repeatable": False,
        "durability": ["operation.json", "pipeline records", "controller checkpoints"],
    },
    {
        "id": "native-bootstrap",
        "producers": [
            "zog.image_build.native",
            "zog.image_build.native_tools",
            "zog.image_build.native_stage",
        ],
        "input_kinds": [
            "host-bootstrap",
            "temporary-userspace",
            "native-temporary-toolchain",
            "toolchain",
            "native-check",
        ],
        "output_kinds": [
            "native-temporary-toolchain",
            "toolchain",
            "native-check",
        ],
        "repeatable": True,
        "durability": ["operation.json or intent.json", "pipeline records", "controller checkpoints"],
    },
    {
        "id": "final-libc",
        "producers": [
            "zog.image_build.glibc_final",
            "zog.image_build.glibc_publish",
        ],
        "input_kinds": ["native temporary/final build environment"],
        "output_kinds": ["native-final-libc"],
        "repeatable": False,
        "durability": ["intent.json", "acceptance.json", "controller checkpoints"],
    },
    {
        "id": "final-math",
        "producers": ["zog.image_build.final_math"],
        "input_kinds": ["native-final-libc"],
        "output_kinds": ["native-check"],
        "required_targets": ["mpc-final"],
        "repeatable": False,
        "durability": ["intent.json", "pipeline records", "controller checkpoints"],
    },
    {
        "id": "final-compiler",
        "producers": [
            "zog.image_build.final_compiler",
            "zog.image_build.retained_compiler",
        ],
        "input_kinds": ["native-final-libc", "native-check"],
        "output_kinds": ["toolchain"],
        "output_profile": FINAL_PROFILE,
        "repeatable": False,
        "durability": ["intent.json", "result.json", "controller checkpoints"],
    },
)


def _sha(value):
    return "sha256:" + identity(value)


def describe():
    payload = {
        "contract": SPECIFICATION_CONTRACT,
        "bootstrap_pipeline": {
            "contract": BOOTSTRAP_CONTRACT,
            "phases": [dict(phase) for phase in _PHASES],
            "automatic_retry": False,
            "implicit_generation_promotion": False,
            "arbitrary_command_execution": False,
            "remote_execution_operation": None,
            "remote_execution_status": "typed-worker-contract-required",
        },
        "verification": {
            "contract": VERIFICATION_CONTRACT,
            "profile": FINAL_PROFILE,
            "required_checks": list(FINAL_CHECKS),
            "controller_completion_required": True,
            "process_cleanup_required": True,
        },
        "immutable_artifact": {
            "contract": ARTIFACT_CONTRACT,
            "profile": FINAL_PROFILE,
            "kind": "toolchain",
            "stage": 2,
            "self_hosted": True,
            "source_built": True,
            "build_environment_complete": True,
            "activation": "toolchain-active",
            "generation_identity": "sha256 of immutable publication inputs",
        },
    }
    return {**payload, "identity": _sha(payload)}


def specification_binding():
    spec = describe()
    return {
        "contract": SPECIFICATION_CONTRACT,
        "identity": spec["identity"],
        "profile": FINAL_PROFILE,
    }


def _successful_execution(value, label):
    if (
        not isinstance(value, dict)
        or value.get("exit_code") != 0
        or value.get("cleanup_complete") is not True
    ):
        raise ImageBuildError(label + " lacks successful controller completion")
    return {
        key: value.get(key)
        for key in (
            "runtime_id",
            "invocation_id",
            "journal_reference",
            "exit_code",
            "cleanup_complete",
        )
        if key in value
    }


def verification_record(
    compiler_evidence,
    compiler_execution,
    m4_evidence,
    m4_execution,
):
    compiler_execution = _successful_execution(
        compiler_execution, "compiler verification"
    )
    m4_execution = _successful_execution(
        m4_execution, "M4 verification"
    )
    acceptance = {
        "compiler": compiler_evidence,
        "execution": compiler_execution,
        "m4": m4_evidence,
        "m4_execution": m4_execution,
    }
    payload = {
        "contract": VERIFICATION_CONTRACT,
        "profile": FINAL_PROFILE,
        "required_checks": list(FINAL_CHECKS),
        "compiler_evidence": _sha(compiler_evidence),
        "m4_evidence": _sha(m4_evidence),
        "compiler_execution": compiler_execution,
        "m4_execution": m4_execution,
        "acceptance_identity": identity(acceptance),
    }
    return {**payload, "identity": _sha(payload)}


def verification_binding(record):
    if (
        not isinstance(record, dict)
        or record.get("contract") != VERIFICATION_CONTRACT
        or record.get("profile") != FINAL_PROFILE
    ):
        raise ImageBuildError("invalid toolchain verification record")
    payload = {key: value for key, value in record.items() if key != "identity"}
    if record.get("identity") != _sha(payload):
        raise ImageBuildError("toolchain verification identity changed")
    if record.get("required_checks") != list(FINAL_CHECKS):
        raise ImageBuildError("toolchain verification checks changed")
    _successful_execution(
        record.get("compiler_execution"), "compiler verification"
    )
    _successful_execution(record.get("m4_execution"), "M4 verification")
    return {
        "contract": VERIFICATION_CONTRACT,
        "identity": record["identity"],
        "profile": FINAL_PROFILE,
    }


def artifact_record(verification):
    verified = verification_binding(verification)
    return {
        "contract": ARTIFACT_CONTRACT,
        "profile": FINAL_PROFILE,
        "specification": specification_binding()["identity"],
        "verification": verified["identity"],
        "activation": "toolchain-active",
    }


def validate_publication(inputs, details):
    """Validate opted-in final toolchain publication; legacy/intermediate is untouched."""
    binding = inputs.get("toolchain_specification") if isinstance(inputs, dict) else None
    if binding is None:
        return False
    if binding != specification_binding():
        raise ImageBuildError("toolchain specification binding changed")
    if (
        inputs.get("kind") != "toolchain"
        or inputs.get("stage") != 2
        or inputs.get("bootstrap") != "gcc-three-stage-comparison"
        or not isinstance(inputs.get("architecture"), str)
        or not inputs["architecture"]
    ):
        raise ImageBuildError("final toolchain publication inputs are incomplete")
    if (
        details.get("stage") != 2
        or details.get("self_hosted") is not True
        or details.get("source_built") is not True
        or details.get("build_environment_complete") is not True
    ):
        raise ImageBuildError("final toolchain publication flags are incomplete")
    verification = details.get("toolchain_verification")
    reference = verification_binding(verification)
    if inputs.get("toolchain_verification") != reference:
        raise ImageBuildError("toolchain verification binding changed")
    if inputs.get("acceptance") != verification.get("acceptance_identity"):
        raise ImageBuildError("toolchain acceptance identity changed")
    if details.get("toolchain_artifact") != artifact_record(verification):
        raise ImageBuildError("toolchain artifact contract changed")
    return True


def validate_final_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("kind") != "toolchain":
        raise ImageBuildError("final toolchain artifact requires toolchain generation")
    if not validate_publication(manifest.get("inputs", {}), manifest):
        raise ImageBuildError("generation does not opt into final toolchain artifact contract")
    if not isinstance(manifest.get("outputs"), list) or not manifest["outputs"]:
        raise ImageBuildError("final toolchain artifact output inventory is empty")
    return manifest

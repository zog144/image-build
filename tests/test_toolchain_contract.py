import copy

import pytest

from zog.image_build.errors import ImageBuildError
from zog.image_build.toolchain_contract import (
    ARTIFACT_CONTRACT,
    BOOTSTRAP_CONTRACT,
    FINAL_CHECKS,
    FINAL_PROFILE,
    SPECIFICATION_CONTRACT,
    VERIFICATION_CONTRACT,
    artifact_record,
    describe,
    specification_binding,
    validate_final_manifest,
    validate_publication,
    verification_binding,
    verification_record,
)


def completion(name):
    return {
        "runtime_id": "runtime-" + name,
        "invocation_id": "invocation-" + name,
        "journal_reference": "journal:" + name,
        "exit_code": 0,
        "cleanup_complete": True,
    }


def accepted():
    verification = verification_record(
        {"result": "compiler-ok"},
        completion("compiler"),
        {"result": "m4-ok"},
        completion("m4"),
    )
    inputs = {
        "schema": 2,
        "kind": "toolchain",
        "stage": 2,
        "architecture": "x86_64",
        "parent": "a" * 64,
        "bootstrap": "gcc-three-stage-comparison",
        "acceptance": verification["acceptance_identity"],
        "toolchain_specification": specification_binding(),
        "toolchain_verification": verification_binding(verification),
    }
    details = {
        "stage": 2,
        "self_hosted": True,
        "source_built": True,
        "build_environment_complete": True,
        "toolchain_verification": verification,
        "toolchain_artifact": artifact_record(verification),
    }
    return inputs, details


def test_toolchain_specification_freezes_bootstrap_and_final_contract():
    spec = describe()
    assert spec["contract"] == SPECIFICATION_CONTRACT
    assert spec["identity"].startswith("sha256:")
    pipeline = spec["bootstrap_pipeline"]
    assert pipeline["contract"] == BOOTSTRAP_CONTRACT
    assert [phase["id"] for phase in pipeline["phases"]] == [
        "cross-bootstrap",
        "native-bootstrap",
        "final-libc",
        "final-math",
        "final-compiler",
    ]
    assert pipeline["automatic_retry"] is False
    assert pipeline["implicit_generation_promotion"] is False
    assert pipeline["remote_execution_operation"] is None
    assert spec["verification"] == {
        "contract": VERIFICATION_CONTRACT,
        "profile": FINAL_PROFILE,
        "required_checks": list(FINAL_CHECKS),
        "controller_completion_required": True,
        "process_cleanup_required": True,
    }
    assert spec["immutable_artifact"]["contract"] == ARTIFACT_CONTRACT
    assert spec["immutable_artifact"]["stage"] == 2
    assert spec["immutable_artifact"]["activation"] == "toolchain-active"


def test_final_toolchain_publication_binds_specification_and_verification():
    inputs, details = accepted()
    assert validate_publication(inputs, details) is True
    manifest = {
        "kind": "toolchain",
        "inputs": inputs,
        "outputs": [{"kind": "file", "path": "usr/bin/cc", "sha256": "1" * 64}],
        **details,
    }
    assert validate_final_manifest(manifest) == manifest


@pytest.mark.parametrize(
    "change",
    [
        "specification",
        "bootstrap",
        "stage",
        "self-hosted",
        "source-built",
        "build-environment",
        "verification",
        "acceptance",
        "artifact",
    ],
)
def test_final_toolchain_contract_fails_closed(change):
    inputs, details = accepted()
    inputs = copy.deepcopy(inputs)
    details = copy.deepcopy(details)
    if change == "specification":
        inputs["toolchain_specification"]["identity"] = "sha256:" + "0" * 64
    elif change == "bootstrap":
        inputs["bootstrap"] = "unreviewed"
    elif change == "stage":
        inputs["stage"] = 1
    elif change == "self-hosted":
        details["self_hosted"] = False
    elif change == "source-built":
        details["source_built"] = False
    elif change == "build-environment":
        details["build_environment_complete"] = False
    elif change == "verification":
        details["toolchain_verification"]["required_checks"].pop()
    elif change == "acceptance":
        inputs["acceptance"] = "0" * 64
    else:
        details["toolchain_artifact"]["verification"] = "sha256:" + "0" * 64
    with pytest.raises(ImageBuildError):
        validate_publication(inputs, details)


def test_verification_requires_successful_cleanup():
    bad = completion("compiler")
    bad["cleanup_complete"] = False
    with pytest.raises(ImageBuildError, match="successful controller completion"):
        verification_record(
            {"result": "compiler-ok"},
            bad,
            {"result": "m4-ok"},
            completion("m4"),
        )


def test_legacy_toolchain_publication_remains_readable_without_opt_in():
    assert validate_publication(
        {"kind": "toolchain", "stage": 2},
        {"stage": 2, "self_hosted": True},
    ) is False

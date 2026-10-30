"""Targeted Boot A installed-verification publication binding and recovery."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zog.build_record import canonical
from zog.image_build import ImageBuild
from zog.image_build import generation_provenance as gp
from zog.image_build import installed_verification as iv
from zog.image_build.developer.seed_build import verify as run_verification
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory, write_json
from zog.image_build.final_compiler import successful_execution
from zog.image_build.metadata import Package, identity
from zog.image_build.provenance import Provenance
from zog.image_build.runner import BoxControlRunner, BuildExecutionResult


def _scenario(tmp_path, *, explicit_argv):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "payload").write_text("accepted bytes")
    monthly = tmp_path / "pin.py"
    monthly.write_text(repr({"date": "2026-10-01"}))
    state = tmp_path / "state"
    pin = Provenance.capture_pin(
        state,
        monthly,
        repository="fixture",
        revision="a" * 40,
        repository_path="pins/pin.py",
    )
    provenance = Provenance(
        state,
        host_id="host",
        project_id="project",
        pin=pin,
    )
    record = {"inputs": {}, "outputs": inventory(root)}
    record["identity"] = identity(record)
    record.update(
        root=str(root),
        provenance=provenance.legacy_output("base", record),
    )
    built = {"base": record}
    definitions = {
        "base": Package("base", (), (), (), {}, {}, (), {})
    }
    calls = []

    def execute(request):
        calls.append(request)
        return BuildExecutionResult(
            "build-job", "invocation", 0, True, "journal-reference"
        )

    execute.configuration = lambda: {
        "project_root": str(tmp_path / "controller-project"),
        "socket_path": str(tmp_path / "root-control.sock"),
        "execution_user_id": 1000,
        "execution_group_id": 1000,
        "startup_timeout_seconds": 30,
        "termination_grace_seconds": 5,
        "resource_limits": {
            "thread-count-maximum": 128,
            "memory-maximum-bytes": 1024 * 1024 * 1024,
        },
    }
    builder = ImageBuild(
        package_dir=tmp_path / "recipes",
        state_dir=state,
        runner=BoxControlRunner(execute=execute),
        provenance=provenance,
    )
    owner = {
        "kind": "image",
        "architecture": "fixture",
        "source_revision": "c" * 40,
        "verification_command": "fixture-check",
        "verification_report_contract": iv.CONTRACT,
        "verification_check": iv.TARGETED_CHECK,
        "execution_policy": builder._policy(),
    }
    if explicit_argv:
        owner[iv.ARGV_FIELD] = iv.verification_argv(owner)
    attempt = state / "image-build/attempts/assembly"
    binding = gp.prepare(
        provenance, attempt, definitions, ["base"], built, owner
    )
    check = state / "image-build/attempts/installed-check"
    run_verification(
        builder,
        check,
        root,
        iv.verification_commands(owner),
        owner,
    )
    execution = successful_execution(check)
    return SimpleNamespace(
        provenance=provenance,
        root=root,
        built=built,
        builder=builder,
        owner=owner,
        attempt=attempt,
        binding=binding,
        check=check,
        execution=execution,
        calls=calls,
    )


def _recovery():
    return {
        "contract": gp.PUBLICATION_RECOVERY_CONTRACT,
        "reason": "installed-verification-argv-binding",
        "producer_source_revision": "c" * 40,
        "recovery_source_revision": "d" * 40,
        "operation": "boot-a-targeted-retained",
        "intent_sha256": "sha256:" + "1" * 64,
        "assembly_prepared_sha256": "sha256:" + "2" * 64,
        "verification_prepared_sha256": "sha256:" + "3" * 64,
        "verification_result_sha256": "sha256:" + "4" * 64,
        "execution_invocation_id": "invocation",
    }


def test_retained_targeted_pipefail_capture_archive_and_publication(tmp_path):
    # No explicit argv emulates the retained ce4b1d75 owner inputs. The exact
    # targeted check compatibility rule must still bind the already-frozen
    # pipefail execution rather than reconstructing the historical short argv.
    s = _scenario(tmp_path, explicit_argv=False)
    expected = ["/bin/bash", "-eu", "-o", "pipefail", "-c", "fixture-check"]
    assert iv.verification_argv(s.owner) == expected
    assert list(s.calls[0].command) == expected

    report = iv.capture(
        s.provenance,
        s.binding,
        s.root,
        s.owner,
        s.check,
        s.execution,
    )
    recovery = _recovery()
    pointer = gp.finish(
        s.provenance,
        s.attempt,
        s.binding,
        s.root,
        verification=[report],
        recovery=recovery,
    )
    selected = s.builder._publish(
        s.root,
        s.owner,
        "image",
        {
            "packages": s.built,
            "build_record": pointer,
            "verification_execution": s.execution,
            "publication_recovery": recovery,
        },
    )
    bundle = gp.verify(s.provenance, selected)
    assert canonical(bundle)
    report_value = json.loads(
        (
            s.provenance.root
            / "artifacts"
            / report["digest"][7:]
        ).read_text()
    )
    assert report_value["commands_digest"] == (
        "sha256:" + identity([expected])
    )
    output = bundle["records"][pointer["output"]]["data"]
    recovery_descriptor = next(
        item
        for item in output["artifacts"]
        if item["name"] == "publication-recovery.json"
    )
    assert json.loads(
        (
            s.provenance.root
            / "artifacts"
            / recovery_descriptor["digest"][7:]
        ).read_text()
    ) == recovery
    assert selected.manifest["publication_recovery"] == recovery
    assert len(s.calls) == 1


def test_new_targeted_owner_freezes_exact_pipefail_argv(tmp_path):
    s = _scenario(tmp_path, explicit_argv=True)
    assert s.owner[iv.ARGV_FIELD] == [
        "/bin/bash", "-eu", "-o", "pipefail", "-c", "fixture-check"
    ]
    report = iv.capture(
        s.provenance,
        s.binding,
        s.root,
        s.owner,
        s.check,
        s.execution,
    )
    assert report["name"] == iv.NAME


def test_targeted_capture_rejects_mismatched_frozen_argv(tmp_path):
    s = _scenario(tmp_path, explicit_argv=False)
    prepared = json.loads((s.check / "prepared.json").read_text())
    prepared["commands"] = [
        ["/bin/bash", "-eu", "-c", s.owner["verification_command"]]
    ]
    write_json(s.check / "prepared.json", prepared)
    with pytest.raises(
        ImageBuildError,
        match="candidate or frozen inputs changed",
    ):
        iv.capture(
            s.provenance,
            s.binding,
            s.root,
            s.owner,
            s.check,
            s.execution,
        )


def test_targeted_explicit_argv_cannot_drop_pipefail():
    owner = {
        "verification_command": "check",
        "verification_check": iv.TARGETED_CHECK,
        iv.ARGV_FIELD: ["/bin/bash", "-eu", "-c", "check"],
    }
    with pytest.raises(
        ImageBuildError,
        match="must preserve pipefail",
    ):
        iv.verification_argv(owner)

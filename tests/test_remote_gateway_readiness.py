"""Gateway-readiness tests using the repository's real graphics recipes."""
import json
from pathlib import Path
import pprint
import shutil

from zog.image_build import ImageBuild, load_package
from zog.image_build.remote_operations import (
    CAPABILITIES_SCHEMA,
    REQUEST_SCHEMA,
    RemoteOperations,
)


REPOSITORY = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
GRAPHICS_ENTRIES = [
    {
        "id": "xcb-util-final",
        "project": "xcb-util",
        "recipe": "xcb-util/stages/final",
    },
    {
        "id": "xcb-util-image-final",
        "project": "xcb-util-image",
        "recipe": "xcb-util-image/stages/final",
    },
    {
        "id": "xcb-util-keysyms-final",
        "project": "xcb-util-keysyms",
        "recipe": "xcb-util-keysyms/stages/final",
    },
    {
        "id": "xcb-util-wm-final",
        "project": "xcb-util-wm",
        "recipe": "xcb-util-wm/stages/final",
    },
    {
        "id": "xcb-util-xrm-final",
        "project": "xcb-util-xrm",
        "recipe": "xcb-util-xrm/stages/final",
    },
]
GRAPHICS_TARGETS = [
    "xcb-util-image-final",
    "xcb-util-keysyms-final",
    "xcb-util-wm-final",
    "xcb-util-xrm-final",
]
TEST_PIN_DATE = "2000-01-01"


def ephemeral_catalogue(tmp_path):
    project = tmp_path / "reviewed-project"
    catalogue = project / "package"
    shutil.copytree(REPOSITORY / "project/package", catalogue)
    packages = {}
    for entry in GRAPHICS_ENTRIES:
        package = load_package(catalogue / entry["recipe"])
        packages.setdefault(entry["project"], {"recipes": {}})["recipes"][
            entry["recipe"]
        ] = list(package.sources)
    pin_dir = project / "pins" / TEST_PIN_DATE
    pin_dir.mkdir(parents=True)
    pin = {"schema": 1, "date": TEST_PIN_DATE, "packages": packages}
    (pin_dir / "commit-pin.py").write_text(
        "# Inactive source-publication test pin; do not activate.\n"
        + pprint.pformat(pin, sort_dicts=False)
        + "\n"
    )
    return catalogue


def request(operation_id, operation, arguments):
    return {
        "schema": REQUEST_SCHEMA,
        "operation_id": operation_id,
        "operation": operation,
        "source": {
            "repository": "zog144/image-build",
            "revision": REVISION,
        },
        "arguments": arguments,
    }


def adapter(builder, *, repository_root=REPOSITORY):
    return RemoteOperations(
        builder,
        repository_root=repository_root,
        source_repository="zog144/image-build",
        source_revision=REVISION,
    )


def test_capability_contract_declares_generic_submit_and_worker_boundary(tmp_path):
    builder = ImageBuild(
        package_dir=REPOSITORY / "project/package",
        state_dir=tmp_path / "state",
    )
    result = adapter(builder).execute(
        request("gateway-capabilities", "capabilities.inspect", {})
    )
    assert result["status"] == "completed"
    contract = result["artifacts"]["remote_capabilities"]
    assert contract["contract"] == CAPABILITIES_SCHEMA
    assert contract["source"] == {
        "repository": "zog144/image-build",
        "revision": REVISION,
    }
    assert contract["generic_pipeline"]["supported"] is True
    assert contract["generic_pipeline"]["recipe_snapshot"] == {
        "operation": "recipes.snapshot",
        "contract": "image-build-recipe-snapshot-v1",
        "required_for": ["pipeline.submit", "pipeline.retry"],
    }
    assert contract["generic_pipeline"]["submit"]["operation"] == "pipeline.submit"
    assert contract["generic_pipeline"]["submit"]["snapshot_predecessor"] == {
        "field": "predecessor",
        "operation": "recipes.snapshot",
        "required": False,
        "when_present": "must-bind-same-completed-snapshot",
    }
    assert contract["generic_pipeline"]["submit"]["modes"] == [
        "bootstrap",
        "image",
        "native-check",
        "seed-check",
    ]
    assert contract["maintained_workers"]["remote_execution_operation"] is None
    assert contract["reporting"] == {
        "execution_evidence_contract": "image-build-remote-execution-evidence-v1",
        "controller_jobs_limit": 24,
        "result_bytes_limit": 128 * 1024,
    }
    runtime = contract["runtime_dependencies"]
    assert runtime["contract"] == "image-build-runtime-dependencies-v1"
    assert runtime["preflight_contract"] == "image-build-runtime-preflight-v1"
    assert runtime["preflight_entrypoint"] == (
        "python -B -m zog.image_build.runtime_preflight"
    )
    assert runtime["smoke_contract"] == (
        "image-build-runtime-companion-smoke-v1"
    )
    assert runtime["smoke_entrypoint"] == (
        "python -B -m zog.image_build.runtime_companion_smoke"
    )
    build_record = runtime["profiles"]["provenance"]["components"][0]
    assert build_record["repository"] == "zog144/build-record"
    assert build_record["validated_revision"] == (
        "a866c9c4b0dd385045f00ce2de7d809f5b67c104"
    )
    assert build_record["version"] == "0.8.2"
    assert build_record["source_subdir"] == "src"
    assert build_record["component_dependencies"] == []
    assert build_record["external_dependencies"] == []
    box_control = runtime["profiles"]["controller"]["components"][0]
    assert box_control["repository"] == "zog144/box-control"
    assert box_control["validated_revision"] == (
        "644170fc441863307092f329bf7e23cb64eb33e2"
    )
    assert box_control["version"] == "0.1.0"
    assert box_control["source_subdir"] == "box-control/src"
    assert (
        contract["maintained_workers"]["generic_pipeline_submit_equivalent"]
        is False
    )
    assert set(contract["maintained_workers"]["workers"]) == {
        "stages",
        "native-stage",
        "glibc-final",
        "glibc-publish",
        "final-math",
        "final-compiler",
    }


def test_real_graphics_snapshot_prepares_durable_generic_pipeline_without_execution(
    tmp_path, monkeypatch
):
    builder = ImageBuild(
        package_dir=ephemeral_catalogue(tmp_path),
        state_dir=tmp_path / "state",
    )
    host = tmp_path / "bootstrap"
    host.mkdir()
    (host / "seed").write_text("gateway-readiness")
    selection = builder.import_bootstrap(
        host, {"fixture": "graphics-gateway-readiness"}
    )
    remote = adapter(builder, repository_root=tmp_path)

    snapshot_request = request(
        "graphics-snapshot-a",
        "recipes.snapshot",
        {
            "entries": list(reversed(GRAPHICS_ENTRIES)),
            "pin_date": TEST_PIN_DATE,
        },
    )
    first = remote.execute(snapshot_request)
    assert first["status"] == "completed"
    snapshot = first["recipe_identity"]
    assert first["artifacts"]["packages"].keys() == {
        entry["id"] for entry in GRAPHICS_ENTRIES
    }

    second = remote.execute(
        request(
            "graphics-snapshot-b",
            "recipes.snapshot",
            {
                "entries": GRAPHICS_ENTRIES,
                "pin_date": TEST_PIN_DATE,
            },
        )
    )
    assert second["status"] == "completed"
    assert second["recipe_identity"] == snapshot

    manifest_path = (
        builder.state
        / "image-build/recipe-snapshots/snapshots"
        / snapshot[7:]
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["entries"] == sorted(
        GRAPHICS_ENTRIES, key=lambda item: item["id"]
    )
    assert set(manifest["packages"]) == {
        entry["id"] for entry in GRAPHICS_ENTRIES
    }

    resume_calls = []

    def stop_before_execution(pipeline_id):
        resume_calls.append(pipeline_id)
        raise KeyboardInterrupt("gateway-readiness preparation boundary")

    monkeypatch.setattr(builder, "resume", stop_before_execution)
    submit_request = request(
        "graphics-submit",
        "pipeline.submit",
        {
            "mode": "image",
            "selection": selection.generation,
            "targets": GRAPHICS_TARGETS,
            "recipe_snapshot": snapshot,
        },
    )
    submitted = remote.execute(submit_request)
    assert submitted["status"] == "pending"
    assert submitted["recipe_identity"] == snapshot
    assert submitted["failure"]["type"] == "KeyboardInterrupt"
    assert resume_calls == [submitted["pipeline_id"]]

    pipeline = builder.inspect_pipeline(submitted["pipeline_id"])
    assert pipeline["owner"] == {
        "contract": REQUEST_SCHEMA,
        "operation_id": "graphics-submit",
        "source_repository": "zog144/image-build",
        "source_revision": REVISION,
        "recipe_snapshot": snapshot,
    }
    assert pipeline["recipes"] == manifest["inventory"]
    assert pipeline["attempts"] == {}

    replay = remote.execute(submit_request)
    assert replay["pipeline_id"] == submitted["pipeline_id"]
    assert replay["recipe_identity"] == snapshot
    assert resume_calls == [submitted["pipeline_id"], submitted["pipeline_id"]]

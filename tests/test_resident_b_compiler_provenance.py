"""Source-only acceptance: reviewed original reader and fail-closed operation trace."""
import copy
import json
from pathlib import Path

import pytest

from tools import trace_resident_b_compiler_provenance as provenance

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / "project/host/resident-b-compiler-provenance-successor-v1.json"


def test_reviewed_reader_blob_identity_retained_without_regenerating_issuance():
    from zog.image_build import compiler_base_acceptance as ca
    assert provenance.checked_reader() is ca
    assert provenance.git_blob(Path(ca.__file__).read_bytes()) == (
        "3eb562bbf2460fb95af0780a079cb2b058650f80")
    assert ca.SCHEMA == "image-build-compiler-base-acceptance-v1"
    assert ca.BINDING == "image-build-compiler-base-binding-v1"


def test_successor_selection_is_held_and_does_not_forge_original_operation():
    value = json.loads(SELECTOR.read_text())
    assert value["status"] == "HISTORICAL_OPERATION_UNRESOLVED_NATIVE_HOLD"
    assert value["original"]["authenticated_project_id"] is None
    assert value["original"]["authenticated_operation_id"] is None
    assert value["original"]["signed_receipt_reopened_by_this_source"] is False
    assert value["activation"]["native_build_permitted"] is False
    assert value["activation"]["original_operation_replay_permitted"] is False
    assert value["activation"]["original_records_mutable"] is False


@pytest.fixture
def original(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    host, project, attempt = "fixture-host", "zog-compiler-view", "application-image-facilities-oct11-assembly"
    digest = "sha256:" + "a" * 64
    binding = {
        "schema": "image-build-compiler-base-binding-v1",
        "status": "independent-compiler-capability-observed-not-job-authorization",
        "generation_id": provenance.GENERATION,
        "acceptance_receipt_sha256": provenance.RECEIPT,
        "generation_record_sha256": digest,
        "project_id": project,
        "host_id": host,
    }
    manifest = {"build_record": {
        "host_id": host, "project_id": project,
        "generation": provenance.GENERATION, "record": digest,
        "build_id": "attempt:" + attempt,
    }, "inputs": {"provenance": {"host_id": host, "project_id": project}}}
    return state, manifest, binding, attempt


def _write(state, path, record):
    target = state / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")))


def _operation_records(state, attempt, *, operation_id="b" * 32, pipeline_id="c" * 32):
    source = {"repository": "zog144/image-build", "revision": "d" * 40}
    owner = {"contract": "image-build-remote-operation-request-v1",
             "operation_id": operation_id,
             "source_repository": source["repository"],
             "source_revision": source["revision"]}
    # Contract copies the exact persisted request schema; this is synthetic
    # linkage, not an assertion about the historical Oct 11 producer.
    request = {"schema": owner["contract"], "operation_id": operation_id,
               "operation": "pipeline.submit", "source": source,
               "arguments": {"mode": "image"}}
    record = {"pipeline_id": pipeline_id, "status": "complete", "operation": "image",
              "generation": provenance.GENERATION,
              "attempts": {"image": attempt}, "owner": owner}
    result = {"operation_id": operation_id, "operation_type": "pipeline.submit",
              "pipeline_id": pipeline_id, "status": "completed",
              "terminal_outcome": "success", "uncertainty": False}
    _write(state, "image-build/pipelines/" + pipeline_id + "/pipeline.json", record)
    _write(state, "image-build/remote-operations/" + operation_id + "/request.json", request)
    _write(state, "image-build/remote-operations/" + operation_id + "/binding.json", {"pipeline_id": pipeline_id})
    _write(state, "image-build/remote-operations/" + operation_id + "/result.json", result)
    return record, request, result


def test_build_record_attempt_never_becomes_fabricated_remote_operation(original):
    state, manifest, binding, attempt = original
    record = provenance.trace_records(state=state, manifest=manifest, binding=binding)
    assert record["assembly_attempt"] == attempt
    assert record["operation_id"] is None
    assert record["authenticated_operation"] is False
    assert record["status"] == "HISTORICAL_OPERATION_UNRESOLVED"
    assert not record["native_build_permitted"]


def test_unowned_historical_pipeline_remains_unresolved(original):
    state, manifest, binding, attempt = original
    p, _, _ = _operation_records(state, attempt)
    p.pop("owner")
    _write(state, "image-build/pipelines/" + p["pipeline_id"] + "/pipeline.json", p)
    record = provenance.trace_records(state=state, manifest=manifest, binding=binding)
    assert record["pipeline_id"] == p["pipeline_id"]
    assert record["operation_id"] is None
    assert record["status"] == "HISTORICAL_OPERATION_UNRESOLVED"


def test_uniquely_linked_original_operation_is_read_only_and_unprivileged(original):
    state, manifest, binding, attempt = original
    p, _, _ = _operation_records(state, attempt)
    result = provenance.trace_records(state=state, manifest=manifest, binding=binding)
    assert result["operation_id"] == "b" * 32
    assert result["pipeline_id"] == p["pipeline_id"]
    assert result["status"] == "ORIGINAL_PROJECT_AND_OPERATION_LINKED"
    assert result["authenticated_operation"] is True
    assert result["native_build_permitted"] is False
    assert result["service_activation_permitted"] is False
    # No path under the original evidence tree is created or rewritten.
    assert len(list((state / "image-build/remote-operations").rglob("*.json"))) == 3


@pytest.mark.parametrize("malformed", ["changed-request", "changed-binding", "changed-outcome",
                                      "changed-project", "changed-pointer", "changed-attempt"])
def test_conflicting_source_identity_fails_closed(original, malformed):
    state, manifest, binding, attempt = original
    pipeline, request, result = _operation_records(state, attempt)
    if malformed == "changed-request":
        request["source"]["revision"] = "f" * 40
        _write(state, "image-build/remote-operations/" + "b"*32 + "/request.json", request)
    elif malformed == "changed-binding":
        _write(state, "image-build/remote-operations/" + "b"*32 + "/binding.json",
               {"pipeline_id": "e" * 32})
    elif malformed == "changed-outcome":
        result["terminal_outcome"] = "unknown"
        _write(state, "image-build/remote-operations/" + "b"*32 + "/result.json", result)
    elif malformed == "changed-project":
        binding["project_id"] = "wrong-project"
    elif malformed == "changed-pointer":
        manifest["build_record"]["record"] = "sha256:" + "f" * 64
    elif malformed == "changed-attempt":
        _write(state, "image-build/attempts/" + attempt + "/assembly/generation.json",
               {"generation": provenance.GENERATION, "record": "sha256:" + "f" * 64,
                "build_id": "attempt:" + attempt})
    with pytest.raises(provenance.ProvenanceHold):
        provenance.trace_records(state=state, manifest=manifest, binding=binding)


def test_missing_remote_terminal_result_does_not_infer_operation(original):
    state, manifest, binding, attempt = original
    _operation_records(state, attempt)
    (state / "image-build/remote-operations/" / ("b" * 32) / "result.json").unlink()
    result = provenance.trace_records(state=state, manifest=manifest, binding=binding)
    assert result["status"] == "HISTORICAL_OPERATION_UNRESOLVED"
    assert result["operation_id"] is None


def test_duplicate_claim_to_same_assembly_is_not_disambiguated_by_sort_order(original):
    state, manifest, binding, attempt = original
    first, _, _ = _operation_records(state, attempt)
    duplicate = copy.deepcopy(first)
    duplicate["pipeline_id"] = "d" * 32
    _write(state, "image-build/pipelines/" + duplicate["pipeline_id"] + "/pipeline.json", duplicate)
    with pytest.raises(provenance.ProvenanceHold, match="multiple"):
        provenance.trace_records(state=state, manifest=manifest, binding=binding)


def test_symlinked_or_duplicate_json_evidence_cannot_claim_original_operation(original):
    state, manifest, binding, attempt = original
    _operation_records(state, attempt)
    request = state / "image-build/remote-operations/" / ("b" * 32) / "request.json"
    request.write_text('{"schema":"x","schema":"x"}')
    with pytest.raises(provenance.ProvenanceHold, match="duplicate"):
        provenance.trace_records(state=state, manifest=manifest, binding=binding)
    request.unlink()
    request.symlink_to("/etc/passwd")
    with pytest.raises(provenance.ProvenanceHold):
        provenance.trace_records(state=state, manifest=manifest, binding=binding)

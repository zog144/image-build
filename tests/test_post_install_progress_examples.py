import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "examples/host-welcome/post-install-progress-v2"
EXPECTED = {
    "successful.json": ("succeeded", "pipeline-complete-publication-unobserved"),
    "in-progress.json": ("running", "pipeline-running"),
    "failed.json": ("failed", "command-failed"),
    "interrupted.json": ("uncertain", "command-outcome-uncertain"),
    "unknown.json": ("unknown", "selection-unobserved"),
    "published.json": ("succeeded", "view-published-compatible"),
}


def test_host_welcome_v2_examples_are_exact_bounded_and_sanitized():
    assert {path.name for path in EXAMPLES.glob("*.json")} == set(EXPECTED)
    for name, expected in EXPECTED.items():
        value = json.loads((EXAMPLES / name).read_text())
        assert set(value) == {
            "schema", "snapshot_id", "observed_at", "producer",
            "producer_source", "boot_id", "selection_owner", "items", "page",
        }
        assert value["schema"] == "image-build-post-install-progress-v2"
        assert value["producer"] == "image-build"
        assert value["selection_owner"] == "host-install"
        assert value["producer_source"] == {
            "contract": "image-build-post-install-source-v1",
            "repository": "zog144/image-build",
            "revision": "a" * 40,
        }
        assert len(value["items"]) == 1
        item = value["items"][0]
        assert (item["state"], item["message_code"]) == expected
        assert item["progress"] is None
        assert item["runtime_admission"] == "unobserved"
        assert item["commands_truncated"] is False
        encoded = json.dumps(value, sort_keys=True).lower()
        for forbidden in (
            "argv", "environment", "journal", "/etc/", "/var/", "/home/",
            "password", "credential", "private_key", "bearer ",
            "https://", "http://",
        ):
            assert forbidden not in encoded


def test_published_example_keeps_build_publication_and_runtime_separate():
    item = json.loads((EXAMPLES / "published.json").read_text())["items"][0]
    assert item["pipeline_state"] == "complete"
    assert item["commands"][0]["state"] == "succeeded"
    assert item["publication"]["state"] == "succeeded"
    assert item["publication"]["compatibility_checked"] is True
    assert len(item["publication"]["rootfs_generation"]) == 64
    assert item["runtime_admission"] == "unobserved"


def test_interrupted_example_preserves_exact_command_identity_without_success():
    item = json.loads((EXAMPLES / "interrupted.json").read_text())["items"][0]
    command = item["commands"][0]
    assert item["pipeline_state"] == "pending"
    assert command["controller_request_id"] == "signed-build-123"
    assert command["build_job_id"] == "3" * 32
    assert command["controller_observed_at"] is None
    assert command["state"] == "uncertain"
    assert command["message_code"] == "command-observation-missing"

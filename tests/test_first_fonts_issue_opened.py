"""Cross-repository proof of actual first Fonts GitHub issues.opened source.

The authoritative event workflow runs in host-deploy, not in image-build.
No AWS credentials, GitHub mutations, real queue calls or compiler tasks.
"""
import copy
import json
import os
from pathlib import Path
import sys

import pytest

TASKC = Path(os.environ["ZOG_HOSTDEPLOY_TASKC_PR26"]).resolve()
SOURCE_ROOT = TASKC / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from zog.host_deploy.gateway import github_dispatch, github_configuration, protocol


SOURCE = "1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
FONTS = "graphics-fonts-image-v1"
WORKSPACE_ID = "2" * 32
QUEUE = "https://sqs.us-east-1.amazonaws.com/123456789012/zog-build-requests.fifo"


def event(number=39, actor="zog144", intent=None):
    if intent is None:
        intent = {
            "schema": 1,
            "workspace_id": WORKSPACE_ID,
            "operation": "build.submit",
            "parameters": {"lane": "compiler-fonts", "task": FONTS},
        }
    return {
        "action": "opened",
        "repository": {"full_name": "zog144/host-deploy", "id": 543},
        "sender": {"login": actor, "type": "User"},
        "issue": {
            "number": number, "state": "open",
            "user": {"login": actor},
            "body": github_dispatch.ISSUE_MARKER + "\n```json\n"
                    + json.dumps(intent) + "\n```",
        },
    }


def config():
    return {
        "GITHUB_EVENT_NAME": "issues", "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_ACTOR": "zog144", "GITHUB_TRIGGERING_ACTOR": "zog144",
        "GITHUB_REPOSITORY": "zog144/host-deploy",
        "GITHUB_REPOSITORY_ID": "543",
        "ZOG_GATEWAY_DISPATCH_REVISION": "cdbf97facb07979d1ad19dcb5791211c90146f5f",
        "ZOG_GATEWAY_AWS_REGION": "us-east-1",
        "ZOG_GATEWAY_QUEUE_URL": QUEUE,
        "ZOG_GATEWAY_ROLE_ARN": "arn:aws:iam::123456789012:role/test-fonts-github",
        "ZOG_GATEWAY_AUTHORIZED_ACTORS": '["zog144"]',
        "ZOG_GATEWAY_ALLOWED_OPERATIONS": '["build.submit"]',
        "ZOG_GATEWAY_FONTS_ENABLED": "true",
    }


def prepare(tmp_path, event_data=None, env=None):
    event_file = tmp_path / "opened.json"
    event_file.write_text(json.dumps(event_data if event_data is not None else event()))
    output = tmp_path / "prepared.json"
    summary = github_configuration.prepare_configured(
        event_file, output, config() if env is None else env
    )
    return summary, protocol.loads_request(output.read_bytes()), output


def test_actual_first_fonts_issue_handler_binds_reviewed_source_and_stable_id(tmp_path):
    summary, request, output = prepare(tmp_path)
    assert request["source"] == {
        "repository": "zog144/image-build", "commit": SOURCE
    }
    assert request["parameters"] == {
        "lane": "compiler-fonts", "task": FONTS
    }
    assert request["origin"] == {
        "repository": "zog144/host-deploy", "issue_number": 39,
        "trigger_actor": "zog144"
    }
    assert summary["request_id"] == github_dispatch.first_fonts_request_id(39)
    assert request["request_id"] == github_dispatch.first_fonts_request_id(39)
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.read_bytes() == protocol.canonical_bytes(request) + b"\n"
    assert github_dispatch.first_fonts_request_id(40) != request["request_id"]
    assert github_dispatch.prepare_event(event(), {"zog144"}) == request


@pytest.mark.parametrize("modify", [
    lambda e: e.update(action="edited"),
    lambda e: e["repository"].update(full_name="zog144/image-build"),
    lambda e: e["sender"].update(login="foreign"),
    lambda e: e["issue"]["user"].update(login="foreign"),
    lambda e: e["issue"].update(state="closed"),
    lambda e: e["issue"].update(number=0),
])
def test_reject_other_events_and_actors_before_preparation(tmp_path, modify):
    value = event()
    modify(value)
    with pytest.raises(ValueError):
        prepare(tmp_path, value)
    assert not (tmp_path / "prepared.json").exists()


@pytest.mark.parametrize("field,value", [
    ("source", {"repository": "zog144/image-build", "commit": SOURCE}),
    ("request_id", "f" * 32),
    ("origin", {"repository": "zog144/host-deploy",
                "issue_number": 39, "trigger_actor": "zog144"}),
])
def test_issue_cannot_substitute_source_or_request_identity(tmp_path, field, value):
    data = json.loads(json.dumps(event()))
    intent = json.loads(data["issue"]["body"].split("```json\n", 1)[1].split("\n```")[0])
    intent[field] = value
    with pytest.raises(ValueError):
        prepare(tmp_path, event(intent=intent))
    assert not (tmp_path / "prepared.json").exists()


@pytest.mark.parametrize("key,value", [
    ("ZOG_GATEWAY_FONTS_ENABLED", "false"),
    ("ZOG_GATEWAY_ALLOWED_OPERATIONS", '["host.status"]'),
    ("GITHUB_RUN_ATTEMPT", "2"),
    ("GITHUB_TRIGGERING_ACTOR", "foreign"),
    ("GITHUB_REPOSITORY_ID", "999"),
])
def test_missing_admin_or_native_preparation_does_not_create_request(tmp_path,key,value):
    env = config()
    env[key] = value
    with pytest.raises(ValueError):
        prepare(tmp_path, env=env)
    assert not (tmp_path / "prepared.json").exists()


class SQS:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def send_message(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise TimeoutError("uncertain")
        return {"MessageId": "original", "SequenceNumber": "1"}


def test_original_fifo_send_and_redelivery_key_are_stable(tmp_path):
    _, request, _ = prepare(tmp_path)
    client = SQS()
    report = github_dispatch.submit_request(QUEUE, request, client=client)
    assert report["request_id"] == request["request_id"]
    assert report["request_sha256"] == protocol.request_digest(request)
    assert client.calls == [{
        "QueueUrl": QUEUE,
        "MessageBody": protocol.canonical_bytes(request).decode("ascii"),
        "MessageGroupId": WORKSPACE_ID,
        "MessageDeduplicationId": github_dispatch.first_fonts_request_id(39),
    }]
    uncertain = SQS(fail=True)
    with pytest.raises(TimeoutError):
        github_dispatch.submit_request(QUEUE, request, client=uncertain)
    assert len(uncertain.calls) == 1


def test_source_selected_workflow_is_real_host_deploy_issue_trigger():
    script = (TASKC / ".github/workflows/gateway-issue-dispatch.yml").read_text()
    assert "issues:\n    types: [opened]" in script
    assert "ZOG_GATEWAY_FONTS_ENABLED: ${{ vars.ZOG_GATEWAY_FONTS_ENABLED }}" in script
    assert "github.run_attempt == 1" in script
    assert "vars.ZOG_GATEWAY_SUBMIT_ENABLED == 'true'" in script
    assert "github_configuration --event" in script
    assert "github_dispatch submit --request" in script
    assert "id-token: write" in script
    assert "persist-credentials: false" in script
    assert "pull_request_target" not in script
    assert "${{ github.event.issue.body }}" not in script
    template = (TASKC / ".github/ISSUE_TEMPLATE/first-fonts-gateway.md").read_text()
    assert FONTS in template and github_dispatch.ISSUE_MARKER in template
    assert '"source"' not in template and '"request_id"' not in template

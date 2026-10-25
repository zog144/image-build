import json
from pathlib import Path

from zog.image_build.certify_manage_software import PROFILES, validate_lock

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = (
    ROOT
    / "project"
    / "applications"
    / "certify-manage"
    / "cloudflare-dns-01.json"
)


def load():
    return json.loads(DEFINITION.read_text())


def test_cloudflare_application_definition_is_complete_and_valid():
    value = load()
    assert value["schema"] == 1
    assert value["contract"] == "image-build-certify-manage-application-definition-v1"
    assert value["application"] == "certify-manage"
    assert value["profile"] == "cloudflare-dns-01"
    assert value["publication_authorized"] is False

    lock = validate_lock(value["runtime_lock"])
    assert lock["profile"] == "cloudflare-dns-01"
    assert {item["name"] for item in lock["packages"]} == set(
        PROFILES["cloudflare-dns-01"]
    )
    assert lock["certify_manage_revision"] == (
        "8d073ff449557fc82c12eea93e240cdeec1b0fcc"
    )


def test_cloudflare_definition_keeps_http_profile_separate():
    value = load()
    dns = set(PROFILES["cloudflare-dns-01"])
    http = set(PROFILES["http-01"])
    assert dns - http == {
        "certbot-dns-cloudflare",
        "cloudflare",
        "anyio",
        "httpx",
        "httpcore",
        "h11",
        "pydantic",
        "pydantic-core",
        "annotated-types",
        "sniffio",
        "typing-inspection",
    }
    assert value["required_capabilities"]["certbot_plugin"] == "dns-cloudflare"
    assert value["provenance_summary"]["accepted_http_artifact"].startswith(
        "sha256:"
    )
    assert value["provenance_summary"]["accepted_http_view"].startswith(
        "sha256:"
    )


def test_notice_plan_exactly_covers_runtime_lock_destinations():
    value = load()
    lock = validate_lock(value["runtime_lock"])
    expected = {
        notice
        for package in lock["packages"]
        for notice in package["notices"]
    }
    observed = {
        item["destination"] for item in value["notice_copy_plan"]
    }
    assert observed == expected
    assert len(observed) == len(value["notice_copy_plan"])
    assert all(item["source_sha256"] for item in value["notice_copy_plan"])


def test_definition_contains_no_mutable_or_secret_material():
    value = load()
    raw = json.dumps(value, sort_keys=True).lower()
    for forbidden in (
        "api_token=",
        "cloudflare.ini",
        "privkey.pem",
        "fullchain.pem",
        "renewal.conf",
        "/var/lib/zog-certify-manage",
    ):
        assert forbidden not in raw
    assert value["required_capabilities"]["credential_material_in_artifact"] is False


def test_pydantic_core_rights_gate_remains_explicit():
    value = load()
    blockers = value["acceptance"]["retained_blockers"]
    assert len(blockers) == 1
    assert blockers[0]["component"] == "pydantic-core"
    assert blockers[0]["cargo_lock_sha256"] == (
        "c3c27fc600d7dafd149229c6501271dbc5f6b4f7b1bfa116b32e77217c2b5038"
    )

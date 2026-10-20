import shutil
from pathlib import Path

import pytest

from zog.image_build.errors import ImageBuildError
from zog.image_build.post_install_progress_deployment import (
    APPLICATIONS,
    MODULE_BLOBS,
    POLICY_PATH,
    POLICY_SCHEMA,
    SERVICE_UNIT,
    SOCKET_PATH,
    SOCKET_UNIT,
    SOURCE_FILES,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    broker_argv,
    deployment_contract,
    policy,
    reviewed_source_inventory,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "systemd"


def test_native_observer_contract_matches_reviewed_host_welcome_v1():
    assert POLICY_SCHEMA == "zog-host-welcome-image-progress-observer-v1"
    assert POLICY_PATH == "/etc/zog/host-welcome-image-progress-observer.json"
    assert SOCKET_PATH == "/run/host-welcome/image-progress.sock"
    assert SOURCE_REPOSITORY == "zog144/image-build"
    assert SOURCE_REVISION == "fcc12f3db959afe395b1adfb5b0b4dc1f16a3258"
    assert APPLICATIONS == (
        "agreety", "firefox-esr", "greetd", "i3", "xorg-server",
    )
    assert "turbovnc" not in APPLICATIONS
    assert "chromium" not in APPLICATIONS
    assert "weston" not in APPLICATIONS


def test_policy_is_exact_fixed_and_requires_distinct_nonroot_uids():
    value = policy(consumer_uid=1501, producer_uid=1502)
    assert value == {
        "schema": POLICY_SCHEMA,
        "enabled": True,
        "consumer_uid": 1501,
        "producer_uid": 1502,
        "socket": SOCKET_PATH,
        "image_build_source_commit": SOURCE_REVISION,
    }
    assert validate_policy(value) == value
    for bad in (
        dict(value, enabled=False),
        dict(value, socket="/tmp/image-progress.sock"),
        dict(value, image_build_source_commit="0" * 40),
        {**value, "extra": True},
    ):
        with pytest.raises(ImageBuildError):
            validate_policy(bad)
    with pytest.raises(ImageBuildError):
        policy(consumer_uid=1501, producer_uid=1501)
    with pytest.raises(ImageBuildError):
        policy(consumer_uid=0, producer_uid=1502)


def test_broker_argv_fixes_source_allowlist_and_exposes_no_mutation_selector():
    argv = broker_argv(state_dir="/var/lib/zog/image-build-state", consumer_uid=1501)
    assert argv[:2] == ("-m", "zog.image_build.post_install_progress_broker")
    assert argv[-4:] == (
        "--source-repository", SOURCE_REPOSITORY,
        "--source-revision", SOURCE_REVISION,
    )
    assert argv.count("--application") == len(APPLICATIONS)
    for application in APPLICATIONS:
        assert application in argv
    joined = " ".join(argv)
    for forbidden in (
        "--operation", "--pipeline", "--resume", "--cancel", "--publish",
        "--install", "--start", "--socket", "--project",
    ):
        assert forbidden not in joined
    with pytest.raises(ImageBuildError):
        broker_argv(state_dir="../state", consumer_uid=1501)


def test_current_tree_matches_all_reviewed_security_critical_source_blobs(tmp_path):
    observed = reviewed_source_inventory(ROOT)
    assert set(observed) == set(MODULE_BLOBS)
    assert len(observed) == 13
    for module, row in observed.items():
        assert row["git_blob"] == MODULE_BLOBS[module]
        assert len(row["sha256"]) == 64

    copied = tmp_path / "source"
    for relative in SOURCE_FILES.values():
        source = ROOT / relative
        target = copied / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    first = copied / next(iter(SOURCE_FILES.values()))
    first.write_bytes(first.read_bytes() + b"\n# tampered\n")
    with pytest.raises(ImageBuildError, match="differs from reviewed source"):
        reviewed_source_inventory(copied)


def test_reference_systemd_units_are_dedicated_bounded_and_read_only():
    socket_text = (EXAMPLES / (SOCKET_UNIT + ".in")).read_text()
    service_text = (EXAMPLES / (SERVICE_UNIT + ".in")).read_text()

    assert "ListenStream=" + SOCKET_PATH in socket_text
    assert "SocketUser=@WELCOME_UID@" in socket_text
    assert "SocketMode=0600" in socket_text
    assert "DirectoryMode=0711" in socket_text
    assert "Accept=no" in socket_text
    assert "RemoveOnStop=yes" in socket_text

    expected = (
        "-m zog.image_build.post_install_progress_broker "
        "--state-dir @IMAGE_BUILD_STATE@ "
        "--authorized-uid @WELCOME_UID@ "
        "--application agreety "
        "--application firefox-esr "
        "--application greetd "
        "--application i3 "
        "--application xorg-server "
        "--source-repository zog144/image-build "
        "--source-revision " + SOURCE_REVISION
    )
    assert expected in service_text
    assert "User=@IMAGE_BUILD_UID@" in service_text
    assert "Group=@IMAGE_BUILD_GID@" in service_text
    assert "Environment=PYTHONPATH=" in service_text
    assert "RestrictAddressFamilies=AF_UNIX" in service_text
    assert "ReadOnlyPaths=@IMAGE_BUILD_STATE@" in service_text
    assert "ProtectSystem=strict" in service_text
    assert "NoNewPrivileges=yes" in service_text
    assert "CapabilityBoundingSet=" in service_text
    assert "/run/host-welcome/controller-progress.sock" not in service_text
    assert "/run/zog/root-control.sock" not in service_text
    assert "station" not in service_text.lower()


def test_deployment_contract_is_manifest_only_and_never_activation_authority():
    value = deployment_contract(
        state_dir="/var/lib/zog/image-build-state",
        consumer_uid=1501,
        producer_uid=1502,
    )
    assert value["contract"] == "image-build-post-install-progress-native-deployment-v1"
    assert value["applications"] == list(APPLICATIONS)
    assert value["read_only"] is True
    assert value["mutation_authorized"] is False
    assert value["production_activation_authorized"] is False
    assert value["consumer_uid"] != value["producer_uid"]

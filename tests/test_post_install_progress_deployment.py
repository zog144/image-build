import shutil
from pathlib import Path

import pytest

from zog.image_build.errors import ImageBuildError
from zog.image_build.post_install_progress_deployment import (
    APPLICATIONS,
    CERTIFY_MANAGE_APPLICATIONS,
    CERTIFY_MANAGE_PROFILE,
    CERTIFY_MANAGE_SERVICE_TEMPLATE,
    DEFAULT_PROFILE,
    GRAPHICAL_PROFILE,
    MODULE_BLOBS,
    PROFILE_CONTRACT,
    PROFILES,
    POLICY_PATH,
    POLICY_SCHEMA,
    SERVICE_UNIT,
    TRANSPORT_AUTH,
    SOCKET_PATH,
    SOCKET_UNIT,
    SOURCE_FILES,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    broker_argv,
    deployment_contract,
    observer_profile,
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
    assert SOURCE_REVISION == "fe625fd901a62ef3c877a8fbc159e3b4aae7f952"
    assert TRANSPORT_AUTH == "image-build-post-install-progress-linux-credentials-v1"
    assert MODULE_BLOBS["zog.image_build.post_install_progress_broker"] == (
        "997f802492f5bc60724bc6cebff2c045191f2fc1"
    )
    assert MODULE_BLOBS["zog.image_build.post_install_progress"] == (
        "7fa485ca5d3f067999dbe16ff66986315abcf1e3"
    )
    assert DEFAULT_PROFILE == GRAPHICAL_PROFILE
    assert APPLICATIONS == (
        "agreety", "firefox-esr", "greetd", "i3", "xorg-server",
    )
    assert CERTIFY_MANAGE_APPLICATIONS == ("certify-manage",)
    assert set(PROFILES) == {GRAPHICAL_PROFILE, CERTIFY_MANAGE_PROFILE}
    assert "certify-manage" not in APPLICATIONS
    assert not (set(APPLICATIONS) & set(CERTIFY_MANAGE_APPLICATIONS))
    assert "turbovnc" not in APPLICATIONS
    assert "chromium" not in APPLICATIONS
    assert "weston" not in APPLICATIONS


def test_named_profiles_are_exact_disjoint_and_fail_closed():
    graphical = observer_profile(GRAPHICAL_PROFILE)
    assert graphical == {
        "schema": 1,
        "contract": PROFILE_CONTRACT,
        "profile": GRAPHICAL_PROFILE,
        "purpose": "graphical-first-wave",
        "applications": list(APPLICATIONS),
        "service_template": SERVICE_UNIT + ".in",
    }

    certify = observer_profile(CERTIFY_MANAGE_PROFILE)
    assert certify == {
        "schema": 1,
        "contract": PROFILE_CONTRACT,
        "profile": CERTIFY_MANAGE_PROFILE,
        "purpose": "gate-c-non-graphical-certify-manage",
        "applications": ["certify-manage"],
        "service_template": CERTIFY_MANAGE_SERVICE_TEMPLATE,
    }
    assert set(graphical["applications"]).isdisjoint(certify["applications"])
    with pytest.raises(ImageBuildError, match="unsupported"):
        observer_profile("graphical-plus-certbot")
    with pytest.raises(ImageBuildError, match="unsupported"):
        broker_argv(
            state_dir="/var/lib/zog/image-build-state",
            consumer_uid=1501,
            profile="certify-manage,firefox-esr",
        )


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
    argv = broker_argv(
        state_dir="/var/lib/zog/image-build-state",
        consumer_uid=1501,
        profile=GRAPHICAL_PROFILE,
    )
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


def test_certify_manage_broker_profile_is_single_application_and_read_only():
    argv = broker_argv(
        state_dir="/var/lib/zog/image-build-state",
        consumer_uid=1501,
        profile=CERTIFY_MANAGE_PROFILE,
    )
    assert argv.count("--application") == 1
    assert "certify-manage" in argv
    for application in APPLICATIONS:
        assert application not in argv
    joined = " ".join(argv)
    for forbidden in (
        "--operation", "--pipeline", "--resume", "--cancel", "--publish",
        "--install", "--start", "--socket", "--project",
    ):
        assert forbidden not in joined


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
    certify_text = (EXAMPLES / CERTIFY_MANAGE_SERVICE_TEMPLATE).read_text()

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

    certify_expected = (
        "-m zog.image_build.post_install_progress_broker "
        "--state-dir @IMAGE_BUILD_STATE@ "
        "--authorized-uid @WELCOME_UID@ "
        "--application certify-manage "
        "--source-repository zog144/image-build "
        "--source-revision " + SOURCE_REVISION
    )
    assert certify_expected in certify_text
    assert "--application firefox-esr" not in certify_text
    assert "--application greetd" not in certify_text
    assert "RestrictAddressFamilies=AF_UNIX" in certify_text
    assert "ReadOnlyPaths=@IMAGE_BUILD_STATE@" in certify_text
    assert "ProtectSystem=strict" in certify_text
    assert "NoNewPrivileges=yes" in certify_text
    assert "CapabilityBoundingSet=" in certify_text


def test_deployment_contract_is_manifest_only_and_never_activation_authority():
    value = deployment_contract(
        state_dir="/var/lib/zog/image-build-state",
        consumer_uid=1501,
        producer_uid=1502,
        profile=GRAPHICAL_PROFILE,
    )
    assert value["contract"] == "image-build-post-install-progress-native-deployment-v3"
    assert value["transport_auth"] == TRANSPORT_AUTH
    assert value["observer_profile"]["profile"] == GRAPHICAL_PROFILE
    assert value["service_template"] == SERVICE_UNIT + ".in"
    assert value["applications"] == list(APPLICATIONS)
    assert value["read_only"] is True
    assert value["mutation_authorized"] is False
    assert value["production_activation_authorized"] is False
    assert value["consumer_uid"] != value["producer_uid"]


def test_certify_manage_deployment_contract_does_not_widen_graphical_profile():
    value = deployment_contract(
        state_dir="/var/lib/zog/image-build-state",
        consumer_uid=1501,
        producer_uid=1502,
        profile=CERTIFY_MANAGE_PROFILE,
    )
    assert value["contract"] == "image-build-post-install-progress-native-deployment-v3"
    assert value["observer_profile"] == observer_profile(CERTIFY_MANAGE_PROFILE)
    assert value["service_template"] == CERTIFY_MANAGE_SERVICE_TEMPLATE
    assert value["applications"] == ["certify-manage"]
    assert value["broker_argv"].count("--application") == 1
    assert "certify-manage" in value["broker_argv"]
    for application in APPLICATIONS:
        assert application not in value["broker_argv"]
    assert value["read_only"] is True
    assert value["mutation_authorized"] is False
    assert value["production_activation_authorized"] is False

"""Producer-owned native deployment reference for host-welcome image progress.

This module is data/validation only. It does not create accounts, install units,
write /etc, enable services, or grant production activation. host-install owns
those root-controlled operations and must independently resolve live identities
and attest the installed aggregate distribution.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import ImageBuildError

CONTRACT = "image-build-post-install-progress-native-deployment-v3"
TRANSPORT_AUTH = "image-build-post-install-progress-linux-credentials-v1"
PROFILE_CONTRACT = "image-build-post-install-progress-observer-profile-v1"
GRAPHICAL_PROFILE = "graphical-first-wave-v1"
CERTIFY_MANAGE_PROFILE = "certify-manage-gate-c-v1"
DEFAULT_PROFILE = GRAPHICAL_PROFILE
POLICY_SCHEMA = "zog-host-welcome-image-progress-observer-v1"
POLICY_PATH = "/etc/zog/host-welcome-image-progress-observer.json"
SOCKET_PATH = "/run/host-welcome/image-progress.sock"
SOCKET_UNIT = "zog-host-welcome-image-progress.socket"
SERVICE_UNIT = "zog-host-welcome-image-progress.service"

SOURCE_REPOSITORY = "zog144/image-build"
SOURCE_REVISION = "7b653e8be3f89730a52688d71df28513456f9cf3"

APPLICATIONS = (
    "agreety",
    "firefox-esr",
    "greetd",
    "i3",
    "xorg-server",
)
CERTIFY_MANAGE_APPLICATIONS = ("certify-manage",)
CERTIFY_MANAGE_SERVICE_TEMPLATE = (
    "zog-host-welcome-image-progress-certify-manage.service.in"
)
PROFILES = {
    GRAPHICAL_PROFILE: {
        "applications": APPLICATIONS,
        "service_template": SERVICE_UNIT + ".in",
        "purpose": "graphical-first-wave",
    },
    CERTIFY_MANAGE_PROFILE: {
        "applications": CERTIFY_MANAGE_APPLICATIONS,
        "service_template": CERTIFY_MANAGE_SERVICE_TEMPLATE,
        "purpose": "gate-c-non-graphical-certify-manage",
    },
}

MODULE_BLOBS = {
    "zog.image_build.post_install_progress_broker":
        "e7ba6eab10e70e91fc5921bba1eec26f31ace1db",
    "zog.image_build.post_install_progress":
        "f5de79b847b77ab55a0c6bca432a067853628609",
    "zog.image_build.application_software":
        "736cffeb3e42811f93bebb50a0fa9c52e4a7b52b",
    "zog.image_build.application_views":
        "91c144628a9cb5293706fb1114a7063dd30d9291",
    "zog.image_build.build_views":
        "7581de78d0d70dbfa1a1f7a2e308cd43fd3bec1c",
    "zog.image_build.errors":
        "dc80cc8438eab55c5438172328ae778e914f506a",
    "zog.image_build.filesystem":
        "1f6c1fa8628118de5ec2e6c727fd6b725498a99f",
    "zog.image_build.metadata":
        "79238579b11e87070886b2fd0125a186a94fd29e",
    "zog.image_build.engine":
        "c65a948ae027850247dee6da8999f121ee3397a4",
    "zog.image_build.rootfs_compatibility":
        "3adbef4cdcef29a89bdc309eab30aeb40be167e2",
    "zog.image_build.artifact_observations":
        "5ca72fc4e3f04a921860ad99853c1981ecf7c188",
    "zog.image_build.runtime_facilities":
        "651f5ceb35f40aae5831ead08d97495575740dff",
    "zog.image_build.application_data_targets":
        "94b5e69dcbe5ad30c4e98787fc217910a38e074e",
}
SOURCE_FILES = {
    module: "src/" + module.replace(".", "/") + ".py"
    for module in MODULE_BLOBS
}


def _git_blob_sha(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _numeric_uid(value, label):
    if type(value) is not int or not 1 <= value < 2**31:
        raise ImageBuildError("invalid " + label)
    return value


def _absolute_path(value, label):
    if type(value) is not str:
        raise ImageBuildError("invalid " + label)
    path = Path(value)
    if (
        not path.is_absolute()
        or value != str(path)
        or ".." in path.parts
        or "." in path.parts
        or value == "/"
    ):
        raise ImageBuildError("invalid " + label)
    return value


def observer_profile(value=DEFAULT_PROFILE):
    """Return one reviewed fixed broker allowlist profile.

    Profiles are deliberately disjoint.  In particular, the Gate C Certbot
    profile does not widen the graphical first-wave service and cannot be
    combined with it by callers.
    """
    if not isinstance(value, str) or value not in PROFILES:
        raise ImageBuildError("unsupported image progress observer profile")
    profile = PROFILES[value]
    return {
        "schema": 1,
        "contract": PROFILE_CONTRACT,
        "profile": value,
        "purpose": profile["purpose"],
        "applications": list(profile["applications"]),
        "service_template": profile["service_template"],
    }


def policy(*, consumer_uid, producer_uid):
    """Return the exact consumer-visible root policy body."""
    consumer_uid = _numeric_uid(consumer_uid, "host-welcome consumer UID")
    producer_uid = _numeric_uid(producer_uid, "image-build producer UID")
    if consumer_uid == producer_uid:
        raise ImageBuildError("observer producer and consumer UIDs must differ")
    return {
        "schema": POLICY_SCHEMA,
        "enabled": True,
        "consumer_uid": consumer_uid,
        "producer_uid": producer_uid,
        "socket": SOCKET_PATH,
        "image_build_source_commit": SOURCE_REVISION,
    }


def validate_policy(value):
    """Validate the exact v1 policy shared with the reviewed host-welcome consumer."""
    if type(value) is not dict or set(value) != {
        "schema", "enabled", "consumer_uid", "producer_uid", "socket",
        "image_build_source_commit",
    }:
        raise ImageBuildError("invalid host-welcome image progress observer policy")
    expected = policy(
        consumer_uid=value.get("consumer_uid"),
        producer_uid=value.get("producer_uid"),
    )
    if value != expected:
        raise ImageBuildError("unreviewed host-welcome image progress observer policy")
    return dict(value)


def broker_argv(*, state_dir, consumer_uid, profile=DEFAULT_PROFILE):
    """Return the immutable broker argv suffix for one reviewed observer profile."""
    state_dir = _absolute_path(state_dir, "image-build state directory")
    consumer_uid = _numeric_uid(consumer_uid, "host-welcome consumer UID")
    selected = observer_profile(profile)
    result = [
        "-m", "zog.image_build.post_install_progress_broker",
        "--state-dir", state_dir,
        "--authorized-uid", str(consumer_uid),
    ]
    for application in selected["applications"]:
        result.extend(("--application", application))
    result.extend((
        "--source-repository", SOURCE_REPOSITORY,
        "--source-revision", SOURCE_REVISION,
    ))
    return tuple(result)


def reviewed_source_inventory(source_root):
    """Verify the security-critical projection/broker dependency bytes."""
    root = Path(source_root)
    observed = {}
    for module, relative in SOURCE_FILES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ImageBuildError("reviewed image-build observer source missing or redirected")
        data = path.read_bytes()
        if not 0 < len(data) <= 2_000_000:
            raise ImageBuildError("reviewed image-build observer source exceeds size bound")
        git_blob = _git_blob_sha(data)
        if git_blob != MODULE_BLOBS[module]:
            raise ImageBuildError(
                "image-build observer dependency differs from reviewed source: " + module
            )
        observed[module] = {
            "git_blob": git_blob,
            "sha256": hashlib.sha256(data).hexdigest(),
            "path": relative,
        }
    return observed


def deployment_contract(*, state_dir, consumer_uid, producer_uid,
                        profile=DEFAULT_PROFILE):
    """Return producer-owned immutable facts for a host-install staging manifest."""
    validate_policy(policy(consumer_uid=consumer_uid, producer_uid=producer_uid))
    selected = observer_profile(profile)
    return {
        "schema": 1,
        "contract": CONTRACT,
        "observer_profile": selected,
        "policy_path": POLICY_PATH,
        "socket_path": SOCKET_PATH,
        "socket_unit": SOCKET_UNIT,
        "service_unit": SERVICE_UNIT,
        "service_template": selected["service_template"],
        "source_repository": SOURCE_REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "transport_auth": TRANSPORT_AUTH,
        "applications": list(selected["applications"]),
        "state_dir": _absolute_path(state_dir, "image-build state directory"),
        "consumer_uid": consumer_uid,
        "producer_uid": producer_uid,
        "broker_argv": list(broker_argv(
            state_dir=state_dir,
            consumer_uid=consumer_uid,
            profile=profile,
        )),
        "read_only": True,
        "mutation_authorized": False,
        "production_activation_authorized": False,
    }

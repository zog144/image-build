"""Versioned named verification outcomes, separate from command/log ownership."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from .errors import ImageBuildError
from .filesystem import write_json
from .metadata import identity
from .trace_records import sanitize

V1_SCHEMA = "image-build-verification-observation-v1"
V2_SCHEMA = "image-build-verification-observation-v2"
ENVIRONMENT_SCHEMA = "image-build-verification-environment-v1"
SCHEMA = V1_SCHEMA
_CONTROLLER_MODE = "box-control-build-job-v1"


def _copy(value, label):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
        return json.loads(raw)
    except (TypeError, ValueError) as error:
        raise ImageBuildError("invalid verification " + label) from error


def _digest(value, label):
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
        or any(c not in "0123456789abcdef" for c in value[7:])
    ):
        raise ImageBuildError("invalid verification " + label)
    return value


def _number(value, label, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ImageBuildError("invalid verification " + label)
    if (positive and value <= 0) or (not positive and value < 0):
        raise ImageBuildError("invalid verification " + label)
    return value


def _safe_json(value, label):
    value = _copy(value, label)
    if sanitize(value) != value:
        raise ImageBuildError(
            "verification execution environment must not contain credentials"
        )
    return value


def _request_dict(request):
    if is_dataclass(request):
        request = asdict(request)
    if not isinstance(request, dict):
        raise ImageBuildError("verification execution request must be an object")
    # Select before canonicalization. Host root/source/output locators and command
    # argv are deliberately not execution-environment identity and may contain
    # Path objects in the typed runner request.
    relevant = {
        key: request[key]
        for key in (
            "environment",
            "working_directory",
            "timeout_seconds",
            "execution_timeout_seconds",
            "read_only_root",
            "network_access",
            "execution_user_id",
            "execution_group_id",
            "startup_timeout_seconds",
            "termination_grace_seconds",
            "resource_limits",
            "device_profile",
        )
        if key in request
    }
    return _copy(relevant, "execution request")


def _duration(value, label):
    value = _number(value, label, positive=True)
    if type(value) is int or value.is_integer():
        return str(int(value))
    return repr(value)


def execution_environment(request, controller):
    """Normalize only execution-relevant facts; exclude command, locators and IDs."""
    request = _request_dict(request)
    if not isinstance(controller, dict):
        raise ImageBuildError(
            "verification execution environment requires controller configuration"
        )
    controller = _copy(controller, "controller configuration")

    required_request = {
        "environment",
        "working_directory",
        "read_only_root",
        "network_access",
    }
    if not required_request <= set(request):
        raise ImageBuildError(
            "verification execution request lacks environment facts"
        )
    timeout = request.get(
        "timeout_seconds", request.get("execution_timeout_seconds")
    )
    if timeout is None:
        raise ImageBuildError(
            "verification execution request lacks timeout"
        )

    def configured(name):
        value = request.get(name, controller.get(name))
        if value is None:
            raise ImageBuildError(
                "verification controller configuration lacks " + name
            )
        return value

    environment = request["environment"]
    if (
        not isinstance(environment, dict)
        or any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or not key
            or "\x00" in key
            or "\x00" in value
            for key, value in environment.items()
        )
    ):
        raise ImageBuildError(
            "invalid verification process environment"
        )
    working_directory = request["working_directory"]
    if (
        not isinstance(working_directory, str)
        or not working_directory.startswith("/")
        or "\x00" in working_directory
    ):
        raise ImageBuildError(
            "invalid verification working directory"
        )
    if type(request["read_only_root"]) is not bool:
        raise ImageBuildError(
            "invalid verification read-only-root policy"
        )
    if type(request["network_access"]) is not bool:
        raise ImageBuildError(
            "invalid verification network policy"
        )

    user = configured("execution_user_id")
    group = configured("execution_group_id")
    if (
        type(user) is not int
        or type(group) is not int
        or not 0 < user < 2**31
        or not 0 < group < 2**31
    ):
        raise ImageBuildError(
            "verification execution requires explicit nonzero UID/GID"
        )
    resource_limits = configured("resource_limits")
    if (
        not isinstance(resource_limits, dict)
        or not resource_limits
        or any(
            not isinstance(key, str)
            or not key
            or type(value) is not int
            or value <= 0
            for key, value in resource_limits.items()
        )
    ):
        raise ImageBuildError(
            "verification execution requires positive resource limits"
        )
    device_profile = controller.get(
        "device_profile", request.get("device_profile")
    )
    device_digest = (
        None
        if device_profile is None
        else "sha256:" + identity(_safe_json(device_profile, "device profile"))
    )

    # build-record owns the portable descriptor domain names. Numeric limits that
    # may exceed interoperable JSON integer bounds are represented as decimal
    # strings; execution UID/GID remain bounded integers.
    descriptor = {
        "isolation": {
            "mount_namespace": True,
            "user_namespace": False,
            "root_read_only": request["read_only_root"],
            "device_profile_digest": device_digest,
        },
        "user": {
            "uid": user,
            "gid": group,
        },
        "root": {
            "mode": "prepared-rootfs",
            "writable_output": "separate-workspace",
        },
        "network": {
            "mode": (
                "host"
                if request["network_access"]
                else "none"
            ),
        },
        "timeout": {
            "execution_seconds": _duration(
                timeout, "execution timeout"
            ),
            "startup_seconds": _duration(
                configured("startup_timeout_seconds"),
                "startup timeout",
            ),
            "termination_grace_seconds": _duration(
                configured("termination_grace_seconds"),
                "termination grace",
            ),
        },
        "runtime": {
            "executor": _CONTROLLER_MODE,
            "working_directory": working_directory,
            "environment": [
                key + "=" + environment[key]
                for key in sorted(environment)
            ],
            "resource_limits": {
                key: str(resource_limits[key])
                for key in sorted(resource_limits)
            },
        },
    }
    descriptor = _safe_json(
        descriptor, "execution environment"
    )
    digest = "sha256:" + identity(descriptor)
    return {
        "contract": ENVIRONMENT_SCHEMA,
        "digest": digest,
        "descriptor": descriptor,
    }


def planned_execution_environment(builder, root, source, output, command):
    """Freeze the environment that BoxControlRunner will request before submission."""
    make_request = getattr(builder.runner, "build_request", None)
    execute = getattr(builder.runner, "execute", None)
    if not callable(make_request) or not hasattr(execute, "configuration"):
        raise ImageBuildError(
            "verification environment v2 requires configured box-control execution"
        )
    request = make_request(root, source, output, command, {})
    return execution_environment(request, execute.configuration())


def producer_policy_digest(policy):
    return "sha256:" + identity(_copy(policy, "producer policy"))


def _common(*, schema, check_id, definition_digest, subject, attempt_id,
            sequence, outcome, execution, evidence):
    value = dict(
        schema=schema,
        check_id=check_id,
        definition_digest=definition_digest,
        subject=subject,
        attempt_id=attempt_id,
        sequence=sequence,
        outcome=outcome,
        execution=execution,
        evidence=evidence,
        granularity="command",
        timing={
            "started_at": None,
            "finished_at": None,
            "observed_at": None,
        },
        producer={"name": "image-build", "contract": schema},
    )
    return value


def observation(*, check_id, definition_digest, subject, attempt_id, sequence,
                outcome, execution, environment_digest, evidence):
    """Construct legacy v1 evidence without changing its historical semantics."""
    value = _common(
        schema=V1_SCHEMA,
        check_id=check_id,
        definition_digest=definition_digest,
        subject=subject,
        attempt_id=attempt_id,
        sequence=sequence,
        outcome=outcome,
        execution=execution,
        evidence=evidence,
    )
    value["environment_digest"] = environment_digest
    value["id"] = "sha256:" + identity(value)
    validate(value)
    return value


def observation_v2(*, check_id, definition_digest, subject, attempt_id, sequence,
                   outcome, execution, execution_environment,
                   producer_policy_digest, evidence):
    value = _common(
        schema=V2_SCHEMA,
        check_id=check_id,
        definition_digest=definition_digest,
        subject=subject,
        attempt_id=attempt_id,
        sequence=sequence,
        outcome=outcome,
        execution=execution,
        evidence=evidence,
    )
    validate_execution_environment(execution_environment)
    value["execution_environment"] = _copy(
        execution_environment, "execution environment"
    )
    value["producer_policy_digest"] = producer_policy_digest
    value["id"] = "sha256:" + identity(value)
    validate(value)
    return value


def validate_execution_environment(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"contract", "digest", "descriptor"}
        or value.get("contract") != ENVIRONMENT_SCHEMA
        or not isinstance(value.get("descriptor"), dict)
    ):
        raise ImageBuildError(
            "unsupported verification execution environment"
        )
    descriptor = _safe_json(
        value["descriptor"], "execution environment descriptor"
    )
    if set(descriptor) != {
        "isolation", "user", "root", "network", "timeout", "runtime"
    }:
        raise ImageBuildError(
            "verification execution environment descriptor fields differ"
        )
    for domain in descriptor.values():
        if not isinstance(domain, dict):
            raise ImageBuildError(
                "verification execution environment domains must be objects"
            )
    isolation = descriptor["isolation"]
    if (
        set(isolation)
        != {
            "mount_namespace",
            "user_namespace",
            "root_read_only",
            "device_profile_digest",
        }
        or isolation["mount_namespace"] is not True
        or isolation["user_namespace"] is not False
        or type(isolation["root_read_only"]) is not bool
        or (
            isolation["device_profile_digest"] is not None
            and _digest(
                isolation["device_profile_digest"],
                "device profile digest",
            )
            is None
        )
    ):
        raise ImageBuildError(
            "invalid verification isolation descriptor"
        )
    user = descriptor["user"]
    if (
        set(user) != {"uid", "gid"}
        or type(user["uid"]) is not int
        or type(user["gid"]) is not int
        or not 0 < user["uid"] < 2**31
        or not 0 < user["gid"] < 2**31
    ):
        raise ImageBuildError(
            "invalid verification user descriptor"
        )
    if descriptor["root"] != {
        "mode": "prepared-rootfs",
        "writable_output": "separate-workspace",
    }:
        raise ImageBuildError(
            "invalid verification root descriptor"
        )
    network = descriptor["network"]
    if (
        set(network) != {"mode"}
        or network["mode"] not in {"host", "none"}
    ):
        raise ImageBuildError(
            "invalid verification network descriptor"
        )
    timeout = descriptor["timeout"]
    if (
        set(timeout)
        != {
            "execution_seconds",
            "startup_seconds",
            "termination_grace_seconds",
        }
        or any(
            not isinstance(timeout[key], str)
            or not timeout[key]
            for key in timeout
        )
    ):
        raise ImageBuildError(
            "invalid verification timeout descriptor"
        )
    runtime = descriptor["runtime"]
    if (
        set(runtime)
        != {
            "executor",
            "working_directory",
            "environment",
            "resource_limits",
        }
        or runtime["executor"] != _CONTROLLER_MODE
        or not isinstance(runtime["working_directory"], str)
        or not runtime["working_directory"].startswith("/")
        or not isinstance(runtime["environment"], list)
        or any(
            not isinstance(item, str)
            or "=" not in item
            for item in runtime["environment"]
        )
        or runtime["environment"] != sorted(runtime["environment"])
        or not isinstance(runtime["resource_limits"], dict)
        or not runtime["resource_limits"]
        or any(
            not isinstance(key, str)
            or not isinstance(child, str)
            or not child
            for key, child in runtime["resource_limits"].items()
        )
    ):
        raise ImageBuildError(
            "invalid verification runtime descriptor"
        )
    _digest(value["digest"], "execution environment digest")
    if value["digest"] != "sha256:" + identity(descriptor):
        raise ImageBuildError(
            "verification execution environment digest differs"
        )
    return value


def _validate_common(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        raise ImageBuildError("unsupported verification observation")
    if value["id"] != "sha256:" + identity(
        {k: v for k, v in value.items() if k != "id"}
    ):
        raise ImageBuildError(
            "verification observation identity differs"
        )
    if value["outcome"] not in {"PASS", "FAIL", "ERROR", "SKIP"}:
        raise ImageBuildError("invalid verification outcome")
    if type(value["sequence"]) is not int or value["sequence"] < 0:
        raise ImageBuildError("invalid verification sequence")
    for key in ("check_id", "attempt_id"):
        if not isinstance(value[key], str) or not value[key]:
            raise ImageBuildError(
                "verification identity missing: " + key
            )
    _digest(value["definition_digest"], "definition digest")
    if (
        not isinstance(value["subject"], dict)
        or not value["subject"]
        or not value["evidence"]
    ):
        raise ImageBuildError(
            "verification subject/evidence missing"
        )
    producer = value.get("producer")
    if producer != {
        "name": "image-build",
        "contract": value["schema"],
    }:
        raise ImageBuildError(
            "verification producer contract differs"
        )


def validate(value):
    schema = value.get("schema") if isinstance(value, dict) else None
    common = {
        "schema",
        "id",
        "check_id",
        "definition_digest",
        "subject",
        "attempt_id",
        "sequence",
        "outcome",
        "execution",
        "evidence",
        "granularity",
        "timing",
        "producer",
    }
    if schema == V1_SCHEMA:
        fields = common | {"environment_digest"}
        _validate_common(value, fields)
        _digest(
            value["environment_digest"],
            "environment digest",
        )
    elif schema == V2_SCHEMA:
        fields = common | {
            "execution_environment",
            "producer_policy_digest",
        }
        _validate_common(value, fields)
        validate_execution_environment(
            value["execution_environment"]
        )
        _digest(
            value["producer_policy_digest"],
            "producer policy digest",
        )
    else:
        raise ImageBuildError(
            "unsupported verification observation"
        )
    if value.get("granularity") != "command":
        raise ImageBuildError(
            "invalid verification granularity"
        )
    timing = value.get("timing")
    if (
        not isinstance(timing, dict)
        or set(timing)
        != {"started_at", "finished_at", "observed_at"}
    ):
        raise ImageBuildError(
            "invalid verification timing"
        )
    return value


def _v2_binding(prepared):
    return (
        prepared.get("verification_observation_contract")
        == V2_SCHEMA
    )


def capture(builder, folder, prepared, index, error=None):
    """Called after a named installed command. Never turn pending into a result."""
    binding = prepared["binding"]
    if (
        not isinstance(binding, dict)
        or binding.get("verification_report_contract")
        != "image-build-installed-verification-v1"
    ):
        return None
    p = builder.provenance
    if p is None:
        return None
    folder = Path(folder)
    checkpoint = folder / f"command-{index}.execution.json"
    actual_environment = None
    if checkpoint.exists():
        raw = json.loads(checkpoint.read_text())
        request = raw.get("request", {})
        if (
            request.get("command") != prepared["commands"][index]
            or request.get("root")
            != str((folder / "root").resolve())
            or request.get("source")
            != str((folder / "source").resolve())
            or request.get("output")
            != str((folder / "output").resolve())
            or raw.get("policy")
            != builder._policy().get("controller")
        ):
            raise ImageBuildError(
                "verification completion binding differs"
            )
        if _v2_binding(prepared):
            actual_environment = execution_environment(
                request, raw.get("policy")
            )
        if (
            raw.get("cleanup_complete") is not True
            or type(raw.get("exit_code")) is not int
        ):
            return None
        outcome = (
            "PASS" if raw["exit_code"] == 0 else "FAIL"
        )
        execution = {
            key: raw[key]
            for key in (
                "runtime_id",
                "invocation_id",
                "journal_reference",
                "exit_code",
            )
        }
    else:
        raw = getattr(error, "record", {})
        if (
            raw.get("state") != "completed"
            or raw.get("outcome")
            not in {
                "nonzero-exit",
                "signal",
                "timeout",
                "fault",
                "cancelled",
            }
        ):
            return None
        controller = folder / f"command-{index}.controller.json"
        if not controller.exists():
            return None
        saved = json.loads(controller.read_text())
        if (
            saved.get("job_id") != raw.get("job_id")
            or saved.get("request_id")
            != raw.get("request_id")
        ):
            raise ImageBuildError(
                "verification failure job identity differs"
            )
        if _v2_binding(prepared):
            retained = saved.get("binding")
            if (
                not isinstance(retained, dict)
                or set(retained) != {"request", "configuration"}
            ):
                raise ImageBuildError(
                    "verification failure lacks frozen execution binding"
                )
            request = retained["request"]
            if (
                request.get("command")
                != prepared["commands"][index]
                or request.get("root")
                != str((folder / "root").resolve())
                or request.get("source")
                != str((folder / "source").resolve())
                or request.get("output")
                != str((folder / "output").resolve())
            ):
                raise ImageBuildError(
                    "verification failure execution binding differs"
                )
            actual_environment = execution_environment(
                request, retained["configuration"]
            )
        outcome = (
            "FAIL"
            if raw["outcome"] == "nonzero-exit"
            else "ERROR"
        )
        execution = {
            key: raw.get(key)
            for key in (
                "job_id",
                "invocation_id",
                "journal_reference",
                "exit_code",
                "outcome",
            )
        }
    name = binding.get(
        "verification_check", "installed-trust"
    )
    common = dict(
        check_id=(
            "image-build/"
            + name
            + "/command/"
            + str(index)
        ),
        definition_digest=(
            "sha256:"
            + identity(prepared["commands"][index])
        ),
        subject={
            "kind": "generation-candidate",
            "generation_id": json.dumps(
                [
                    p.host_id,
                    p.project_id,
                    identity(binding),
                ],
                separators=(",", ":"),
            ),
            "root_inventory_digest": (
                "sha256:" + identity(prepared["root"])
            ),
        },
        attempt_id=json.dumps(
            [p.host_id, p.project_id, folder.name],
            separators=(",", ":"),
        ),
        sequence=index,
        outcome=outcome,
        execution=dict(host_id=p.host_id, **execution),
        evidence=[
            {
                "kind": "execution-checkpoint",
                "digest": "sha256:" + identity(raw),
            },
            {
                "kind": "build-trace",
                "host_id": p.host_id,
                "build_id": "attempt:" + folder.name,
            },
        ],
    )
    if _v2_binding(prepared):
        environments = prepared.get("execution_environments")
        if (
            not isinstance(environments, list)
            or len(environments) != len(prepared["commands"])
        ):
            raise ImageBuildError(
                "verification v2 frozen environments differ"
            )
        expected_environment = environments[index]
        validate_execution_environment(expected_environment)
        if actual_environment != expected_environment:
            raise ImageBuildError(
                "verification execution environment differs from frozen descriptor"
            )
        frozen_policy = prepared.get(
            "producer_policy_digest"
        )
        _digest(
            frozen_policy, "producer policy digest"
        )
        owner_policy = binding.get("execution_policy")
        if (
            owner_policy is None
            or producer_policy_digest(owner_policy)
            != frozen_policy
        ):
            raise ImageBuildError(
                "verification producer policy differs from frozen owner binding"
            )
        value = observation_v2(
            **common,
            execution_environment=expected_environment,
            producer_policy_digest=frozen_policy,
        )
    else:
        # Historical v1 semantics intentionally remain the broad current policy
        # hash. Existing prepared operations are never retrofitted to v2.
        value = observation(
            **common,
            environment_digest=(
                "sha256:" + identity(builder._policy())
            ),
        )

    intent = (
        folder
        / "verification-observations"
        / f"{index}.prepared.json"
    )
    if intent.exists():
        saved = json.loads(intent.read_text())
        validate(saved)
        comparable = dict(
            saved,
            timing=dict(
                saved["timing"], observed_at=None
            ),
        )
        comparable["id"] = "sha256:" + identity(
            {
                k: v
                for k, v in comparable.items()
                if k != "id"
            }
        )
        if comparable != value:
            raise ImageBuildError(
                "immutable verification observation changed"
            )
        value = saved
    else:
        value["timing"]["observed_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        value["id"] = "sha256:" + identity(
            {
                k: v
                for k, v in value.items()
                if k != "id"
            }
        )
        write_json(intent, value)

    descriptor = p._bytes(
        "verification-observation.json", value
    )
    path = (
        folder
        / "verification-observations"
        / f"{index}.json"
    )
    if (
        path.exists()
        and json.loads(path.read_text()) != descriptor
    ):
        raise ImageBuildError(
            "immutable verification observation changed"
        )
    write_json(path, descriptor)
    index_path = (
        p.root
        / "observation-index"
        / ("sha256-" + identity(binding))
        / (value["id"][7:] + ".json")
    )
    write_json(index_path, descriptor)
    return descriptor

#!/usr/bin/env python3
"""Read-only Resident B source inspection, separate from frozen Boot A audit.

A PASS only means the reviewed *missing/present source inventory* still
matches. It can never authorize a generation, install, credential or boot.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "project/package"
AUDIT = ROOT / "project/host/resident-b-source-prerequisite-audit-2026-11-03.json"

SOURCE_STAGE = {
    "python-final": "python", "openssl-final": "openssl",
    "sqlite-final": "sqlite", "dbus-final": "dbus",
    "iproute2-final": "iproute2", "systemd-final": "systemd",
    "host-install-final": "host-install",
    "host-discover-final": "host-discover",
    "host-identify-final": "host-identify",
    "python-cryptography-final": "python-cryptography",
    "ca-certificates-final": "ca-certificates",
}
FINDING_STATUS = {
    "PYTHON_VERSION_DECISION": "HOLD",
    "PYTHON_SSL_SQLITE_STAGE_EDGES": "GAP",
    "PYTHON_SSL_SQLITE_INSTALLED": "GAP",
    "SYSTEMD_NETWORK_UTILITIES": "SOURCE_OUTPUT_DECLARED_NATIVE_UNVERIFIED",
    "CONTROL_CLI_OUTPUTS": "SOURCE_OUTPUT_DECLARED_NATIVE_UNVERIFIED",
    "ROOT_BOX_CONTROL_PACKAGES": "GAP",
    "CREDENTIAL_RUNTIME_EDGES": "GAP",
    "DBUS_RUNTIME_IDENTITY": "NATIVE_UNVERIFIED",
    "IPROUTE2_RUNTIME_LINKAGE": "NATIVE_UNVERIFIED",
    "OPENSSL_SQLITE_RUNTIME_LINKAGE": "NATIVE_UNVERIFIED",
    "RESIDENT_B_GENERATION": "NATIVE_UNVERIFIED",
}
MISSING_REQUIRED_OUTPUTS = {
    "python-final": frozenset((
        "usr/bin/python3.12", "usr/lib/libpython3.12.so.1.0")),
}
FIXED_REQUIRED_OUTPUTS = {
    "systemd-final": frozenset(("usr/bin/networkctl", "usr/bin/resolvectl")),
    "host-install-final": frozenset(("usr/bin/host-install",)),
    "host-discover-final": frozenset((
        "usr/bin/host-discover", "usr/bin/host-discover-recovery",
        "usr/bin/host-discover-supervisor")),
}
REQUIRED_PYTHON_MODULES = frozenset((
    "MODULE__SSL_STATE=yes", "MODULE__SQLITE3_STATE=yes",
    "test_ssl", "test_sqlite3",
))
SAFE_FLAGS = {
    "systemd": ("-Dnetworkd=true", "-Dresolve=true", "-Dtimesyncd=true"),
    "dbus": ("-Dsystemd=enabled", "-Ddbus_user=messagebus"),
    "iproute2": ("--libbpf_force=off",),
}
READONLY_FIELDS = frozenset((
    "schema", "reviewed_boot_a_pr10_head",
    "reviewed_host_install_boot_contract", "scope", "source_status",
    "native_generation_id", "installed_artifact_receipts",
    "build_submitted", "credential_delivery_enabled",
    "certificate_dependency", "production_source_selection_changed",
    "requested_python_version", "authored_python_upstream_version",
    "authored_python_source_package_path", "python_build_checks",
    "source_manifest_observed", "direct_runtime_dependencies_observed",
    "uncovered_stage_requirements", "admission", "boot_a_audit_unchanged",
    "required_future_evidence",
))


def literal(path):
    return ast.literal_eval(Path(path).read_text())


def inspect(record, *, stages=None, dependencies=None, upstream=None,
            build_scripts=None, existing_packages=None):
    if type(record) is not dict or set(record) != READONLY_FIELDS:
        raise ValueError("Resident B review fields changed or an approval field was added")
    if (record["schema"] != "zog-resident-b-source-prerequisites-v1"
            or record["reviewed_boot_a_pr10_head"] !=
            "e982c61df1a31e650dae2b40ba9d8758ece7913b"
            or record["reviewed_host_install_boot_contract"] !=
            "cf3ca569d6109ab75e5082dd4109698680155984"
            or record["scope"] != "resident-b-only-no-boot-a-contract-change"
            or record["source_status"] != "GAPS_RECORDED_NOT_READY"
            or record["admission"] != "NO_GO_RESIDENT_B"):
        raise ValueError("Resident B original source/acceptance boundary changed")
    if (record["native_generation_id"] is not None
            or record["installed_artifact_receipts"] is not None
            or record["boot_a_audit_unchanged"] is not True
            or any(record[key] is not False for key in (
                "build_submitted", "credential_delivery_enabled",
                "certificate_dependency", "production_source_selection_changed"))):
        raise ValueError("source review cannot promote native generation or authority")

    if (record["requested_python_version"] != "3.12"
            or record["authored_python_upstream_version"] != "3.15.0rc2"
            or record["authored_python_source_package_path"] !=
            "project/package/python/stages/final/upstream.py"):
        raise ValueError("Python 3.12 requested versus selected 3.15 source gap hidden")

    source_upstream = upstream if upstream is not None else literal(
        ROOT / record["authored_python_source_package_path"])
    if source_upstream.get("version") != record["authored_python_upstream_version"]:
        raise ValueError("reviewed Python source pin changed")
    if type(record["required_future_evidence"]) is not list or len(
            record["required_future_evidence"]) != 7:
        raise ValueError("native Resident B obligations omitted")

    stages = stages if stages is not None else {
        stage: literal(PKG / name / "stages/final/produce-manifest.py")
        for stage, name in SOURCE_STAGE.items()}
    dependencies = dependencies if dependencies is not None else {
        stage: literal(PKG / name / "stages/final/dependencies.py")
        for stage, name in SOURCE_STAGE.items()}
    if set(stages) != set(SOURCE_STAGE) or set(dependencies) != set(SOURCE_STAGE):
        raise ValueError("unknown or omitted Resident B stage")
    expected_manifest = record["source_manifest_observed"]
    expected_deps = record["direct_runtime_dependencies_observed"]
    if set(expected_manifest) != set(SOURCE_STAGE) or set(expected_deps) != set(SOURCE_STAGE):
        raise ValueError("stage inventory omitted or substituted")
    for key in SOURCE_STAGE:
        required = stages[key]["required"]
        observed = expected_manifest[key]
        if (type(observed) is not list or len(set(observed)) != len(observed)
                or not set(observed).issubset(required)):
            raise ValueError("observed source output missing: " + key)
        if dependencies[key].get("runtime") != expected_deps[key]:
            raise ValueError("direct declared runtime stage dependencies drifted: " + key)
        if type(dependencies[key].get("build")) is not list:
            raise ValueError("missing recorded build edges: " + key)
    for key, fixed in FIXED_REQUIRED_OUTPUTS.items():
        if not fixed.issubset(set(stages[key]["required"])):
            raise ValueError("required Resident B CLI output removed: " + key)
        if not fixed.issubset(set(expected_manifest[key])):
            raise ValueError("reviewed Resident B CLI source record omitted output: " + key)
    for key, missing in MISSING_REQUIRED_OUTPUTS.items():
        if not missing.isdisjoint(stages[key]["required"]):
            raise ValueError("unreviewed Resident B source output was added: " + key)
    if ({"openssl-final", "sqlite-final"} &
            set(dependencies["python-final"]["build"] +
                dependencies["python-final"]["runtime"])):
        raise ValueError("Python predecessor graph changed; re-audit required")
    for key in ("host-identify-final", "host-install-final",
                "python-cryptography-final"):
        if dependencies[key]["runtime"]:
            raise ValueError("reviewed controller source edges changed: " + key)
    existing_packages = (existing_packages if existing_packages is not None
                         else {p.name for p in PKG.iterdir() if p.is_dir()})
    if "root-control" in existing_packages or "box-control" in existing_packages:
        raise ValueError("reviewed controller packaging gap changed; re-audit required")

    build_scripts = build_scripts if build_scripts is not None else {
        name: (PKG / name / "stages/final/build.py").read_text()
        for name in ("python", "systemd", "dbus", "iproute2")}
    if set(build_scripts) != {"python", "systemd", "dbus", "iproute2"}:
        raise ValueError("Resident B source build recipe missing")
    if (set(record["python_build_checks"]) != REQUIRED_PYTHON_MODULES
            or any(term not in build_scripts["python"]
                   for term in REQUIRED_PYTHON_MODULES)
            or "Python-3.15.0rc2" not in build_scripts["python"]):
        raise ValueError("Python SSL and SQLite source feature checks missing")
    for name, flags in SAFE_FLAGS.items():
        for flag in flags:
            if flag not in build_scripts[name]:
                raise ValueError("required Resident B source feature flag missing: "+name)

    findings = record["uncovered_stage_requirements"]
    if (type(findings) is not list or len(findings) != len(FINDING_STATUS)
            or len({x.get("code") for x in findings if type(x) is dict}) != len(findings)
            or {x.get("code"): x.get("status") for x in findings} != FINDING_STATUS
            or any(set(x) != {"code", "finding", "status"}
                   or not isinstance(x["finding"], str) or len(x["finding"]) < 35
                   for x in findings)):
        raise ValueError("known Resident B source gaps were concealed or approved")
    return {
        "inventory": "PASS_EXACT_SOURCE_GAPS_RETAINED",
        "authored_python": source_upstream["version"],
        "requested_python": record["requested_python_version"],
        "unresolved": len(FINDING_STATUS),
        "resident_b": "NO_GO",
        "native_generation": "UNVERIFIED",
        "boot_a": "UNCHANGED_NOT_ACCEPTED",
    }


if __name__ == "__main__":
    print(json.dumps(inspect(json.loads(AUDIT.read_text())), sort_keys=True))

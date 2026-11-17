#!/usr/bin/env python3
"""Verify one Resident B source candidate; never select an installed generation.

Reuses the existing PR12/PR14/PR15/PR16 stage and evidence readers.
An internally coherent candidate is *not* compiler, installer, boot or
redistribution authorization.
"""
import ast
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "project/host/resident-b-consolidated-source-selection-v1.json"
PACKAGE = ROOT / "project/package"
EXPECTED = {
    "box-control": (
        "c886e7a90bb4ea74e771a6c5dcefaa2069539ec7",
        "2a2749f9c223fb947695634008c5e37cafc49248c19f84262f60e23c7575a121",
        "one-shot",
    ),
    "root-control": (
        "d9dfd6c02a5a96750f1213bf663cdceab72f1efd",
        "8be83a4d9e50f7165ea08f70b8443cad4553b079fa058d29c3544766ebca5de1",
        "disabled-systemd-unit",
    ),
}
TOOLS = [
    "resident312-flit-core-final", "resident312-installer-final",
    "resident312-packaging-final", "resident312-wheel-final",
    "resident312-setuptools-final", "resident312-dbus-next-final",
    "resident312-image-build-final",
]
HOST = {
    "systemd-final": [
        "usr/lib/systemd/systemd-networkd", "usr/lib/systemd/systemd-resolved",
        "usr/bin/networkctl", "usr/bin/resolvectl",
    ],
    "host-install-final": ["usr/bin/host-install"],
    "host-discover-final": [
        "usr/bin/host-discover", "usr/bin/host-discover-recovery",
        "usr/bin/host-discover-supervisor",
    ],
}


def refuse(reason):
    raise ValueError("Resident B consolidated source candidate NOT READY: " + reason)


def literal(name, file="stages/final/produce-manifest.py"):
    return ast.literal_eval((PACKAGE / name / file).read_text())


def verify(*, selection=None):
    record = json.loads(SELECTION.read_text()) if selection is None else selection
    if (type(record) is not dict or set(record) != {
        "schema", "status", "lineage", "python_controllers", "source_tools",
        "controllers", "resident_utilities", "python_runtime_boundary",
        "retained_evidence", "native_authority", "remaining_native_checks",
        "native_input", "package_closure", "native_admission", "aggregate_installed",
    } or record["schema"] != "zog-resident-b-consolidated-source-selection-v1"
            or record["status"] != "SOURCE_CANDIDATE_PINNED_NATIVE_HOLD"):
        refuse("invalid source selection schema or false native promotion")
    lineage = record["lineage"]
    if (lineage != {
        "source_branch_base_commit": "0f90f125e79214e17b6dd2384b5f1c669a1e3cc0",
        "reuses": ["image-build PR #12", "image-build PR #14",
                   "image-build PR #15", "image-build PR #16"],
        "duplicate_package_stages": [],
    }):
        refuse("source lineage is duplicated, unrelated or substituted")
    aggregate = record["aggregate_installed"]
    if aggregate != {
        "schema": "zog-resident-b-installed-aggregate-selection-v1",
        "status": "SOURCE_PINNED_NO_ACTUAL_AGGREGATE",
        "source_pin_path": "project/host/resident-b-aggregate-installed-source-pins-v1.json",
        "distribution": "zog",
        "version": "0.1.1.dev20261117",
        "target_interpreter": "/usr/bin/python3.12",
        "controller_modules_pin_count": 78,
        "aggregate_wheel_sha256": None,
        "installed_record_sha256": None,
        "installed_root_generation": None,
        "installed_bytes_verified": False,
        "installer_receipt_verified": False,
        "native_activation_permitted": False,
    }:
        refuse("aggregate source evidence or native hold changed")
    pin_path = ROOT / aggregate["source_pin_path"]
    pins_spec = importlib.util.spec_from_file_location(
        "resident_b_aggregate_installed_pins",
        ROOT / "tools/verify_resident_b_aggregate_installed.py",
    )
    pins_verifier = importlib.util.module_from_spec(pins_spec)
    pins_spec.loader.exec_module(pins_verifier)
    try:
        source_pins = pins_verifier._check_selection(json.loads(pin_path.read_text()))
    except ValueError as exc:
        refuse("aggregate source controller pins rejected: " + str(exc))
    if sum(len(item["files"]) for item in source_pins["controllers"].values()) != 78:
        refuse("source-pinned controller aggregate module inventory changed")
    native = record["native_authority"]
    if (type(native) is not dict or set(native) != {
        "accepted_generation", "accepted_state", "native_generation_receipt",
        "native_compilation_permitted", "resident_service_activation_permitted",
        "redistribution_authorized"
    } or any(native[k] is not None for k in (
        "accepted_generation", "accepted_state", "native_generation_receipt"))
            or any(native[k] is not False for k in (
        "native_compilation_permitted", "resident_service_activation_permitted",
        "redistribution_authorized"))):
        refuse("source selection carries fabricated native authorization")
    py = record["python_controllers"]
    if (py.get("package") != "python-resident312-final"
            or py.get("version") != "3.12.16"
            or py.get("expected_soabi") != "cpython-312-x86_64-linux-gnu"
            or py.get("replaces_python_final") is not False
            or set(py["required_extensions"]) != {"_ssl", "_sqlite3", "_hashlib"}
            or set(py["build_dependencies"]) != {
                "openssl-final", "sqlite-final", "libffi-final",
                "expat-final", "gdbm-final", "pkgconf-final"
            }):
        refuse("Python 3.12 ABI and declared SSL/SQLite source closure changed")
    edges = literal("python-resident312", "stages/final/dependencies.py")
    if set(edges["build"]) != set(py["build_dependencies"]):
        refuse("Python 3.12 SSL/SQLite predecessor graph changed")
    py_outputs = literal("python-resident312")["required"]
    for path in (
        "usr/bin/python3.12",
        "usr/lib/libpython3.12.so.1.0",
        *("usr/lib/python3.12/lib-dynload/" + name +
          ".cpython-312-x86_64-linux-gnu.so"
          for name in py["required_extensions"]),
    ):
        if path not in py_outputs:
            refuse("Python 3.12 installed SSL/SQLite/ABI requirement omitted: " + path)
    if record["source_tools"] != TOOLS:
        refuse("Python wheel backend/tool chain was removed or duplicated")
    for item in TOOLS:
        name = item.removesuffix("-final")
        if literal(name, "package.py").get("status") != "catalogue-only":
            refuse("Python source tool gained premature native admission")
    if record["resident_utilities"] != HOST:
        refuse("Resident B networking and host CLI selection changed")
    for stage, paths in HOST.items():
        source = stage.removesuffix("-final")
        required = literal(source)["required"]
        if any(path not in required for path in paths):
            refuse("Resident B installed CLI output omitted: " + stage)
    boundary = record["python_runtime_boundary"]
    if boundary != {
        "controller_wheels": "python-resident312-final",
        "existing_host_install_and_discover_recipes":
            "python-final (3.15 source); existing manifests not rewritten to 3.12",
        "verify_both_installed_abi_closures": True,
    }:
        refuse("resident Python 3.12/3.15 source ABI boundary changed")
    for name in ("host-install", "host-discover"):
        if ("usr/lib/python3.15/site-packages/zog/" +
                name.replace("-", "_") + "/__init__.py") not in literal(name)["required"]:
            refuse("host utilities falsely described as Python 3.12 wheels")
    from importlib.util import module_from_spec, spec_from_file_location
    source_path = ROOT / "tools/verify_resident_b_combined_source.py"
    spec = spec_from_file_location("resident_b_prior_combined", source_path)
    prior = module_from_spec(spec)
    spec.loader.exec_module(prior)
    if prior.verify()["authority"] != "NO_GO":
        refuse("older combined source checks were bypassed")
    controllers = record["controllers"]
    if set(controllers) != set(EXPECTED):
        refuse("controller source omitted or duplicated")
    for name, (revision, digest, mode) in EXPECTED.items():
        item = controllers[name]
        package = literal(name, "package.py")
        original = literal(name, "stages/final/sources.py")[0]
        license = literal(name, "license.py")
        outputs = literal(name)["required"]
        if (item.get("stage") != name + "-final"
                or item.get("revision") != revision
                or item.get("archive_sha256") != digest
                or item.get("version") != "0.1.0"
                or item.get("entry_point") != "usr/bin/" + name
                or item.get("wheel_metadata") != ["METADATA", "RECORD"]
                or item.get("mode") != mode
                or package.get("source_revision") != revision
                or package.get("source_archive_sha256") != digest
                or package.get("status") != "catalogue-only"
                or original.get("sha256") != digest
                or not original.get("url", "").endswith("/" + revision)
                or license["source"].get("commit") != revision
                or license.get("status") != "unresolved"):
            refuse("controller source revision, archive or permission substituted: " + name)
        if ("usr/bin/" + name not in outputs
                or not any("/" + name.replace("-", "_") +
                           "-0.1.0.dist-info/" + meta in p for meta in item["wheel_metadata"]
                           for p in outputs)):
            # Installed stage manifests separately require both METADATA and RECORD.
            refuse("controller output metadata missing: " + name)
        for meta in ("METADATA", "RECORD"):
            if not any(p.endswith(name.replace("-", "_") +
                                    "-0.1.0.dist-info/" + meta) for p in outputs):
                refuse("controller installed wheel metadata lost: " + name)
    if record["retained_evidence"] != {
        "original_controller_sources_preserved_as_historical_review": True,
        "compiler_base_receipt_replaced": False,
        "boot_a_selection_changed": False,
    }:
        refuse("historical receipt or Boot A boundary changed")
    remaining = record["remaining_native_checks"]
    if (not isinstance(remaining, list) or len(remaining) != 7
            or any(not isinstance(x, str) or len(x) < 25 for x in remaining)):
        refuse("native acceptance obligations omitted")
    # The exact input generation and entire transitive stage graph are part of
    # this same selection. A source-only package list is insufficient.
    closure_path = ROOT / "tools/verify_resident_b_native_input_closure.py"
    native_spec = spec_from_file_location("resident_b_native_input_closure", closure_path)
    native = module_from_spec(native_spec)
    native_spec.loader.exec_module(native)
    native_result = native.verify(selection=record)
    if record["native_admission"]["authority"]["native_build_permitted"] is not False:
        refuse("native receipt source attempted to grant compiler dispatch")
    if (native_result["stage_count"] != 29
            or native_result["native_packages_verified"] is not False
            or native_result["compiler_authorized"] is not False):
        refuse("source package closure falsely admitted for native use")
    return {
        "source_selection": "CONSOLIDATED_CP312_AND_CURRENT_CONTROLLERS",
        "python3_12": "SOURCE_REVIEWED_NATIVE_UNACCEPTED",
        "network_outputs": "SOURCE_DECLARED",
        "controller_wheels": "REVIEWED_SOURCE_PINS",
        "accepted_generation": None,
        "compiler_authorized": False,
        "service_activation_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))

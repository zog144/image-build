"""Resident B must remain separately source-audited, never inferred from Boot A."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "resident_b", ROOT/"tools/verify_resident_b_source_prerequisites.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
RECORD = json.loads(audit.AUDIT.read_text())


def copies():
    return {k:audit.literal(audit.PKG/n/"stages/final/produce-manifest.py")
            for k,n in audit.SOURCE_STAGE.items()}


def dependencies():
    return {k:audit.literal(audit.PKG/n/"stages/final/dependencies.py")
            for k,n in audit.SOURCE_STAGE.items()}


def builds():
    return {k:(audit.PKG/k/"stages/final/build.py").read_text()
            for k in ("python","dbus","systemd","iproute2")}


def test_resident_b_is_a_read_only_gap_inventory_not_native_acceptance():
    report = audit.inspect(RECORD)
    assert report == {
        "inventory":"PASS_EXACT_SOURCE_GAPS_RETAINED",
        "authored_python":"3.15.0rc2", "requested_python":"3.12",
        "unresolved":11, "resident_b":"NO_GO",
        "native_generation":"UNVERIFIED",
        "boot_a":"UNCHANGED_NOT_ACCEPTED",
    }


@pytest.mark.parametrize("field,value",[
    ("native_generation_id","a"*64),
    ("installed_artifact_receipts",{"fake":"pass"}),
    ("build_submitted",True),
    ("credential_delivery_enabled",True),
    ("certificate_dependency",True),
    ("production_source_selection_changed",True),
    ("boot_a_audit_unchanged",False),
    ("source_status","READY"),
    ("admission","GO"),
    ("resident_b_ready",True),
])
def test_unauthenticated_generation_or_native_promotion_is_rejected(field,value):
    row=copy.deepcopy(RECORD)
    row[field]=value
    with pytest.raises(ValueError):
        audit.inspect(row)


@pytest.mark.parametrize("field,value",[
    ("requested_python_version","3.15"),
    ("authored_python_upstream_version","3.12.0"),
    ("reviewed_boot_a_pr10_head","0"*40),
    ("scope","boot-a-approved"),
])
def test_version_scope_and_exact_source_cannot_shift(field,value):
    row=copy.deepcopy(RECORD)
    row[field]=value
    with pytest.raises(ValueError):
        audit.inspect(row)


@pytest.mark.parametrize("stage,path",[
    ("python-final","usr/bin/python3"),
    ("openssl-final","usr/lib/libssl.so"),
    ("sqlite-final","usr/lib/libsqlite3.so"),
    ("dbus-final","usr/bin/dbus-daemon"),
    ("iproute2-final","usr/sbin/ip"),
    ("systemd-final","usr/lib/systemd/systemd-resolved"),
    ("host-install-final","usr/lib/python3.15/site-packages/zog/host_install/__init__.py"),
    ("host-discover-final","usr/lib/python3.15/site-packages/zog/host_discover/__init__.py"),
    ("ca-certificates-final","etc/ssl/certs/ca-certificates.crt"),
])
def test_missing_source_stage_outputs_cannot_pass_inventory(stage,path):
    source=copies()
    source[stage]["required"].remove(path)
    with pytest.raises(ValueError,match="observed source output missing"):
        audit.inspect(RECORD,stages=source)


@pytest.mark.parametrize("stage,path",[
    ("python-final","usr/bin/python3.12"),
    ("systemd-final","usr/bin/networkctl"),
    ("host-install-final","usr/bin/host-install"),
    ("host-discover-final","usr/bin/host-discover"),
])
def test_newly_added_required_outputs_must_trigger_exact_fresh_review(stage,path):
    source=copies()
    source[stage]["required"].append(path)
    with pytest.raises(ValueError,match="unreviewed Resident B source output"):
        audit.inspect(RECORD,stages=source)


@pytest.mark.parametrize("stage,dependency",[
    ("python-final","openssl-final"),
    ("python-final","sqlite-final"),
    ("host-identify-final","python-cryptography-final"),
    ("host-install-final","python-final"),
])
def test_new_runtime_stage_edges_require_review(stage,dependency):
    d=dependencies()
    d[stage]["runtime"].append(dependency)
    with pytest.raises(ValueError,match="runtime stage dependencies drifted"):
        audit.inspect(RECORD,dependencies=d)


@pytest.mark.parametrize("field,value",[
    ("PYTHON_SSL_SQLITE_INSTALLED","PASS"),
    ("ROOT_BOX_CONTROL_PACKAGES","accepted"),
    ("SYSTEMD_NETWORK_UTILITIES","PASS"),
])
def test_known_unresolved_gaps_cannot_be_marked_accepted(field,value):
    row=copy.deepcopy(RECORD)
    next(x for x in row["uncovered_stage_requirements"]
         if x["code"]==field)["status"]=value
    with pytest.raises(ValueError,match="gaps were concealed"):
        audit.inspect(row)


def test_unknown_or_omitted_finding_fails_closed():
    row=copy.deepcopy(RECORD)
    row["uncovered_stage_requirements"].pop()
    with pytest.raises(ValueError,match="gaps were concealed"):
        audit.inspect(row)


def test_runtime_controller_package_stage_inventory_is_not_invented():
    packages={p.name for p in audit.PKG.iterdir() if p.is_dir()}
    for invented in ("box-control","root-control"):
        with pytest.raises(ValueError,match="controller packaging gap"):
            audit.inspect(RECORD,existing_packages=packages|{invented})


@pytest.mark.parametrize("package,flag",[
    ("python","MODULE__SSL_STATE=yes"),
    ("python","MODULE__SQLITE3_STATE=yes"),
    ("dbus","-Ddbus_user=messagebus"),
    ("systemd","-Dnetworkd=true"),
    ("systemd","-Dtimesyncd=true"),
    ("iproute2","--libbpf_force=off"),
])
def test_missing_runtime_feature_flag_refuses_passing_inventory(package,flag):
    source=builds()
    assert flag in source[package]
    source[package]=source[package].replace(flag,"source-option-removed")
    with pytest.raises(ValueError):
        audit.inspect(RECORD,build_scripts=source)

"""Resident B review stays independent of Boot A and any actual Host."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "resident_b_source",ROOT/"tools/verify_resident_b_source_prerequisites.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
RECORD=json.loads(mod.AUDIT.read_text())

def test_reviewed_source_gaps_are_consistent_and_native_not_authorized():
    result=mod.review(RECORD)
    assert result["resident_b_ready"] is False
    assert result["accepted_generation"] is None
    assert result["python_target_version"]=="3.12"
    assert result["python_source_version"]=="3.15.0rc2"
    assert set(result["missing_required_output_paths"])==mod.MISSING_RESIDENT_B_OUTPUTS
    assert set(result["source_blockers"])==mod.GAPS

@pytest.mark.parametrize("field,changed",[
    ("accepted_generation_id","a"*64),
    ("installed_output_provenance",{"signature":"fake","verified":True}),
    ("source_promoted",True),("native_accepted",True),
    ("release_authorized",True),("job_submission_authorized",True),
    ("boot_a_reopened",True),("certificate_dependency",True),
    ("status","RESIDENT_B_READY"),
    ("target_python","3.15"),("source_python","3.12.12")
])
def test_early_promotion_or_altered_target_is_denied(field,changed):
    altered=copy.deepcopy(RECORD)
    altered[field]=changed
    with pytest.raises(ValueError,match="Resident B source audit NO-GO"):
        mod.review(altered)

def test_unrecognized_authorization_is_never_accepted_as_source_evidence():
    altered=copy.deepcopy(RECORD)
    altered["external_accepted_generation"]={
        "generation_id":"a"*64,"issuer":"host-install","signed":True}
    with pytest.raises(ValueError,match="unknown admission field"):
        mod.review(altered)

@pytest.mark.parametrize("package,path",[
    ("openssl","usr/lib/libssl.so"),
    ("sqlite","usr/lib/libsqlite3.so"),
    ("ca-certificates","etc/ssl/cert.pem"),
    ("dbus","usr/lib/systemd/system/dbus.service"),
    ("iproute2","usr/sbin/ip"),
    ("systemd","usr/lib/systemd/systemd-resolved"),
    ("e2fsprogs","usr/sbin/mkfs.ext4"),
    ("host-install","usr/lib/python3.15/site-packages/zog/host_install/__init__.py"),
])
def test_omitted_real_stage_output_cannot_be_reported_present(package,path):
    manifests={
        p:mod.literal(ROOT/RECORD["source_stage_inputs"][p]/"produce-manifest.py")
        for p in mod.PACKAGE_NAMES
    }
    manifests[package]["required"].remove(path)
    with pytest.raises(ValueError,match="missing observed source-stage output"):
        mod.review(RECORD,manifests=manifests)

def test_python_3_12_is_not_silently_substituted_for_3_15_recipe():
    altered=mod.literal(ROOT/"project/package/python/stages/final/sources.py")
    altered[0]["url"]="https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tar.xz"
    with pytest.raises(ValueError,match="not the reviewed 3.15"):
        mod.review(RECORD,python_source=altered)

def test_python_openssl_and_sqlite_dependencies_require_separate_review():
    altered=mod.literal(ROOT/"project/package/python/stages/final/dependencies.py")
    altered["build"].extend(("openssl-final","sqlite-final"))
    with pytest.raises(ValueError,match="dependency gap changed"):
        mod.review(RECORD,python_dependencies=altered)

def test_python_ssl_extension_output_claim_cannot_be_invented():
    manifests={
        p:mod.literal(ROOT/RECORD["source_stage_inputs"][p]/"produce-manifest.py")
        for p in mod.PACKAGE_NAMES
    }
    manifests["python"]["required"].append("usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so")
    with pytest.raises(ValueError,match="Python extension output contract changed"):
        mod.review(RECORD,manifests=manifests)

def test_systemd_network_tools_cannot_be_claimed_accepted_by_a_modified_record():
    altered=copy.deepcopy(RECORD)
    altered["resident_b_host_install_required"].remove("usr/bin/resolvectl")
    with pytest.raises(ValueError,match="host-install required Resident B"):
        mod.review(altered)

def test_no_boot_a_audit_artifacts_modified_by_this_branch():
    assert "Boot A" in RECORD["scope"]
    assert RECORD["boot_a_reopened"] is False

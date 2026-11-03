#!/usr/bin/env python3
"""Separate, read-only Resident B source audit. NEVER accepts a generation."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
AUDIT = PROJECT / "host/resident-b-source-prerequisite-audit.json"
SCHEMA = "zog-resident-b-source-prerequisites-audit-v1"
REVISION = "1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
HOST_INSTALL_REVISION = "08f007cb14598d22debb2efc20eb3f00c2d8f2dd"
GAPS = frozenset((
    "PYTHON_TARGET_3_12_CONTRADICTS_PINNED_3_15_RC2",
    "PYTHON_OPENSSL_SQLITE_STAGE_DEPS_NOT_DECLARED",
    "PYTHON_SSL_SQLITE_EXTENSION_OUTPUTS_NOT_REQUIRED",
    "NETWORKCTL_RESOLVECTL_MANIFEST_NOT_REQUIRED",
    "HOST_INSTALL_DISCOVER_EXECUTABLE_MANIFEST_NOT_REQUIRED",
    "BOX_CONTROL_ROOT_CONTROL_STAGE_MISSING",
    "PROTECTED_INHERITED_BUILD_AND_CA_RUNTIME_PROOF_ABSENT",
    "GENERATION_AND_RUNNING_SERVICES_NOT_VERIFIED",
))
REQUIRED_ROOT_FIELDS = frozenset((
    "schema","reviewed_image_build_source","host_install_bootable_contract_revision",
    "scope","status","target_python","source_python","python_stage",
    "source_stage_inputs","declared_existing_contracts",
    "resident_b_host_install_required","source_blockers","accepted_generation_id",
    "installed_output_provenance","source_promoted","native_accepted",
    "release_authorized","job_submission_authorized","boot_a_reopened",
    "certificate_dependency",
))
PACKAGE_NAMES = frozenset((
    "python","openssl","sqlite","ca-certificates","dbus",
    "iproute2","systemd","host-install","host-discover","host-identify",
))
DEFERRALS = frozenset(("box-control","root-control"))
MISSING_RESIDENT_B_OUTPUTS = frozenset((
    "usr/bin/networkctl","usr/bin/resolvectl","usr/bin/host-install",
    "usr/bin/host-discover","usr/bin/box-control","usr/bin/root-control",
))

def literal(path):
    return ast.literal_eval(path.read_text())

def _fail(reason):
    raise ValueError("Resident B source audit NO-GO: " + reason)

def review(record, *, manifests=None, python_dependencies=None,
           python_source=None, python_build=None):
    if type(record) is not dict or set(record)!=REQUIRED_ROOT_FIELDS:
        _fail("unknown admission field or missing source requirement")
    if (record["schema"]!=SCHEMA or record["reviewed_image_build_source"]!=REVISION
            or record["host_install_bootable_contract_revision"]!=HOST_INSTALL_REVISION
            or record["status"]!="SOURCE_GAPS_DOCUMENTED_RESIDENT_B_NO_GO"
            or record["target_python"]!="3.12" or record["source_python"]!="3.15.0rc2"
            or record["python_stage"]!="python/stages/final"):
        _fail("pinned Resident B scope/source mismatch")
    if (record["accepted_generation_id"] is not None
            or record["installed_output_provenance"] is not None
            or any(record[key] is not False for key in (
                "source_promoted","native_accepted","release_authorized",
                "job_submission_authorized","boot_a_reopened",
                "certificate_dependency"))):
        _fail("source-only inspection claims native generation, Boot A or certification")
    if set(record["source_blockers"])!=GAPS:
        _fail("reviewed source blockers hidden or treated as resolved")
    stages=record.get("source_stage_inputs")
    if type(stages) is not dict or set(stages)!=PACKAGE_NAMES or any(
        stages.get(p)!="project/package/"+p+"/stages/final" for p in PACKAGE_NAMES
    ):
        _fail("missing real source-stage selection")
    expected=record.get("declared_existing_contracts")
    if type(expected) is not dict or set(expected)!=PACKAGE_NAMES:
        _fail("incomplete declared stage output inventory")
    manifests=manifests or {
        p:literal(ROOT / stages[p] / "produce-manifest.py") for p in PACKAGE_NAMES
    }
    if set(manifests)!=PACKAGE_NAMES:
        _fail("missing original package manifest")
    for p in PACKAGE_NAMES:
        manifest=manifests[p]
        if not isinstance(manifest,dict) or not isinstance(manifest.get("required"),list):
            _fail("invalid original source-stage output manifest: "+p)
        declared=set(manifest["required"])
        if not set(expected[p]).issubset(declared):
            _fail("missing observed source-stage output: "+p)
        if not (ROOT/"project/package"/p/"package.py").exists():
            _fail("source package metadata missing: "+p)
    python_meta=literal(PROJECT/"package/python/package.py")
    if python_meta.get("status")!="catalogue-only":
        _fail("Python source stage silently admitted")
    python_source=python_source or literal(PROJECT/"package/python/stages/final/sources.py")
    if not (isinstance(python_source,list) and len(python_source)==1 and
            "Python-3.15.0rc2.tar.xz" in python_source[0].get("url","")):
        _fail("actual selected Python is not the reviewed 3.15 release candidate")
    python_build=python_build or literal(PROJECT/"package/python/stages/final/build.py")
    configure="\n".join(step[-1] for step in python_build.get("configure",[]))
    if ("upstream/Python-3.15.0rc2" not in configure or
            "MODULE__SSL_STATE=yes" not in configure or
            "MODULE__SQLITE3_STATE=yes" not in configure or
            "/usr/include/openssl/ssl.h" not in configure or
            "/usr/include/sqlite3.h" not in configure):
        _fail("Python build's SSL/SQLite configuration obligations changed")
    python_dependencies=python_dependencies or literal(PROJECT/"package/python/stages/final/dependencies.py")
    if (type(python_dependencies) is not dict or
            set(python_dependencies)!={"build","runtime"}):
        _fail("Python dependency map missing")
    deps=set(python_dependencies["build"]) | set(python_dependencies["runtime"])
    if "openssl-final" in deps or "sqlite-final" in deps:
        _fail("reviewed Python source-stage dependency gap changed; reconcile new source")
    required_python=set(manifests["python"]["required"])
    if any("/_ssl." in path or "/_sqlite3." in path for path in required_python):
        _fail("Python extension output contract changed; source audit requires revision")
    if "usr/bin/networkctl" in manifests["systemd"]["required"] or \
       "usr/bin/resolvectl" in manifests["systemd"]["required"]:
        _fail("systemd network CLI output contract changed; re-review source")
    for p in ("host-install","host-discover"):
        if "usr/bin/"+p in manifests[p]["required"]:
            _fail("controller executable contract changed; re-review source")
    if any((PROJECT/"package"/p/"stages/final").exists() for p in DEFERRALS):
        _fail("trusted controller stage authored; re-review before Resident B readiness")
    required=set(record.get("resident_b_host_install_required",[]))
    if not MISSING_RESIDENT_B_OUTPUTS.issubset(required):
        _fail("host-install required Resident B programs omitted")
    all_declared={item for m in manifests.values() for item in m.get("required",[])}
    if required-all_declared != MISSING_RESIDENT_B_OUTPUTS:
        _fail("unexpected Resident B output gap; re-review recorded host-install contract")
    return {
        "schema":SCHEMA,
        "source_inventory":"CONSISTENT_WITH_REVIEWED_GAPS",
        "missing_required_output_paths":sorted(MISSING_RESIDENT_B_OUTPUTS),
        "python_target_version":"3.12",
        "python_source_version":"3.15.0rc2",
        "source_blockers":sorted(GAPS),
        "resident_b_ready":False,
        "accepted_generation":None,
    }

if __name__=="__main__":
    print(json.dumps(review(json.loads(AUDIT.read_text())),sort_keys=True))

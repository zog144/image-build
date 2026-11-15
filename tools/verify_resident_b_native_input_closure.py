#!/usr/bin/env python3
"""Read-only Resident B native predecessor + complete package-stage source graph.

The exact Boot A successor is an *intended input*, not a claim that any of the
Resident B package outputs or dependency generations have been installed.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "project/host/resident-b-consolidated-source-selection-v1.json"
PACKAGES = ROOT / "project/package"
GENERATION = "273de2a04a8a0b8d4db3005bca078639f3c2fdcd6f9e24a9619d2b0ca6947aab"
PRODUCER = "68d6397ca20c4651df8f13c8a840dc8f77d55034"
PARENT = "45a81ec3ea473bfa397e546b5c0ec1ae306bf00cb864eaa9a86d94c13c623f2e"
FAILED = "5af34ec67cbfdcd1e7936bf70e3cf2f5c6945c7e3de5f95993918325f6e29c44"
HOST_INSTALL_SELECTION = "c783ccbaa2768efd6d9e3c4c5d2c3e1215180b5a"
PLAN_PATH = "examples/resident-boot-a-successor-2026-10-31/plan.json"
ROOT_STAGES = (
    "python-final", "python-cryptography-final", "host-identify-final",
    "host-install-final", "host-discover-final",
    "python-resident312-final", "resident312-flit-core-final",
    "resident312-installer-final", "resident312-packaging-final",
    "resident312-wheel-final", "resident312-setuptools-final",
    "resident312-dbus-next-final", "resident312-image-build-final",
    "box-control-final", "root-control-final",
    "openssl-final", "sqlite-final", "ca-certificates-final", "dbus-final",
    "iproute2-final", "systemd-final",
)


def reject(message):
    raise ValueError("Resident B native predecessor/source closure NOT READY: " + message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def read_stage(stage):
    if not isinstance(stage, str) or not stage.endswith("-final"):
        reject("invalid stage selector")
    file = PACKAGES / stage[:-6] / "stages/final/dependencies.py"
    if not file.is_file():
        reject("source dependency definition missing: " + stage)
    try:
        return ast.literal_eval(file.read_text())
    except (ValueError, SyntaxError) as exc:
        raise ValueError("unreadable source dependency definition: " + stage) from exc


def closure(roots=ROOT_STAGES, *, reader=read_stage):
    """Exact transitive build/runtime closure; also rejects missing/cyclic source."""
    graph = {}
    visiting = set()
    def visit(stage):
        if stage in visiting:
            reject("source dependency cycle: " + stage)
        if stage in graph:
            return
        visiting.add(stage)
        edges = reader(stage)
        if type(edges) is not dict or set(edges) != {"build", "runtime"}:
            reject("invalid build/runtime source dependency record: " + stage)
        record = {}
        for kind in ("build", "runtime"):
            items = edges[kind]
            if (type(items) is not list or len(items) != len(set(items)) or
                any(type(x) is not str or not x.endswith("-final") or x == stage
                    for x in items)):
                reject("invalid or duplicate source dependency edges: " + stage)
            record[kind] = sorted(items)
            for child in items:
                visit(child)
        graph[stage] = record
        visiting.remove(stage)
    if (type(roots) not in (tuple, list) or len(roots) != len(set(roots))
            or not roots):
        reject("invalid root stage selection")
    for root in roots:
        visit(root)
    return dict(sorted(graph.items()))


def evidence(native):
    if (type(native) is not dict or set(native) != {
        "generation", "kind", "role", "producer_source_revision",
        "retained_parent_generation", "rejected_predecessor", "source_plan",
        "source_verification", "inventory_entries", "provenance_records",
        "canonical_archive_sha256", "installed_package_receipt_sha256",
        "package_inventory_verified_against_predecessor",
        "booted_resident_runtime_verified",
    }):
        reject("native input schema differs")
    if (native["generation"] != GENERATION or native["kind"] != "image"
        or native["role"] != "resident-b-intended-build-predecessor"
        or native["producer_source_revision"] != PRODUCER
        or native["retained_parent_generation"] != PARENT
        or native["rejected_predecessor"] != FAILED
        or native["source_plan"] != {
            "repository": "zog144/host-install",
            "reviewed_commit": HOST_INSTALL_SELECTION,
            "path": PLAN_PATH,
        }
        or native["source_verification"] !=
            "published-source-and-installed-verification-passed"
        or native["inventory_entries"] != 40974
        or native["provenance_records"] != 27):
        reject("substituted Boot A predecessor or unsupported evidence")
    if (native["canonical_archive_sha256"] is not None
        or native["installed_package_receipt_sha256"] is not None
        or native["package_inventory_verified_against_predecessor"] is not False
        or native["booted_resident_runtime_verified"] is not False):
        reject("native source selection fabricates installed/booted evidence")


def check_original_plan(plan):
    """Compare the actual host-install PR39 source selection, not old failed plan."""
    try:
        binding = plan["generation_binding"]
        selected = plan["slots"]["HOST-A"]
    except (KeyError, TypeError) as exc:
        raise ValueError("missing host-install successor source plan") from exc
    if (plan.get("schema") != "zog-host-install-boot-a-successor-disposable-plan-v1"
        or plan.get("selected_slot") != "HOST-A"
        or binding.get("generation") != GENERATION
        or binding.get("producer_source_revision") != PRODUCER
        or binding.get("retained_parent_generation") != PARENT
        or binding.get("rejected_predecessor") != FAILED
        or binding.get("retained_inventory_entries") != 40974
        or binding.get("retained_provenance_records") != 27
        or selected.get("generation") != GENERATION
        or selected.get("read_only") is not True
        or plan.get("device_writes_authorized") is not False
        or plan.get("native_boot_authorized") is not False
        or binding.get("publication_byte_pins") is not None
        or binding.get("generation_rebuilt_by_installer") is not False):
        reject("host-install reviewed successor differs or falsely grants execution")
    return True


def verify(*, selection=None, reader=read_stage, allow_unpinned=False):
    data = json.loads(SELECTION.read_text()) if selection is None else selection
    evidence(data.get("native_input"))
    p = data.get("package_closure")
    if type(p) is not dict or set(p) != {
        "policy", "source_roots", "stage_scope", "closure_stage_count",
        "closure_graph_sha256", "predecessor_package_receipts_verified",
        "package_binary_closure_verified", "source_graph_status",
    }:
        reject("package closure contract missing")
    if (p["policy"] != "recursive-final-stage-dependencies-v1"
        or p["source_roots"] != list(ROOT_STAGES)
        or p["stage_scope"] !=
        "candidate-from-existing-recipes; verify-predecessor-outputs-or-build-with-reviewed-source; no-inferred-installed-stage"
        or p["predecessor_package_receipts_verified"] is not False
        or p["package_binary_closure_verified"] is not False):
        reject("package closure source or native receipt boundaries changed")
    graph = closure(p["source_roots"], reader=reader)
    digest = hashlib.sha256(canonical(graph)).hexdigest()
    if not allow_unpinned:
        if (p["source_graph_status"] != "SOURCE_GRAPH_CLOSED_NATIVE_INPUT_RECEIPTS_HELD"
            or p["closure_stage_count"] != len(graph)
            or p["closure_graph_sha256"] != "sha256:" + digest):
            reject("source transitive closure checksum/count not pinned")
    elif p["source_graph_status"] not in (
        "NEEDS_FIRST_SOURCE_MEASUREMENT",
        "SOURCE_GRAPH_CLOSED_NATIVE_INPUT_RECEIPTS_HELD",
    ):
        reject("unknown source-graph status")
    return {"native_input_generation": GENERATION, "stage_count": len(graph),
            "closure_graph_sha256": "sha256:" + digest,
            "source_roots": list(ROOT_STAGES),
            "stages": list(graph),
            "native_packages_verified": False, "compiler_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measure", action="store_true",
                        help="show exact deterministic graph before source digest is pinned")
    parser.add_argument("--host-install-plan", type=Path,
                        help="optional independently checked out PR39 plan for read-only comparison")
    options = parser.parse_args()
    if options.host_install_plan is not None:
        check_original_plan(json.loads(options.host_install_plan.read_text()))
    print(json.dumps(verify(allow_unpinned=options.measure), sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Source-only measurement of reviewed, *newer* Resident B controllers.

Measurements are evidence for source selection, not a synthetic archive,
native compilation, redistribution permission, or service authorization.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
original_path = ROOT / "tools" / "inspect_resident_controller_archive.py"
spec = spec_from_file_location("original_controller_archive", original_path)
original = module_from_spec(spec)
spec.loader.exec_module(original)

SELECTED = {
    "box-control": ("c886e7a90bb4ea74e771a6c5dcefaa2069539ec7",
                    "box-control/pyproject.toml"),
    "root-control": ("d9dfd6c02a5a96750f1213bf663cdceab72f1efd",
                     "pyproject.toml"),
}
UNCHANGED_METADATA = {
    "box-control": {
        "pyproject_sha256": "a099487955e9b42e90aed4103cb32e76f7dae0535692534c25b7be2f09a4eb47",
        "license_sha256": "aaf3d5919ea7f2720b7649d4f1e4fd28a54c58425a45dfd736d040a56480578f",
        "third_party_notice_sha256": "b6636714adafd8c7c8e9ab1db2d07e3c7efe3b312fa10268bc393b83e1db7036",
    },
    "root-control": {
        "pyproject_sha256": "f42d1b9458536b4b20aef183d438267b0790bb8fc9238afcc10b9a1bc62b1c96",
        "license_sha256": "421a457ded4d2bf4b853c5ce211f74797292b2ef2f82bc7245304956fb7cf68f",
        "third_party_notice_sha256": "b3aa6c652c70db0faecdd42d35723c62bc61282dc53a2c1d19d53d73f637f26e",
    },
}


def inspect_all(inspector=original.inspect):
    results = []
    for name, (commit, marker) in SELECTED.items():
        observed = inspector(name, commit, marker)
        print("ZOG_RESIDENT_B_SUCCESSOR_MEASURED", json.dumps(observed, sort_keys=True), flush=True)
        for field, expected in UNCHANGED_METADATA[name].items():
            if observed[field] != expected:
                raise RuntimeError(f"{name} changed upstream original {field}")
        if observed["commit"] != commit or observed["project_member"] != marker:
            raise RuntimeError(f"{name} original commit/metadata was substituted")
        if observed["archive_root"] != f"zog144-{name}-{commit[:7]}":
            raise RuntimeError(f"{name} original archive root differs")
        if observed["source_only"] is not True or observed["redistribution_authorized"] is not False:
            raise RuntimeError(f"{name} native/rights admission was falsely claimed")
        results.append(observed)
    return results


if __name__ == "__main__":
    for report in inspect_all():
        print("ZOG_RESIDENT_B_SUCCESSOR_SOURCE", json.dumps(report, sort_keys=True), flush=True)

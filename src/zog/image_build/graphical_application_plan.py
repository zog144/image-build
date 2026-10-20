"""Machine-readable source status for optional graphical applications.

This module is deliberately read-only. It validates the reviewed catalogue/source
pins and dependency ordering, but it never compiles, publishes, selects, mounts,
launches, or grants privileged roles.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from .errors import ImageBuildError

CONTRACT = "image-build-graphical-application-plan-v1"
ARTIFACT_CONTRACT = "applications-v1"
VIEW_CONTRACT = "application-software-view-v1"
CONSUMER_CONTRACT = "application-software-consumer-v1"


def _literal(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ImageBuildError("graphical application source metadata is unavailable")
    try:
        return ast.literal_eval(path.read_text())
    except (OSError, ValueError, SyntaxError) as error:
        raise ImageBuildError("invalid graphical application source metadata") from error


def _source(record):
    if (
        not isinstance(record, dict)
        or set(record) != {"url", "sha256", "destination", "archive"}
        or not isinstance(record["url"], str)
        or not record["url"].startswith("https://")
        or not isinstance(record["sha256"], str)
        or len(record["sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in record["sha256"])
        or not isinstance(record["destination"], str)
        or not record["destination"]
        or record["archive"] is not True
    ):
        raise ImageBuildError("invalid graphical application source pin")
    return dict(record)


def _catalogue(repository_root, name):
    root = Path(repository_root).resolve() / "project" / "package" / name
    package = _literal(root / "package.py")
    sources = _literal(root / "sources.py")
    if (
        not isinstance(package, dict)
        or package.get("schema") != 1
        or package.get("name") != name
        or package.get("status") != "catalogue-only"
        or package.get("artifact_contract") != ARTIFACT_CONTRACT
        or not isinstance(package.get("source_version"), str)
        or not isinstance(package.get("license_scope"), str)
        or not package["license_scope"]
        or not isinstance(sources, list)
        or not sources
    ):
        raise ImageBuildError("invalid graphical application catalogue entry")
    return {
        "package": name,
        "source_version": package["source_version"],
        "recipe_status": package["recipe_status"],
        "activation": package["activation"],
        "license_scope": package["license_scope"],
        "sources": [_source(item) for item in sources],
    }


def _validate_plan(value):
    required = {
        "schema",
        "contract",
        "artifact_contract",
        "view_contract",
        "consumer_contract",
        "first_group",
        "prepared_foundation_batches",
        "later_group",
        "acceptance_order",
    }
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value["schema"] != 1
        or value["contract"] != CONTRACT
        or value["artifact_contract"] != ARTIFACT_CONTRACT
        or value["view_contract"] != VIEW_CONTRACT
        or value["consumer_contract"] != CONSUMER_CONTRACT
    ):
        raise ImageBuildError("unsupported graphical application plan")
    first = value["first_group"]
    if not isinstance(first, list) or not first:
        raise ImageBuildError("graphical first group is empty")
    names = [item.get("application") for item in first if isinstance(item, dict)]
    if len(names) != len(first) or len(set(names)) != len(names):
        raise ImageBuildError("duplicate graphical application plan")
    seen = set()
    for item in first:
        required_item = {
            "id",
            "application",
            "catalogue_package",
            "depends_on",
            "source_status",
            "build_status",
            "publication",
            "privileged_role",
            "blockers",
            "verified_artifact_ids",
            "verified_view_ids",
        }
        if (
            set(item) != required_item
            or not isinstance(item["id"], str)
            or not isinstance(item["application"], str)
            or not isinstance(item["catalogue_package"], str)
            or not isinstance(item["depends_on"], list)
            or any(dep not in seen for dep in item["depends_on"])
            or item["publication"] != "separate-artifact-and-view"
            or type(item["privileged_role"]) is not bool
            or not isinstance(item["blockers"], list)
            or not item["blockers"]
            or item["verified_artifact_ids"] != []
            or item["verified_view_ids"] != []
        ):
            raise ImageBuildError("invalid graphical first-group entry")
        seen.add(item["application"])
    if value["acceptance_order"][-1] != "privileged-pam-logind-if-applicable":
        raise ImageBuildError("graphical privileged acceptance boundary changed")
    return value


def describe(repository_root):
    root = Path(repository_root).resolve()
    plan = _validate_plan(
        _literal(root / "project" / "bootstrap" / "graphical-applications-first.py")
    )
    enriched = json.loads(json.dumps(plan))
    catalogues = {}
    for item in [*plan["first_group"], *plan["later_group"]]:
        name = item.get("catalogue_package")
        if name is not None and name not in catalogues:
            catalogues[name] = _catalogue(root, name)
    enriched["catalogue"] = {
        name: catalogues[name] for name in sorted(catalogues)
    }
    return enriched


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(describe(args.repository_root), sort_keys=True))


if __name__ == "__main__":
    main()

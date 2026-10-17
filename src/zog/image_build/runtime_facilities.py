"""Runtime-facility normalization for published application images.

Package builds may create empty ephemeral directories below controller-owned roots
(for example D-Bus installing /run/dbus). Those directories are retained in the
package output/provenance record, but application-image assembly replaces the five
facility trees with empty roots. Any immutable content below a facility fails closed.
"""
from pathlib import Path, PurePosixPath

from .errors import ImageBuildError
from .filesystem import inventory

CONTRACT = "image-build-runtime-facility-intent-v1"
FIELD = "runtime_facility_intent"
ROOT_MODES = {
    "applications": 0o755,
    "run": 0o755,
    "proc": 0o755,
    "sys": 0o755,
    "dev": 0o755,
}
ROOTS = tuple(ROOT_MODES)


def _canonical_path(value):
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        raise ImageBuildError("invalid runtime facility directory path")
    path = PurePosixPath(value)
    if str(path) != value or ".." in path.parts:
        raise ImageBuildError("invalid runtime facility directory path")
    return value


def validate(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"contract", "roots", "directories"}
        or value["contract"] != CONTRACT
    ):
        raise ImageBuildError("unsupported runtime facility intent")
    expected_roots = [
        {
            "path": "/" + name,
            "mode": mode,
            "materialization": "controller-private-scaffold",
        }
        for name, mode in ROOT_MODES.items()
    ]
    if value["roots"] != expected_roots:
        raise ImageBuildError("runtime facility roots differ from controller contract")
    directories = value["directories"]
    if not isinstance(directories, list):
        raise ImageBuildError("runtime facility directories must be a list")
    paths = []
    for item in directories:
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "mode", "packages", "materialization"}
        ):
            raise ImageBuildError("invalid runtime facility directory intent")
        path = _canonical_path(item["path"])
        if not any(path.startswith("/" + root + "/") for root in ROOTS):
            raise ImageBuildError("runtime directory is outside a facility root")
        if type(item["mode"]) is not int or not 0 <= item["mode"] <= 0o7777:
            raise ImageBuildError("invalid runtime facility directory mode")
        packages = item["packages"]
        if (
            not isinstance(packages, list)
            or not packages
            or packages != sorted(set(packages))
            or any(not isinstance(name, str) or not name for name in packages)
        ):
            raise ImageBuildError("invalid runtime facility package ownership")
        if item["materialization"] != "runtime-owner":
            raise ImageBuildError("unsupported runtime directory materialization")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise ImageBuildError("runtime facility directory intent is not canonical")
    known = set(paths)
    for path in paths:
        parent = str(PurePosixPath(path).parent)
        if parent not in {"/" + root for root in ROOTS} and parent not in known:
            raise ImageBuildError("runtime facility directory parent intent is missing")
    return value


def derive(built):
    """Bind directory-only package output beneath runtime facilities.

    Facility roots themselves belong to the controller private scaffold. Nested
    directories retain package attribution and mode as runtime intent. A package
    file, symlink or special object below these roots is immutable image content
    and is therefore rejected instead of silently stripped.
    """
    directories = {}
    for package, record in sorted(built.items()):
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("outputs"), list)
            or inventory(Path(record.get("root", ""))) != record["outputs"]
        ):
            raise ImageBuildError("runtime facility package output changed: " + str(package))
        for entry in record["outputs"]:
            path = entry["path"]
            root = path.split("/", 1)[0]
            if root not in ROOT_MODES:
                continue
            if entry["kind"] != "directory":
                raise ImageBuildError(
                    "runtime facility contains immutable package content: /" + path
                )
            if path == root:
                if entry["mode"] != ROOT_MODES[root]:
                    raise ImageBuildError(
                        "runtime facility root mode differs from controller contract: /" + root
                    )
                continue
            current = directories.get(path)
            if current is None:
                current = {
                    "path": "/" + path,
                    "mode": entry["mode"],
                    "packages": [],
                    "materialization": "runtime-owner",
                }
                directories[path] = current
            elif current["mode"] != entry["mode"]:
                raise ImageBuildError(
                    "runtime facility directory mode conflict: /" + path
                )
            current["packages"].append(package)
    value = {
        "contract": CONTRACT,
        "roots": [
            {
                "path": "/" + name,
                "mode": mode,
                "materialization": "controller-private-scaffold",
            }
            for name, mode in ROOT_MODES.items()
        ],
        "directories": [
            dict(item, packages=sorted(set(item["packages"])))
            for _path, item in sorted(directories.items())
        ],
    }
    return validate(value)


def validate_manifest(inputs, details):
    """Freeze facility intent in generation identity and immutable manifest."""
    if FIELD in inputs or FIELD in details:
        value = validate(inputs.get(FIELD))
        if inputs.get(FIELD) != value or details.get(FIELD) != value:
            raise ImageBuildError(
                "runtime facility intent is not frozen in generation inputs"
            )

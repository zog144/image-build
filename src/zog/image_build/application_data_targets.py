"""Immutable application data-mount targets for published runtime images.

These paths are software-image layout, not writable data.  Box-control overlays
controller-owned persistent storage onto them and refuses to create missing targets
inside an immutable published generation.
"""
from pathlib import Path, PurePosixPath

from .errors import ImageBuildError

CONTRACT = "image-build-application-data-targets-v1"
FIELD = "application_data_targets"
MATERIALIZATION = "immutable-empty-mount-target"

_TARGETS = (
    {
        "application": "archive-mirror",
        "path": "/var/lib/archive-mirror",
        "mode": 0o755,
        "materialization": MATERIALIZATION,
    },
    {
        "application": "station-access",
        "path": "/var/lib/station-access",
        "mode": 0o755,
        "materialization": MATERIALIZATION,
    },
)


def definition():
    return {
        "contract": CONTRACT,
        "targets": [dict(item) for item in _TARGETS],
    }


def validate(value):
    expected = definition()
    if value != expected:
        raise ImageBuildError("unsupported application data target contract")
    for item in value["targets"]:
        path = PurePosixPath(item["path"])
        if (
            not item["path"].startswith("/")
            or str(path) != item["path"]
            or ".." in path.parts
            or "\x00" in item["path"]
            or type(item["mode"]) is not int
            or not 0 <= item["mode"] <= 0o7777
        ):
            raise ImageBuildError("invalid application data target")
    return value


def directories():
    """Directories added by application-image composition.

    The parent is explicit so its mode is deterministic even when the accepted
    runtime did not previously contain /var/lib.
    """
    result = {"var/lib": 0o755}
    result.update(
        (item["path"].lstrip("/"), item["mode"])
        for item in _TARGETS
    )
    return result


def bind(outputs):
    """Validate accepted output before adding empty mount targets.

    Existing empty target directories are acceptable.  Existing content, links,
    special objects, or conflicting modes are never hidden by the later writable
    mount and therefore fail publication.
    """
    if not isinstance(outputs, list):
        raise ImageBuildError("application data target outputs must be an inventory")
    by_path = {}
    for record in outputs:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ImageBuildError("invalid accepted output inventory")
        if record["path"] in by_path:
            raise ImageBuildError("duplicate accepted output path")
        by_path[record["path"]] = record

    for target in _TARGETS:
        relative = target["path"].lstrip("/")
        exact = by_path.get(relative)
        if exact is not None and (
            exact.get("kind") != "directory"
            or exact.get("mode") != target["mode"]
        ):
            raise ImageBuildError(
                "application data target conflicts with accepted runtime: "
                + target["path"]
            )

        prefix = relative + "/"
        nested = sorted(name for name in by_path if name.startswith(prefix))
        if nested:
            raise ImageBuildError(
                "application data target is not empty in accepted runtime: "
                + target["path"]
            )

        parts = PurePosixPath(relative).parts
        for index in range(1, len(parts)):
            ancestor = "/".join(parts[:index])
            record = by_path.get(ancestor)
            if record is not None and record.get("kind") != "directory":
                raise ImageBuildError(
                    "application data target parent is redirected or not a directory: /"
                    + ancestor
                )
    return definition()


def validate_root(root, value):
    validate(value)
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ImageBuildError("application image root is not a real directory")
    for target in value["targets"]:
        path = root / target["path"].lstrip("/")
        if path.is_symlink() or not path.is_dir():
            raise ImageBuildError(
                "application data target is missing or redirected: "
                + target["path"]
            )
        if path.stat().st_mode & 0o7777 != target["mode"]:
            raise ImageBuildError(
                "application data target mode differs: " + target["path"]
            )
        if any(path.iterdir()):
            raise ImageBuildError(
                "application data target is not empty: " + target["path"]
            )
        current = path.parent
        while current != root:
            if current.is_symlink() or not current.is_dir():
                raise ImageBuildError(
                    "application data target parent is redirected: "
                    + target["path"]
                )
            current = current.parent
    return value


def validate_manifest(inputs, details):
    if FIELD in inputs or FIELD in details:
        value = validate(inputs.get(FIELD))
        if details.get(FIELD) != value:
            raise ImageBuildError(
                "application data targets are not frozen in generation inputs"
            )

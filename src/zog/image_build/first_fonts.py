"""First Fonts: snapshot only the reviewed *stage* recipes, never the catalogue.

The selected Project's checked-out source is authoritative.  The three
existing final-stage definitions are real source recipes; their catalogue
parents intentionally remain non-executable metadata.  Snapshotting the
whole project/package catalogue would hit an unrelated acl:catalogue-only
entry before any Fonts stage.  This adapter selects the exact closed
libpng -> freetype -> fontconfig graph, validates independently reviewed
source pins and notices, and hands the ordinary ImageBuild scheduler a
normal immutable package directory.  No compiler command is issued here.
"""
from __future__ import annotations

from pathlib import Path

from .errors import ImageBuildError
from .metadata import literal, load_packages, names, order
from .pins import load as load_pin

TARGETS = ("libpng-final", "freetype-final", "fontconfig-final")
ENTRIES = (
    {"id": "libpng-final", "project": "libpng", "stage": "final", "recipe": "libpng/stages/final"},
    {"id": "freetype-final", "project": "freetype", "stage": "final", "recipe": "freetype/stages/final"},
    {"id": "fontconfig-final", "project": "fontconfig", "stage": "final", "recipe": "fontconfig/stages/final"},
)
EDGES = {
    "libpng-final": (),
    "freetype-final": ("libpng-final",),
    "fontconfig-final": ("freetype-final",),
}
OUTPUTS = {
    "libpng-final": (
        "usr/lib/libpng16.so",
        "usr/include/png.h",
        "usr/share/licenses/libpng/LICENSE",
    ),
    "freetype-final": (
        "usr/lib/libfreetype.so",
        "usr/include/freetype2/ft2build.h",
        "usr/share/licenses/freetype/LICENSE.TXT",
        "usr/share/licenses/freetype/docs/FTL.TXT",
        "usr/share/licenses/freetype/docs/GPLv2.TXT",
    ),
    "fontconfig-final": (
        "usr/lib/libfontconfig.so",
        "usr/bin/fc-match",
        "etc/fonts/fonts.conf",
        "usr/share/licenses/fontconfig/COPYING",
    ),
}
PLAN = "project/bootstrap/graphics-fonts.py"
PIN = "project/bootstrap/graphics-fonts-executable-pin.py"
PIN_DATE = "2026-11-01"


def eligible(repository_root, package_dir, targets):
    """Use the fixed reviewed route only for the actual Project catalogue.

    Other implicit pipeline targets retain the original PR26 handling.  In
    particular no unrelated catalogue-only package becomes executable.
    """
    root = Path(repository_root)
    catalog = root / "project" / "package"
    return (
        tuple(targets) == TARGETS
        and not catalog.is_symlink()
        and not Path(package_dir).is_symlink()
        and Path(package_dir).resolve() == catalog.resolve()
    )


def _source_contract(repository_root, catalogue):
    root = Path(repository_root)
    plan_path = root / PLAN
    pin_path = root / PIN
    for path in (root, root / "project", root / "project" / "bootstrap",
                 catalogue, plan_path, pin_path):
        if path.is_symlink():
            raise ImageBuildError("first Fonts project source traverses a symlink")
    plan = literal(plan_path)
    if (not isinstance(plan, dict) or set(plan) !=
            {"schema", "architecture", "stages", "targets"}
            or plan.get("schema") != 1
            or plan.get("stages") != list(ENTRIES)
            or plan.get("targets") != list(TARGETS)):
        raise ImageBuildError("first Fonts stage plan differs from reviewed closed sequence")
    from platform import machine
    if plan["architecture"] != machine():
        raise ImageBuildError("first Fonts stage architecture differs from Host")
    pin = load_pin(pin_path)
    if (set(pin) != {"schema", "date", "packages"}
            or pin["date"] != PIN_DATE
            or set(pin["packages"]) != {e["project"] for e in ENTRIES}):
        raise ImageBuildError("first Fonts reviewed source pin differs")
    for entry in ENTRIES:
        item = pin["packages"][entry["project"]]
        if (type(item) is not dict or set(item) != {"recipes"}
                or type(item["recipes"]) is not dict
                or set(item["recipes"]) != {entry["recipe"]}
                or type(item["recipes"][entry["recipe"]]) is not list
                or len(item["recipes"][entry["recipe"]]) != 1):
            raise ImageBuildError("first Fonts source pin lacks exact reviewed stage")
        # Independently compare the currently checked-out Project stage
        # literal with this reviewed source-pin literal, not with itself.
        stage = catalogue / entry["recipe"]
        if stage.is_symlink() or not stage.is_dir():
            raise ImageBuildError("first Fonts final-stage recipe missing or unsafe")
        source = literal(stage / "sources.py")
        if source != item["recipes"][entry["recipe"]]:
            raise ImageBuildError("first Fonts stage source URL/SHA256 differs from reviewed pin")
    return plan, pin_path, pin


def _review_selected(packages, pin):
    if set(packages) != set(TARGETS) or tuple(order(packages, TARGETS)) != TARGETS:
        raise ImageBuildError("first Fonts dependency closure or order differs")
    for entry in ENTRIES:
        name = entry["id"]
        package = packages[name]
        expected_dependencies = EDGES[name]
        if (package.build_dependencies != expected_dependencies
                or package.runtime_dependencies != expected_dependencies
                or package.test_dependencies
                or package.integration.get("project") != entry["project"]
                or package.integration.get("stage_id") != "final"):
            raise ImageBuildError(name + ": unreviewed Fonts dependency or stage")
        for phase in ("configure", "build", "test", "install"):
            if not package.steps.get(phase):
                raise ImageBuildError(name + ": executable " + phase + " recipe missing")
        if not set(OUTPUTS[name]) <= set(package.outputs):
            raise ImageBuildError(name + ": required binary/header/config/notice output missing")
        notice = package.licensing
        selected = pin["packages"][entry["project"]]["recipes"][entry["recipe"]]
        if (package.sources != tuple(selected)
                or not notice or notice.get("source") != {
                    "url": selected[0]["url"], "sha256": selected[0]["sha256"]
                } or not notice.get("evidence")
                or notice.get("status") not in ("declared", "reviewed")):
            raise ImageBuildError(name + ": exact source or notice evidence missing")
        # "declared" is legitimate for source compilation, not a claim that
        # all bundled components have received public distribution clearance.
        if any(item.get("status") == "reviewed" and not item.get("expression")
               for item in notice.get("components", [])):
            raise ImageBuildError(name + ": unsupported component notice claim")


def prepare(repository_root, package_dir, operation_directory, targets):
    """Materialize one durable, Project-local, exactly pinned stage-only source.

    An operation's old execution/receipt is never imported: each caller must
    have an independently assigned new operation ID. The normal pipeline
    subsequently captures this staged package set and its commit-pin.py
    through ImageBuild.prepare_pipeline, including a copied source inventory.
    """
    if not eligible(repository_root, package_dir, targets):
        raise ImageBuildError("first Fonts executable stages require the selected Project catalogue")
    catalogue = Path(package_dir)
    _, pin_path, pin = _source_contract(repository_root, catalogue)
    from .recipe_snapshots import materialize
    destination = Path(operation_directory) / "fonts-stage-packages"
    # The published source pin, not the historical retained compiler receipt,
    # is copied to this operation's immutable snapshot. No other Project.
    _, packages = materialize(
        catalogue, list(ENTRIES), destination,
        pin_date=PIN_DATE, monthly_pin_path=pin_path,
    )
    _review_selected(packages, pin)
    return destination

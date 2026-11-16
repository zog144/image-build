#!/usr/bin/env python3
"""Build and stage a real aggregate zog wheel from exact reviewed source trees.

Non-resident Certbot *development* input only. This is not a resident image
producer, a station assignment, an installed Host receipt, or a PyPI release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

import verify_resident_b_aggregate_installed as installed

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "project/host/nonresident-certbot-aggregate-build-v1.json"


class BuildHeld(ValueError):
    pass


def deny(message):
    raise BuildHeld("nonresident Certbot aggregate build HOLD: " + message)


def _run(args, *, cwd=None, env=None):
    try:
        subprocess.run([str(x) for x in args], cwd=cwd, env=env, timeout=600, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BuildHeld("selected build or installation command failed: " + repr(args)) from exc


def _blob(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _sha256(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(part)
    return sha.hexdigest()


def _git_head(path):
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, timeout=15
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise BuildHeld("source checkout cannot be authenticated: " + str(path)) from exc


def _clean(path):
    try:
        result = subprocess.check_output(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
            text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BuildHeld("source checkout unreadable: " + str(path)) from exc
    if result:
        deny("source checkout contains unreviewed local files: " + str(path))


def _require_original_file(root, relative, blob):
    file = root / relative
    if file.is_symlink() or not file.is_file() or _blob(file.read_bytes()) != blob:
        deny("selected original Zog base byte identity differs: " + relative)


def _selection():
    x = json.loads(SELECTION.read_text())
    selected = installed._check_selection(json.loads(installed.PIN.read_text()))
    if (set(x) != {"schema", "status", "distribution", "version",
                   "interpreter", "base", "controllers", "operations", "native", "reproducibility"}
            or x["schema"] != "zog-nonresident-certbot-aggregate-build-v1"
            or x["status"] != "REVIEWED_SOURCE_BUILD_UNACCEPTED_NATIVE_INSTALL"
            or x["distribution"] != "zog" or x["version"] != "0.1.1.dev20261116"
            or x["interpreter"] != {
                "major": 3, "minor": 12,
                "canonical_host_executable": "/usr/bin/python3.12",
                "site_packages": "usr/lib/python3.12/site-packages",
            }
            or x["base"] != {
                "repository": "zog144/zog",
                "revision": "d47d86b363824c718d9c165124cb55bbed12e0f9",
                "version": "0.1.0",
                "files": {
                    "pyproject.toml": "a1c58ab3c87ae6c6191fd6b84a9a4279eefe8910",
                    "src/zog/_release_manifest.json": "c5c3dcabbef2198c25b7952f3d6358c4b731bbe5",
                    "src/zog/__init__.py": "5c6596681d8f493b6f5e66418ca11f4aa6446713",
                    "MANIFEST.in": "f79588e6fa05d2c2611a5d66f7b96bebf47338fb",
                    "README.md": "ed02c306333a1cc9194948544d059f2008166dc6",
                },
                "component_count": 14,
            }
            or x["reproducibility"] != {
                "source_date_epoch": 1791740336,
                "normalize_source_timestamps": True,
                "require_independent_second_build": True,
            }
            or x["operations"] != {
                "base_source": "checked_out_pinned_zog",
                "replace_controller_directories": True,
                "change_metadata_version": True,
                "update_release_manifest": True,
                "discard_historical_component_directories": True,
                "no_pypi_publish": True,
            }
            or x["native"] != {
                "accepted_installed_generation": None,
                "approved_installer_receipt": None,
                "installed_on_host": False,
                "station_assignment_approved": False,
                "certificate_issuer_ready": False,
            } or set(x["controllers"]) != {"box-control", "root-control"}):
        deny("source selection or native HOLD changed")
    for name, source in selected["controllers"].items():
        want = x["controllers"].get(name)
        if want != {
            "repository": source["repository"],
            "revision": source["revision"],
            "source_prefix": source["source_prefix"],
            "selected_files": len(source["files"]),
        }:
            deny("controller aggregate source pins disagree: " + name)
    return x


def prepare(base, box, root, workspace):
    """Review inputs and create a new candidate tree, never edit checkouts."""
    selection = _selection()
    if sys.version_info[:2] != (3, 12):
        deny("aggregate producer must use Python 3.12")
    for source in (base, box, root):
        if source.is_symlink() or not source.is_dir():
            deny("source checkout unavailable or linked")
        _clean(source)
    if _git_head(base) != selection["base"]["revision"]:
        deny("wrong original released Zog baseline")
    installed.verify_sources(box, root)
    for name, blob in selection["base"]["files"].items():
        _require_original_file(base, name, blob)
    manifest_path = base / "src/zog/_release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    components = manifest.get("components")
    if (manifest.get("schema") != 1 or manifest.get("distribution") != "zog"
            or manifest.get("version") != selection["base"]["version"]
            or not isinstance(components, list)
            or len(components) != selection["base"]["component_count"]
            or len({x["program"] for x in components}) != len(components)):
        deny("base aggregate manifest is not an exact 14-component release")
    source_files = {
        "box-control": box / "box-control/src/zog/box_control",
        "root-control": root / "src/zog/root_control",
    }
    for name, source in source_files.items():
        if not source.is_dir():
            deny("missing selected complete controller source tree: " + name)
    if workspace.exists() or workspace.is_symlink():
        deny("refuse to overwrite prepared aggregate or evidence")
    if workspace.resolve().is_relative_to(base.resolve()):
        deny("aggregate workspace cannot reside in the original source checkout")
    workspace.mkdir(parents=True)
    try:
        stage = workspace / "source"
        shutil.copytree(base, stage, ignore=shutil.ignore_patterns(".git", "__pycache__",
                        "*.pyc", ".pytest_cache", "*.egg-info", "dist", "build"))
        for name, src in source_files.items():
            component = name.replace("-", "_")
            dest = stage / "src/zog" / component
            if not dest.is_dir() or dest.is_symlink():
                deny("original aggregate controller directory absent")
            shutil.rmtree(dest)
            shutil.copytree(src, dest)
        for component in components:
            if component["program"] in selection["controllers"]:
                component["revision"] = selection["controllers"][component["program"]]["revision"]
        manifest["version"] = selection["version"]
        (stage / "src/zog/_release_manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n"
        )
        init = stage / "src/zog/__init__.py"
        prior = init.read_text()
        if prior.count("__version__ = '0.1.0'") != 1:
            deny("aggregate top-level package version source differs")
        init.write_text(prior.replace("__version__ = '0.1.0'",
                                     f"__version__ = '{selection['version']}'"))
        pyproject = stage / "pyproject.toml"
        raw = pyproject.read_text()
        if raw.count('version = "0.1.0"') != 1:
            deny("unexpected source distribution version")
        raw = raw.replace('version = "0.1.0"',
                          'version = "' + selection["version"] + '"')
        pyproject.write_text(raw)
        meta = tomllib.loads(raw)["project"]
        if (meta["name"] != "zog"
                or meta["version"] != selection["version"]
                or meta["scripts"].get("box-control") != "zog.box_control.cli:main"
                or meta["scripts"].get("root-control") != "zog.root_control.daemon:main"):
            deny("aggregate metadata, entry points or version differ")
        if any(x in raw for x in ('"box-control=="', '"root-control=="')):
            deny("aggregate dependencies on superseded component distributions")
        # Normalize every packaged source timestamp to the selected release's
        # original commit time, even if source checkouts were created now.
        epoch = selection["reproducibility"]["source_date_epoch"]
        for source_entry in sorted(stage.rglob("*"), reverse=True):
            if source_entry.is_symlink():
                deny("symlinked aggregate source in staged candidate")
            if source_entry.is_file() or source_entry.is_dir():
                os.utime(source_entry, (epoch, epoch))
        os.utime(stage, (epoch, epoch))
    except BaseException:
        shutil.rmtree(workspace)
        raise
    return stage, selection


def build(base, box, root, workspace):
    stage, selection = prepare(base, box, root, workspace)
    wheel_dir = workspace / "wheel"
    wheel_dir.mkdir()
    build_environment = dict(os.environ)
    build_environment["SOURCE_DATE_EPOCH"] = str(
        selection["reproducibility"]["source_date_epoch"])
    build_environment["PYTHONHASHSEED"] = "0"
    _run([sys.executable, "-m", "build", "--no-isolation", "--wheel",
          "--outdir", wheel_dir, stage], env=build_environment)
    wheels = list(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        deny("aggregate builder produced anything but one wheel")
    wheel = wheels[0]
    expected_name = "zog-" + selection["version"] + "-py3-none-any.whl"
    if wheel.name != expected_name:
        deny("unexpected aggregate wheel artifact tag/version: " + wheel.name)
    installed_root = workspace / "installed"
    installed_root.mkdir()
    # installer 1.0.1's CLI always uses *its running* sys.executable
    # for generated entrypoints; hosted CI would embed /opt/hostedtoolcache.
    # Select the actual future nonresident Host's canonical interpreter via
    # the public WheelDestination interface, and let installer generate its
    # own installed RECORD with these final entrypoint script bytes.
    from installer import install
    from installer.__main__ import _get_scheme_dict
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile
    from installer.utils import get_launcher_kind
    destination = SchemeDictionaryDestination(
        scheme_dict=_get_scheme_dict("zog", prefix="/usr"),
        interpreter=selection["interpreter"]["canonical_host_executable"],
        script_kind=get_launcher_kind(),
        bytecode_optimization_levels=(),
        destdir=str(installed_root),
        overwrite_existing=False,
    )
    with WheelFile.open(str(wheel)) as source:
        source.validate_record(validate_contents=True)
        install(source, destination, {})
    report = installed.inspect_installed(installed_root)
    if (report["distribution"]["version"] != selection["version"]
            or report["status"] != "INSTALLED_BYTES_AND_RECORD_COHERENT_UNACCEPTED"
            or report["controller_source_pins"]["box-control"]["revision"]
               != selection["controllers"]["box-control"]["revision"]):
        deny("actual installed aggregate did not match reviewed source pins")
    report["schema"] = "zog-nonresident-certbot-aggregate-built-wheel-evidence-v1"
    report["candidate_wheel"] = {
        "file": wheel.name, "sha256": _sha256(wheel),
        "bytes": wheel.stat().st_size,
    }
    report["producer"] = {
        "python": sys.version.split()[0],
        "python_version": list(sys.version_info[:3]),
        "interpreter_expected_on_host": selection["interpreter"]["canonical_host_executable"],
        "source_commits": {
            "base": selection["base"]["revision"],
            "box-control": selection["controllers"]["box-control"]["revision"],
            "root-control": selection["controllers"]["root-control"]["revision"],
        },
        "ephemeral_build": True,
        "native_host_installed": False,
        "original_station_authority_approved": False,
        "issuer_credential_delivered": False,
    }
    receipt = workspace / "aggregate-build-evidence.json"
    receipt.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return {"candidate_wheel": str(wheel), "wheel_sha256": _sha256(wheel),
            "installed_record_sha256": report["distribution"]["RECORD_sha256"],
            "evidence": str(receipt), "native_accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--box", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.base, args.box, args.root, args.workspace)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

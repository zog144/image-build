#!/usr/bin/env python3
"""Independent Resident B controller source installation security boundary.

This verifier inspects immutable package recipes, a *source-only* systemd unit,
and (in CI) the exact pinned public upstream Python source. It never installs,
activates, imports, or executes either controller.
"""
import argparse
import ast
import configparser
import importlib.util
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "project/package"
RECORD = ROOT / "project/host/resident-b-controller-stage-contracts-v1.json"
ORIGINAL = ROOT / "tools/verify_resident_b_controller_source_stages.py"

spec = importlib.util.spec_from_file_location("resident_base_source", ORIGINAL)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

# Exact source review is pinned to the inherited candidate, not the current
# repository default branch or a caller-selected package metadata revision.
EXPECTED_UNITS = {
    "Unit": {
        "Description": "Zog root-control privileged daemon (separately authorized)",
        "After": "systemd-journald.socket",
        "RequiresMountsFor": "/state",
        "ConditionPathIsMountPoint": "/state",
    },
    "Service": {
        "Type": "exec",
        "User": "root",
        "Group": "root",
        "WorkingDirectory": "/",
        "ExecStart": "/usr/bin/root-control",
        "RuntimeDirectory": "zog",
        "RuntimeDirectoryMode": "0755",
        "UMask": "0007",
        "Restart": "no",
        "Environment": "ROOT_CONTROL_JOURNAL_BARRIER=0",
    },
}
EXPECTED_PROGRAMS = {
    "box-control": "zog.box_control.cli:main",
    "root-control": "zog.root_control.daemon:main",
}
EXPECTED_SOURCE_DEPENDENCIES = {
    "box-control": ["image-build==0.2.0.dev5", "dbus-next==0.2.3"],
    "root-control": ["box-control==0.1.0", "image-build==0.2.0.dev5", "dbus-next==0.2.3"],
}

def deny(problem):
    raise ValueError("Resident B controller install boundary NOT READY: " + problem)

def read_stage(name, filename, overrides):
    return overrides.get((name, filename),
                         base.data(PACKAGE/name/filename))

def unit_from_recipe(script):
    # Require exactly one literal file written beneath DESTDIR, with an exact
    # named terminator; don't trust an arbitrary matching snippet in comments.
    marker = 'cat > "$DESTDIR/usr/lib/systemd/system/zog-root-control.service" <<\'ZOG_ROOT_CONTROL_UNIT\'\n'
    if script.count(marker) != 1:
        deny("missing/redirected root service publication")
    body = script.split(marker, 1)[1]
    if body.count("\nZOG_ROOT_CONTROL_UNIT") != 1:
        deny("ambiguous root service heredoc")
    unit, tail = body.split("\nZOG_ROOT_CONTROL_UNIT", 1)
    if tail.strip():
        deny("commands after root service publication require separate review")
    return unit + "\n"

def verify_systemd_unit(text):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        parser.read_string(text)
    except (configparser.Error, ValueError) as exc:
        deny("malformed root-control systemd unit: " + str(exc))
    if set(parser.sections()) != set(EXPECTED_UNITS):
        deny("root-control service section, activation or identity changed")
    for section, required in EXPECTED_UNITS.items():
        actual = dict(parser.items(section))
        if actual != required:
            deny("root-control " + section + " identity, socket/STATE or execution option changed")
    # Explicitly deny source image-embedded root socket grants, activation
    # targets and state identities; those require independent host-install.
    for forbidden in ("ROOT_CONTROL_SOCKET_GID", "EnvironmentFile=",
                      "ExecStartPre=", "SocketGroup=", "SupplementaryGroups=",
                      "WantedBy=", "Alias=", "Also="):
        if forbidden in text:
            deny("root service source embedded a privileged grant: " + forbidden)
    return True

def check_source_cli(source):
    if "RootControlDaemon" in source or ".serve()" in source:
        deny("box-control one-shot CLI reclassified as daemon")
    tree = ast.parse(source)
    mains = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name == "main"]
    if len(mains) != 1:
        deny("box-control entry main absent or ambiguous")
    body = ast.get_source_segment(source, mains[0]) or ""
    if "BoxControl.discover().evaluate()" not in body or "return 0 if report.ok else 1" not in body:
        deny("box-control selected one-shot evaluator changed")

def check_source_daemon(source):
    tree = ast.parse(source)
    socket_assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DEFAULT_SOCKET"
                for target in node.targets)
    ]
    if len(socket_assignments) != 1:
        deny("root-control socket constant ambiguous")
    value = socket_assignments[0].value
    if (not isinstance(value, ast.Call)
        or not isinstance(value.func, ast.Name) or value.func.id != "Path"
        or len(value.args) != 1 or
        ast.literal_eval(value.args[0]) != "/run/zog/root-control.sock"):
        deny("privileged controller socket path changed")
    daemons = [node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "RootControlDaemon"]
    if len(daemons) != 1:
        deny("root-control privileged daemon identity changed")
    methods = {node.name: node for node in daemons[0].body
               if isinstance(node, ast.FunctionDef)}
    if not {"__init__", "_protect_socket", "serve"} <= set(methods):
        deny("root-control daemon protection methods missing")
    protect = ast.get_source_segment(source, methods["_protect_socket"]) or ""
    initial = ast.get_source_segment(source, methods["__init__"]) or ""
    main = next((ast.get_source_segment(source, n) or "" for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == "main"), "")
    required = {
        "socket mode": "os.chmod(self.socket_path, 0o660)" in protect,
        "group applied only with an explicit value": "if self.socket_group_gid is not None:" in protect,
        "no implicit group": "socket_group_gid=None" in initial,
        "positive numeric group": "socket_group_gid < 1" in initial,
        "root-owned default path": 'str(DEFAULT_SOCKET)' in main,
        "protected selected group value": 'os.environ.get("ROOT_CONTROL_SOCKET_GID")' in main,
        "group passed to daemon": "socket_group_gid=socket_group_gid" in main,
    }
    if not all(required.values()):
        deny("root-control selected socket owner/group contract changed: "+
             ",".join(k for k, passed in required.items() if not passed))

def verify(*, overrides=None, root_daemon=None, box_cli=None,
           root_pyproject=None, box_pyproject=None):
    overrides = overrides or {}
    # Existing independent original-source pin, output, notice and v2 wheel
    # tests must *also* pass. Do not substitute this for their verifier.
    base.verify(overrides=overrides)
    record = json.loads(RECORD.read_text())
    controllers = {item["id"]: item for item in record["controllers"]}
    for name in EXPECTED_PROGRAMS:
        manifest = read_stage(name, "stages/final/produce-manifest.py", overrides)
        build = read_stage(name, "stages/final/build.py", overrides)
        deps = read_stage(name, "stages/final/dependencies.py", overrides)
        integration = read_stage(name, "stages/final/integration.py", overrides)
        ctrl = controllers[name]
        path = "usr/bin/" + name
        if manifest["required"].count(path) != 1 or ctrl["executable"] != path:
            deny("controller executable path/manifest/installation binding differs: " + name)
        command = build["install"][0][-1]
        for item in ("python3.12 -I -m installer --destdir=\"$DESTDIR\" dist/*.whl",
                     'test -x "$DESTDIR/'+path+'"',
                     'test -s "$DESTDIR/usr/lib/python3.12/site-packages/zog/'+name.replace("-","_")+'/__init__.py"'):
            if item not in command:
                deny("controller installed executable/package target changed: " + name)
        # Required runtime inputs are exact: omitted (or invented) stages
        # must not be treated as satisfied by an ambient host interpreter.
        expected = base.SOURCES[name]["runtime"]
        if set(deps["runtime"]) != expected or "python-resident312-final" not in deps["runtime"]:
            deny("missing or replaced controller runtime dependency: " + name)
        if (integration.get("source_grant") is not False or
            integration.get("native_accepted") is not False or
            integration.get("auto_enable") is not False or
            integration.get("runtime_python") != "python-resident312-final"):
            deny("runtime authority or Python ABI silently promoted: " + name)
        if name == "box-control":
            if (integration.get("runtime_uid") !=
                "selected non-root project owner, authorized by host-install" or
                "HOME" not in integration.get("working_directory", "") or
                integration.get("root_control_socket") != "/run/zog/root-control.sock" or
                "protected group membership selected by installer" not in integration.get("socket_access","") or
                integration.get("unit_installed") is not False or
                integration.get("service_mode") != "one-shot-project-evaluator"):
                deny("unprivileged box-control identity/project/socket binding changed")
            if any(x in command for x in ("systemctl", "usr/lib/systemd/system/zog-box-control",
                                           "ROOT_CONTROL_SOCKET_GID", "chmod 666")):
                deny("box-control stage attempted service or privileged socket grant")
            if any("zog-box-control.service" in x for x in manifest["required"]):
                deny("box-control stage installed an unreviewed service")
        else:
            if (integration.get("runtime_uid") != "root" or
                integration.get("runtime_gid") != "root" or
                integration.get("socket_path") != "/run/zog/root-control.sock" or
                "installer-selected protected numeric GID" not in integration.get("socket_group","") or
                integration.get("unit_installed") is not True or
                integration.get("unit_path") !=
                "usr/lib/systemd/system/zog-root-control.service" or
                integration.get("unit_auto_enabled") is not False):
                deny("privileged root service/socket identity contract changed")
            if (ctrl.get("installation", {}).get("uid") != "root" or
                "STATE" not in integration.get("state","")):
                deny("root STATE requirement or UID changed")
            if ("systemctl" in command or "multi-user.target.wants" in command or
                "ROOT_CONTROL_SOCKET_GID" in command or
                "mkdir /state" in command or "install -d /state" in command):
                deny("privileged service auto-activation or STATE/group fabrication")
            unit = unit_from_recipe(command)
            verify_systemd_unit(unit)
    if root_daemon is not None:
        check_source_daemon(root_daemon)
    if box_cli is not None:
        check_source_cli(box_cli)
    for name, meta in (("root-control", root_pyproject),
                       ("box-control", box_pyproject)):
        if meta is None:
            continue
        doc = tomllib.loads(meta)
        if (doc["project"]["name"] != name or
            doc["project"]["version"] != "0.1.0" or
            doc["project"]["scripts"] != {name: EXPECTED_PROGRAMS[name]} or
            doc["project"]["dependencies"] != EXPECTED_SOURCE_DEPENDENCIES[name]):
            deny("pinned upstream executable/Requires-Dist changed: " + name)
    return {
        "source_install_contract": "EXACT_STAGE_AND_PRIVILEGE_BOUNDARY_REVIEW",
        "root_service": "DISABLED_ROOT_ONLY",
        "box_control": "ONE_SHOT_NONROOT_UNSELECTED",
        "socket_group": "NOT_PROVISIONED_BY_IMAGE",
        "state_identity": "REQUIRES_PROTECTED_NATIVE_RECEIPT",
        "native_install": "NO_GO",
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root-daemon", type=Path, required=True)
    p.add_argument("--box-cli", type=Path, required=True)
    p.add_argument("--root-pyproject", type=Path, required=True)
    p.add_argument("--box-pyproject", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(root_daemon=args.root_daemon.read_text(),
                            box_cli=args.box_cli.read_text(),
                            root_pyproject=args.root_pyproject.read_text(),
                            box_pyproject=args.box_pyproject.read_text()),
                     sort_keys=True))

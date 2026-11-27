#!/usr/bin/env python3
"""Fail-closed Resident B Python 3.12/3.15 source split, NOT native approval."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "project/package"

# Only exact required output paths are admitted. Both ABI families must coexist.
SPECS = {
    "python-final": ("3.15", ["usr/bin/python3", "usr/bin/python3.15",
                              "usr/lib/libpython3.15.so.1.0"]),
    "python-cryptography-final": ("3.15", [
        "usr/lib/python3.15/site-packages/cryptography/__init__.py"]),
    "host-identify-final": ("3.15", [
        "usr/lib/python3.15/site-packages/zog/host_identify/__init__.py"]),
    "host-install-final": ("3.15", [
        "usr/bin/host-install",
        "usr/lib/python3.15/site-packages/zog/host_install/__init__.py"]),
    "host-discover-final": ("3.15", [
        "usr/bin/host-discover", "usr/bin/host-discover-recovery",
        "usr/bin/host-discover-supervisor",
        "usr/lib/python3.15/site-packages/zog/host_discover/__init__.py"]),
    "python-resident312-final": ("3.12", [
        "usr/bin/python3.12", "usr/lib/libpython3.12.so.1.0",
        "usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so",
        "usr/lib/python3.12/lib-dynload/_sqlite3.cpython-312-x86_64-linux-gnu.so",
        "usr/lib/python3.12/lib-dynload/_hashlib.cpython-312-x86_64-linux-gnu.so"]),
    "box-control-final": ("3.12", [
        "usr/bin/box-control",
        "usr/lib/python3.12/site-packages/zog/box_control/__init__.py"]),
    "root-control-final": ("3.12", [
        "usr/bin/root-control",
        "usr/lib/python3.12/site-packages/zog/root_control/__init__.py",
        "usr/lib/systemd/system/zog-root-control.service"]),
}
HOST = {"host-identify-final", "host-install-final",
        "host-discover-final", "python-cryptography-final"}
HOST_DEPENDENCIES = {
    "host-install-final": {"build": {"python-final"}, "runtime": {"python-final"}},
    "host-identify-final": {"build": {"python-final"},
                            "runtime": {"python-final", "python-cryptography-final"}},
    "host-discover-final": {"build": {"python-final", "host-identify-final",
                                      "host-install-final"},
                            "runtime": {"python-final", "host-identify-final",
                                        "host-install-final"}},
    "python-cryptography-final": {"build": {"python-final"},
                                  "runtime": {"python-final"}},
}

def read(stage, filename):
    path = ROOT / stage[:-6] / "stages/final" / filename
    if not path.is_file() or path.is_symlink():
        raise ValueError("Resident B runtime source manifest missing/linked: " + stage)
    return ast.literal_eval(path.read_text())

def verify(*, manifests=None, dependencies=None):
    observed = {}
    for stage, (abi, expected) in SPECS.items():
        obj = (manifests[stage] if manifests is not None else
               read(stage, "produce-manifest.py"))
        if type(obj) is not dict or set(obj) != {"trees", "required"} or obj["trees"] != ["usr"]:
            raise ValueError("Resident B runtime output schema differs: " + stage)
        required = obj["required"]
        if type(required) is not list or len(required) != len(set(required)):
            raise ValueError("Resident B runtime output list invalid: " + stage)
        if not set(expected) <= set(required):
            raise ValueError("Resident B missing selected ABI output: " + stage)
        opposite = "3.12" if abi == "3.15" else "3.15"
        if any(not isinstance(p, str) or not p.startswith("usr/")
               or p.startswith("/") or ".." in Path(p).parts
               or ("usr/lib/python" + opposite + "/") in p
               or p == "usr/bin/python" + opposite
               for p in required):
            raise ValueError("Resident B crossed selected Python ABI: " + stage)
        if stage == "python-final" and "usr/bin/python3.12" in required:
            raise ValueError("Resident B alias python3 cannot be controller runtime")
        observed[stage] = {"abi": abi, "required": expected}
    for stage, expected in HOST_DEPENDENCIES.items():
        edges = (dependencies[stage] if dependencies is not None else
                 read(stage, "dependencies.py"))
        if (type(edges) is not dict or set(edges) != {"build", "runtime"}
                or any(type(edges[k]) is not list or set(edges[k]) != v
                       for k, v in expected.items())):
            raise ValueError("Resident B host Python 3.15 dependency differs: " + stage)
    for stage in ("box-control-final", "root-control-final"):
        edges = (dependencies[stage] if dependencies is not None else
                 read(stage, "dependencies.py"))
        if (type(edges) is not dict or "python-resident312-final" not in
                edges.get("build", []) or "python-resident312-final" not in
                edges.get("runtime", []) or "python-final" in
                edges.get("runtime", [])):
            raise ValueError("Resident B controller Python 3.12 dependency differs")
    return {
        "schema": "zog-resident-b-dual-python-source-boundary-v1",
        "controller_interpreter": "/usr/bin/python3.12",
        "host_default_interpreter": "/usr/bin/python3",
        "host_required_version": "3.15.0rc2",
        "controller_required_version": "3.12.16",
        "stage_count": len(SPECS),
        "stage_abi": {k: observed[k]["abi"] for k in sorted(observed)},
        "installed_shebang_elf_record_verified": False,
        "native_build_or_activation_permitted": False,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))

"""Adversarial source tests for Mesa's unadmitted native isolation gate.

Synthetic roots and receipts are untrusted test inputs, not native acceptance.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def gate():
    spec = importlib.util.spec_from_file_location(
        "mesa_isolation_adversarial", ROOT / "tools/verify_mesa_toolchain.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch, phase="mako"):
    module = gate()
    root = tmp_path / "zog"
    bins = root / "bin"
    site = root / "lib" / "python3.15" / "site-packages"
    pc = root / "lib" / "pkgconfig"
    for path in (bins, site, pc):
        path.mkdir(parents=True)
    verifier = root / "share" / "verify_mesa_toolchain.py"
    verifier.parent.mkdir()
    verifier.write_bytes(b"review-only-verifier")
    monkeypatch.setattr(module, "__file__", str(verifier))
    tools = module.TOOLS if phase == "mesa" else module.BASE_TOOLS
    mappings = {}
    for name in tools:
        path = bins / ("python3" if name == "python" else name)
        path.write_bytes(("approved-" + name).encode())
        path.chmod(0o755)
        mappings[name] = {"path": str(path),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (bins / "pkg-config").symlink_to(bins / "pkgconf")
    imports = module.MODULES if phase == "mesa" else module.BASE_MODULES
    data = {
        "schema": "zog-mesa-native-tool-receipt-v1",
        "authority": "root-control-protected-installed-bytes",
        "allowed_roots": [str(root)],
        "sysroot": str(root),
        "tools": mappings,
        "imports": {name: [str(site)] for name in imports},
        "pkgconfig_dirs": [str(pc)],
        "verifier": {"path": str(verifier),
                     "sha256": hashlib.sha256(verifier.read_bytes()).hexdigest()},
    }
    return module, root, data


@pytest.mark.parametrize("phase", ["mako", "pyyaml", "mesa"])
def test_exact_bytes_and_protected_verifier_pin_fail_closed(tmp_path, monkeypatch, phase):
    module, root, data = fixture(tmp_path, monkeypatch, phase)
    module.check_files(data, phase)
    monkeypatch.setenv("PATH", str(root / "bin"))
    module.check_invoked_commands(data)
    tool = root / "bin" / "cmake"
    tool.write_bytes(b"replaced")
    with pytest.raises(module.IsolationError, match="installed tool bytes"):
        module.check_files(data, phase)
    data["tools"]["cmake"]["sha256"] = hashlib.sha256(tool.read_bytes()).hexdigest()
    data["verifier"]["sha256"] = "0" * 64
    with pytest.raises(module.IsolationError, match="verifier source bytes"):
        module.check_files(data, phase)


def test_reject_host_binary_and_import_allowlist(tmp_path, monkeypatch):
    module, root, data = fixture(tmp_path, monkeypatch)
    foreign = tmp_path / "host-tool"
    foreign.write_bytes(b"HOST")
    data["tools"]["ninja"] = {
        "path": str(foreign), "sha256": hashlib.sha256(foreign.read_bytes()).hexdigest()}
    with pytest.raises(module.IsolationError, match="Host executable"):
        module.check_files(data, "mako")
    data["tools"]["ninja"]["path"] = str(root / "bin" / "ninja")
    data["tools"]["ninja"]["sha256"] = hashlib.sha256(
        (root / "bin" / "ninja").read_bytes()).hexdigest()
    data["imports"]["setuptools"] = [str(tmp_path)]
    with pytest.raises(module.IsolationError, match="Host module origin"):
        module.check_files(data, "mako")


@pytest.mark.parametrize("failure", ["host_module", "host_sys_path",
                                      "not_isolated", "wrong_python"])
def test_interpreter_origin_and_python_import_validation(tmp_path, monkeypatch, failure):
    module, root, data = fixture(tmp_path, monkeypatch)
    site = root / "lib" / "python3.15" / "site-packages"
    report = {
        "executable": data["tools"]["python"]["path"],
        "isolated": 1,
        "no_user_site": 1,
        "paths": [str(root / "lib" / "python3.15"), str(site)],
        "modules": {name: str(site / (name + ".py")) for name in data["imports"]},
    }
    if failure == "host_module":
        report["modules"]["setuptools"] = "/usr/lib/python3.15/site-packages/setuptools.py"
    elif failure == "host_sys_path":
        report["paths"].append("/usr/lib/python3.15/site-packages")
    elif failure == "not_isolated":
        report["isolated"] = 0
    elif failure == "wrong_python":
        report["executable"] = "/usr/bin/python3"
    invoked = []
    def fake_run(argv, **kw):
        invoked.append(argv)
        return SimpleNamespace(stdout=json.dumps(report))
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    with pytest.raises(module.IsolationError):
        module.check_imports(data)
    assert invoked and invoked[0][1:3] == ["-I", "-c"]


def test_valid_isolated_import_report_and_no_py_user_site(tmp_path, monkeypatch):
    module, root, data = fixture(tmp_path, monkeypatch)
    site = root / "lib" / "python3.15" / "site-packages"
    report = {
        "executable": data["tools"]["python"]["path"],
        "isolated": 1, "no_user_site": 1,
        "paths": [str(root / "lib" / "python3.15"), str(root / "python3.15.zip")],
        "modules": {name: str(site / (name + ".py")) for name in data["imports"]},
    }
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kw:
                        SimpleNamespace(stdout=json.dumps(report)))
    module.check_imports(data)


@pytest.mark.parametrize("key,value", [
    ("PYTHONPATH", "/host/site"), ("PYTHONSTARTUP", "/host/start.py"),
    ("PYTHONPYCACHEPREFIX", "/host/cache"), ("PIP_CONFIG_FILE", "/host/pip.conf"),
    ("LD_PRELOAD", "/host/lib.so"), ("LIBRARY_PATH", "/host/lib"),
    ("CPATH", "/host/include"), ("GCC_EXEC_PREFIX", "/host/gcc"),
    ("MESON_PACKAGE_CACHE_DIR", "/host/cache"),
    ("PKG_CONFIG_SYSTEM_LIBRARY_PATH", "/host/lib"),
    ("PKG_CONFIG_SYSTEM_INCLUDE_PATH", "/host/include"),
    ("PKG_CONFIG_PATH", "/host/lib/pkgconfig"),
])
def test_reject_host_environment_search_injection(tmp_path, monkeypatch, key, value):
    module, root, data = fixture(tmp_path, monkeypatch)
    env = {"PATH": str(root / "bin"), "PYTHONNOUSERSITE": "1",
           "PIP_NO_INDEX": "1", "PKG_CONFIG_LIBDIR": data["pkgconfig_dirs"][0],
           "PKG_CONFIG_SYSROOT_DIR": data["sysroot"]}
    module.check_environment(data, env)
    env[key] = value
    with pytest.raises(module.IsolationError):
        module.check_environment(data, env)


@pytest.mark.parametrize("bad", [
    "-I /usr/include", "-L/usr/lib", "-isystem /usr/include",
    "-iquote/usr/include", "-idirafter /tmp/host",
    "-Wl,-rpath,/usr/lib", "-Wl,--dynamic-linker=/host/ld.so",
    "@/host/response-file", "-fplugin=/host/plugin.so",
])
def test_pkgconf_flags_deny_host_paths_and_opaque_switches(tmp_path, bad):
    module = gate()
    root = tmp_path / "zog"
    (root / "include").mkdir(parents=True)
    (root / "lib").mkdir()
    module.check_pkgconf_flags(
        "safe", f"-I{root / 'include'} -L {root / 'lib'} -pthread -lsafe",
        (root.resolve(),))
    with pytest.raises(module.IsolationError):
        module.check_pkgconf_flags("attacker", bad, (root.resolve(),))


def test_private_pkgconf_dependencies_are_inspected(tmp_path, monkeypatch):
    module, root, data = fixture(tmp_path, monkeypatch, phase="mesa")
    observed = []
    def fake_run(argv, **kw):
        observed.append(argv)
        if "--variable=pcfiledir" in argv:
            return SimpleNamespace(stdout=str(root / "lib" / "pkgconfig"))
        return SimpleNamespace(stdout=f"-I{root}/include -L{root}/lib -lsafe")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.check_pkgconf(data)
    assert len(observed) == len(module.PC) * 2
    assert all("--static" in cmd for cmd in observed if "--cflags" in cmd)
    def leak_run(argv, **kw):
        if "--variable=pcfiledir" in argv:
            return SimpleNamespace(stdout=str(root / "lib" / "pkgconfig"))
        return SimpleNamespace(stdout="-L/host/private -lbad")
    monkeypatch.setattr(module.subprocess, "run", leak_run)
    with pytest.raises(module.IsolationError, match="Host pkgconf"):
        module.check_pkgconf(data)


def test_python_build_steps_cannot_import_from_checkout():
    draft = ROOT / "project" / "graphics-drafts"
    for package in ("mako", "pyyaml"):
        content = ast.literal_eval(
            (draft / package / "stages/final/build.py").read_text())
        for phase in ("build", "install"):
            command = content[phase][0][-1]
            assert "python3 -I" in command
            assert "python3 - <<" not in command
            assert "python3 -m installer" not in command
        if "prepare" in content:
            assert "python3 -I -" in content["prepare"][0][-1]

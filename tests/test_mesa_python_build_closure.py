"""Source-stage PEP517 and native toolchain no-Host fallback contracts."""
import ast
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
DRAFT=ROOT/"project/graphics-drafts"
def lit(path): return ast.literal_eval(path.read_text())

def test_draft_wheels_have_exact_source_and_existing_canonical_backends():
    pin=lit(ROOT/"project/pins/2026-11-01/graphics-source-pin.py")
    for name in ("mako","pyyaml"):
        source=lit(DRAFT/name/"stages/final/sources.py")[0]
        assert {k:source[k] for k in ("url","sha256")}==pin["packages"][name]["source"]
        assert lit(DRAFT/name/"license.py")["status"]=="unresolved"
        assert not (ROOT/"project/package"/name).exists()
    m=lit(DRAFT/"mako/stages/final/dependencies.py")
    y=lit(DRAFT/"pyyaml/stages/final/dependencies.py")
    assert "python-markupsafe-final" in m["runtime"]
    assert "python-setuptools-final" in m["build"] and "python-setuptools-final" in y["build"]
    assert "python-installer-final" in m["build"] and "python-installer-final" in y["build"]
    assert "python-wheel-final" in y["build"]
    upstream=lit(ROOT/"project/package/python-markupsafe/upstream.py")
    assert len(upstream["sha256"])==64
    for name in ("python", "cmake", "ninja", "meson", "pkgconf", "python-setuptools"):
        assert (ROOT/"project/package"/name/"upstream.py").exists()

def test_pure_python_pyyaml_source_transform_is_explicit():
    m=lit(DRAFT/"mako/stages/final/build.py")
    y=lit(DRAFT/"pyyaml/stages/final/build.py")
    for item in (m,y):
        assert "verify_mesa_toolchain.py --attestation" in item["build"][0][-1]
        assert item["environment"]["PIP_NO_INDEX"]=="1"
        assert item["environment"]["PYTHONNOUSERSITE"]=="1"
    assert "setuptools.build_meta" in m["build"][0][-1]
    assert "_pyyaml_pep517" in y["build"][0][-1]
    assert "Cython" in y["prepare"][0][-1] and "original_sha256" in y["prepare"][0][-1]
    assert "PYYAML_FORCE_LIBYAML" in y["environment"]
    assert "none-any.whl" in y["test"][0][-1]

def load():
    spec=importlib.util.spec_from_file_location("mesa_gate",ROOT/"tools/verify_mesa_toolchain.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_no_host_override_even_when_tools_exist(tmp_path):
    module=load()
    root=tmp_path/"zog"; root.mkdir()
    binpath=root/"bin"; binpath.mkdir()
    pc=root/"pkgconfig"; pc.mkdir()
    data={"allowed_roots":[str(root)],"pkgconfig_dirs":[str(pc)],"sysroot":str(root)}
    env={"PYTHONNOUSERSITE":"1","PIP_NO_INDEX":"1",
         "PKG_CONFIG_LIBDIR":str(pc),"PKG_CONFIG_SYSROOT_DIR":str(root),
         "PATH":str(binpath)}
    module.check_environment(data,env)
    for key,value in (("PYTHONPATH","/usr/lib/python3.12"),("LD_LIBRARY_PATH","/host/lib"),
                      ("PKG_CONFIG_PATH","/host/pkg"),("PIP_INDEX_URL","https://host"),
                      ("PATH",str(binpath)+":/usr/bin")):
        bad=dict(env);bad[key]=value
        with pytest.raises(module.IsolationError): module.check_environment(data,bad)
    bad=dict(env);bad["PKG_CONFIG_LIBDIR"]="/usr/lib/pkgconfig"
    with pytest.raises(module.IsolationError): module.check_environment(data,bad)

def test_no_untrusted_receipt_or_host_file(tmp_path):
    module=load()
    root=tmp_path/"root";root.mkdir()
    with pytest.raises(module.IsolationError):
        module.roots_for({"schema":"zog-mesa-native-tool-receipt-v1",
                          "authority":"untrusted","allowed_roots":[str(root)]})
    with pytest.raises(module.IsolationError):
        module.roots_for({"schema":"zog-mesa-native-tool-receipt-v1",
                          "authority":"root-control-protected-installed-bytes",
                          "allowed_roots":["/"]})

def test_all_six_still_rights_and_publication_held():
    rights=json.loads((DRAFT/"rights-admission-evidence.json").read_text())
    assert rights["status"].endswith("NO-GO")
    assert not rights["canonical_admitted"] and not rights["rights_approved"]
    assert set(rights["components"])=={"llvm","mesa","libdrm","libxshmfence","libXxf86vm","mesa-demos"}
    for name in rights["components"]:
        assert lit(DRAFT/name/"license.py")["status"]=="unresolved"
        assert not (ROOT/"project/package"/name).exists()

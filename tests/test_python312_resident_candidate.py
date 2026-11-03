"""Held Python 3.12.16 source candidate and negative SSL/SQLite/ABI checks."""
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("python312_candidate",
    ROOT/"tools/verify_python312_resident_candidate.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_official_31216_candidate_does_not_repin_original_python():
    result=m.check()
    assert result["selection"]=="HOLD" and result["native"]=="UNVERIFIED"
    assert m.load("package.py")["status"]=="catalogue-only"
    original=(ROOT/"project/package/python/stages/final/upstream.py").read_text()
    assert "3.15.0rc2" in original and "3.12.16" not in original

@pytest.mark.parametrize("changed",["missing_ssl","missing_sqlite","wrong_soabi",
    "incorrect_python_path","missing_libpython","wrong_extension_abi"])
def test_wrong_or_missing_compiled_extension_output_rejected(changed):
    record=m.load("stages/final/produce-manifest.py")
    mapping={"missing_ssl":"_ssl.","missing_sqlite":"_sqlite3.",
      "incorrect_python_path":"usr/bin/python3.12","missing_libpython":"libpython3.12"}
    if changed=="wrong_soabi":
        record["required"]=[s.replace("cpython-312","cpython-315") for s in record["required"]]
    elif changed=="wrong_extension_abi":
        record["required"]=[s.replace("x86_64-linux-gnu","aarch64-linux-gnu") for s in record["required"]]
    else:
        record["required"]=[s for s in record["required"] if mapping[changed] not in s]
    with pytest.raises(ValueError,match="ABI output"):
        m.check(outputs=record)

@pytest.mark.parametrize("target",["openssl-final","sqlite-final"])
def test_no_undeclared_ssl_or_sqlite_predecessor(target):
    record=m.load("stages/final/dependencies.py")
    record["build"].remove(target)
    with pytest.raises(ValueError,match="OpenSSL/SQLite selected-stage"):
        m.check(deps=record)
    record=m.load("stages/final/dependencies.py")
    record["runtime"].remove(target)
    with pytest.raises(ValueError,match="OpenSSL/SQLite selected-stage"):
        m.check(deps=record)

def test_wrong_upstream_source_or_unapproved_rights_fail():
    src=m.load("stages/final/sources.py")
    src[0]["sha256"]="a"*64
    with pytest.raises(ValueError,match="incorrect upstream"):
        m.check(sources=src)
    rights=m.load("license.py")
    rights["status"]="approved"
    with pytest.raises(ValueError,match="falsely approved"):
        m.check(license=rights)

def test_host_pkgconfig_and_untrusted_lib_search_path_denied():
    script=m.load("stages/final/build.py")
    script["environment"]["PKG_CONFIG_LIBDIR"]="/usr/local/lib/pkgconfig"
    with pytest.raises(ValueError,match="host pkg-config"):
        m.check(build=script)
    script=m.load("stages/final/build.py")
    script["configure"][0][-1]+="\nexport HOST_LIB=/usr/lib\n"
    with pytest.raises(ValueError,match="host library"):
        m.check(build=script)

def test_stage_cannot_claim_native_acceptance_or_compiler_approval():
    for field,value in (("native_compiled",True),
                        ("submission_allowed",True),
                        ("accepted_generation_receipts",{"issuer":"self","accepted":True}),
                        ("no_host_fallback",False),
                        ("soabi","cpython-315-x86_64-linux-gnu")):
        record=m.load("stages/final/integration.py")
        record[field]=value
        with pytest.raises(ValueError,match="premature admission"):
            m.check(integration=record)

def test_runtime_import_probe_and_strict_openssl_headers_are_required():
    script=m.load("stages/final/build.py")
    script["test"][0][-1]=script["test"][0][-1].replace(",_ssl,_sqlite3,_hashlib","")
    with pytest.raises(ValueError,match="module-import acceptance"):
        m.check(build=script)
    script=m.load("stages/final/build.py")
    script["configure"][0][-1]=script["configure"][0][-1].replace("/usr/include/openssl/ssl.h","/host/usr/include/openssl/ssl.h")
    with pytest.raises(ValueError,match="selected-root|configure ABI"):
        m.check(build=script)

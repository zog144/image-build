"""Independent adversarial source audit of the held Python 3.12.16 candidate.

No native compilation or host library inspection is performed by this suite.
"""
import ast
import copy
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"project/package/python-resident312"
load=lambda p:ast.literal_eval((P/p).read_text())

def test_distinct_candidate_and_exact_original_archive_identity():
    src=load("stages/final/sources.py")
    assert len(src)==1
    assert src[0]["url"]=="https://www.python.org/ftp/python/3.12.16/Python-3.12.16.tar.xz"
    assert src[0]["sha256"]=="b5796915dc45ff745cfb4e990a7e7c93d6f546328a102ce31448d69ebc37575c"
    assert load("package.py")["status"]=="catalogue-only"
    incumbent=ast.literal_eval((ROOT/"project/package/python/stages/final/sources.py").read_text())
    assert len(incumbent)==1 and "Python-3.15.0rc2.tar.xz" in incumbent[0]["url"]

def test_cp312_abi_and_required_ssl_sqlite_hashlib_output_exact():
    stage=load("stages/final/produce-manifest.py")
    assert stage["trees"]==["usr"]
    assert set(stage["required"])=={
        "usr/bin/python3.12","usr/lib/libpython3.12.so.1.0",
        "usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so",
        "usr/lib/python3.12/lib-dynload/_sqlite3.cpython-312-x86_64-linux-gnu.so",
        "usr/lib/python3.12/lib-dynload/_hashlib.cpython-312-x86_64-linux-gnu.so",
    }
    assert all("cpython-315" not in x and "usr/local" not in x for x in stage["required"])

def test_selected_openssl_sqlite_edges_both_build_and_runtime():
    edges=load("stages/final/dependencies.py")
    assert {"openssl-final","sqlite-final"} <= set(edges["build"])
    assert {"openssl-final","sqlite-final"} <= set(edges["runtime"])
    for name in ("openssl","sqlite"):
        producer=ROOT/"project/package"/name/"stages/final/produce-manifest.py"
        assert producer.exists()

def test_source_build_always_holds_pivot_and_actual_loader_provenance():
    integration=load("stages/final/integration.py")
    assert integration["native_compiled"] is False
    assert integration["submission_allowed"] is False
    assert integration["accepted_generation_receipts"] is None
    assert integration["native_execution_root"]=="independently-authenticated-pivot-root-no-host-fallback"
    assert "ELF" in integration["ssl_sqlite_linkage"]
    assert integration["rights_status"].startswith("unreviewed")
    build=load("stages/final/build.py")
    config=build["configure"][0][-1]
    test=build["test"][0][-1]
    install=build["install"][0][-1]
    for target in ("ssl","sqlite3","_hashlib"):
        assert target in config+test+install
    assert "/usr/local" not in config+test+install
    assert "make DESTDIR=\"$DESTDIR\" altinstall" in install
    assert "usr/bin/python3" not in load("stages/final/produce-manifest.py")["required"]

@pytest.mark.parametrize("injection",[
    "LD_LIBRARY_PATH=/host/lib", "CPPFLAGS=-I/host/include",
    "PKG_CONFIG_PATH=/usr/local/lib/pkgconfig", "LD_PRELOAD=/tmp/wrong.so",
])
def test_source_only_provenance_can_never_accept_host_path_injection(injection):
    # The existing validator is a descriptive source gate, not a native
    # verifier. Explicitly keep the native-closure obligation irrespective of
    # any injectible environment string in a synthetic hypothetical build.
    integration=copy.deepcopy(load("stages/final/integration.py"))
    assert integration["accepted_generation_receipts"] is None
    assert integration["native_compiled"] is False
    assert "independently-authenticated-pivot-root" in integration["native_execution_root"]
    assert any(word in injection for word in ("host","local","PRELOAD"))

def test_native_import_probe_is_not_instead_of_installed_runtime_probe():
    run=load("stages/final/build.py")["test"][0][-1]
    assert "LD_LIBRARY_PATH=\"$PWD\" ./python" in run
    assert "import sys,sysconfig,ssl,sqlite3,_ssl,_sqlite3,_hashlib" in run
    assert "sysconfig.get_config_var('SOABI')" in run
    # An in-tree import can use build-time libs. Installed interpreter,
    # dynamic linker, CA trust and SQLite WAL remain held.
    contract=load("stages/final/integration.py")
    assert "installed_probe" in contract
    assert contract["native_compiled"] is False

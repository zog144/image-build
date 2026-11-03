#!/usr/bin/env python3
"""Read-only version/ABI/source-contract verifier for held Python 3.12.16."""
import ast
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"project/package/python-resident312"
URL="https://www.python.org/ftp/python/3.12.16/Python-3.12.16.tar.xz"
SHA="b5796915dc45ff745cfb4e990a7e7c93d6f546328a102ce31448d69ebc37575c"
ABI="cpython-312-x86_64-linux-gnu"
REQUIRED=frozenset((
    "usr/bin/python3.12","usr/lib/libpython3.12.so.1.0",
    "usr/lib/python3.12/lib-dynload/_ssl."+ABI+".so",
    "usr/lib/python3.12/lib-dynload/_sqlite3."+ABI+".so",
    "usr/lib/python3.12/lib-dynload/_hashlib."+ABI+".so",
))
BUILD=frozenset(("pkgconf-final","openssl-final","sqlite-final",
                 "libffi-final","expat-final","gdbm-final"))
RUNTIME=frozenset(("openssl-final","sqlite-final","libffi-final","expat-final","gdbm-final"))
ALL_FIELDS=frozenset(("schema","status","source_version","target_architecture","soabi",
    "required_selected_predecessors","accepted_generation_receipts",
    "native_execution_root","tool_provenance","no_host_fallback","ssl_sqlite_linkage",
    "installed_probe","package_collision","rights_status","native_compiled","submission_allowed"))

def load(name):
    return ast.literal_eval((C/name).read_text())

def _require(value,message):
    if not value:
        raise ValueError("Python 3.12 source candidate NO-GO: "+message)

def check(*, package=None,sources=None,deps=None,outputs=None,build=None,
          integration=None,license=None):
    package=package if package is not None else load("package.py")
    sources=sources if sources is not None else load("stages/final/sources.py")
    deps=deps if deps is not None else load("stages/final/dependencies.py")
    outputs=outputs if outputs is not None else load("stages/final/produce-manifest.py")
    build=build if build is not None else load("stages/final/build.py")
    integration=integration if integration is not None else load("stages/final/integration.py")
    license=license if license is not None else load("license.py")
    _require(type(package) is dict and
             package.get("status")=="catalogue-only" and
             package.get("production_python_final_untouched") is True and
             package.get("version")=="3.12.16" and package.get("target_abi")==ABI,
             "existing Python selection must not change")
    _require(type(sources) is list and len(sources)==1 and type(sources[0]) is dict
             and sources[0]=={"url":URL,"sha256":SHA,"destination":"upstream","archive":True},
             "incorrect upstream Python XZ checksum or source URL")
    _require(type(deps) is dict and set(deps)=={"build","runtime"} and
             set(deps["build"])==BUILD and set(deps["runtime"])==RUNTIME and
             len(deps["build"])==len(BUILD) and len(deps["runtime"])==len(RUNTIME),
             "missing exact OpenSSL/SQLite selected-stage dependency")
    _require(type(outputs) is dict and set(outputs)=={"trees","required"}
             and outputs["trees"]==["usr"] and set(outputs["required"])==REQUIRED
             and len(outputs["required"])==len(REQUIRED),
             "missing or wrong _ssl/_sqlite3 3.12 native ABI output")
    _require(type(integration) is dict and set(integration)==ALL_FIELDS and
             integration.get("status")=="source-candidate-native-NO-GO" and
             integration.get("source_version")=="3.12.16" and
             integration.get("target_architecture")=="x86_64" and
             integration.get("soabi")==ABI and
             integration.get("required_selected_predecessors")==["openssl-final","sqlite-final"] and
             integration.get("accepted_generation_receipts") is None and
             integration.get("native_compiled") is False and
             integration.get("submission_allowed") is False and
             integration.get("no_host_fallback") is True and
             integration.get("native_execution_root")=="independently-authenticated-pivot-root-no-host-fallback" and
             integration.get("rights_status")=="unreviewed-python312-original-archive-members-and-generated-files",
             "missing protected provenance or premature admission")
    _require(type(license) is dict and license.get("status")=="unresolved"
             and license.get("evidence")==[] and license.get("source")=={"url":URL,"sha256":SHA},
             "source bytes/rights falsely approved")
    _require(type(build) is dict and set(build)=={"configure","build","test","install","environment"},
             "candidate build phases omitted")
    def script(phase):
        steps=build[phase]
        _require(type(steps) is list and len(steps)==1
                 and steps[0][:5]==["/bin/bash","-eu","-o","pipefail","-c"],
                 "selected strict build phase changed: "+phase)
        return steps[0][5]
    configure=script("configure"); test=script("test"); install=script("install")
    _require(all(re.search(r"(?m)^test -s " + re.escape(header) + r"$", configure)
             for header in ("/usr/include/openssl/ssl.h", "/usr/include/sqlite3.h"))
             and all(re.search(r"(?m)^test -e " + re.escape(lib) + r"$", configure)
                     for lib in ("/usr/lib/libssl.so", "/usr/lib/libcrypto.so",
                                 "/usr/lib/libsqlite3.so")),
             "selected-root OpenSSL/SQLite header or ELF paths modified")
    _require(all(term in configure for term in (
        "Python-3.12.16", "/usr/include/openssl/ssl.h", "/usr/include/sqlite3.h",
        "/usr/lib/libssl.so","/usr/lib/libsqlite3.so",
        "--with-openssl=/usr","--with-openssl-rpath=no",
        "MODULE__SSL_STATE=yes","MODULE__SQLITE3_STATE=yes")),
        "OpenSSL/SQLite configure ABI or headers incomplete")
    _require(all(term in test for term in (
        "import sys,sysconfig,ssl,sqlite3,_ssl,_sqlite3,_hashlib",
        "(3,12,16)","cpython-312-x86_64-linux-gnu","sqlite3.connect")),
        "native build module-import acceptance missing")
    _require("make DESTDIR=\"$DESTDIR\" altinstall" in install
             and all(path in install for path in REQUIRED if path!="usr/lib/python3.12/lib-dynload/_hashlib."+ABI+".so")
             and 'test -n "${DESTDIR:-}"' in install,
             "stage-to-DESTDIR install or required ABI output not checked")
    env=build["environment"]
    _require(type(env) is dict and env.get("PKG_CONFIG_LIBDIR")=="/usr/lib/pkgconfig:/usr/share/pkgconfig"
             and env.get("PKG_CONFIG_SYSROOT_DIR")=="/"
             and env.get("PYTHONNOUSERSITE")=="1" and env.get("PIP_NO_INDEX")=="1",
             "uncontrolled host pkg-config/python fallback")
    _require(not any(unsafe in "\\n".join((configure,test,install)) for unsafe in
                     ("/host/", "/usr/local", "LD_PRELOAD=", "PKG_CONFIG_PATH="))
             and
             "HOST_LIB" not in json.dumps(build) and
             "PYTHONPATH" not in env,
             "host library/header/module fallback allowed")
    return {"source_candidate":"SCHEMA_AND_SOURCE_CONSISTENT","native":"UNVERIFIED",
            "candidate_version":"3.12.16","ABI":ABI,"source_sha256":SHA,
            "selection":"HOLD"}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

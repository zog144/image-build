#!/usr/bin/env python3
"""Read-only original-source inspection for separate Resident B cp312 candidates.

No PEP517 imports, builds, install, native work, Host identity or redistribution grant.
"""
import ast
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath
from email.parser import BytesParser
ROOT=Path(__file__).resolve().parents[1]
KEYS=("flit-core","installer","packaging","wheel","setuptools","dbus-next","image-build")
LIMIT=24*1024*1024
def observe(key,opener=urllib.request.urlopen):
    pkg="resident312-"+key
    stage=ROOT/"project/package"/pkg/"stages/final"
    src=ast.literal_eval((stage/"sources.py").read_text())[0]
    expected=ast.literal_eval((ROOT/"project/package"/pkg/"package.py").read_text())
    req=urllib.request.Request(src["url"],headers={
        "User-Agent":"Zog-ResidentB-source-inspection/1","Accept":"application/octet-stream"})
    try:
        with opener(req,timeout=50) as f:
            raw=f.read(LIMIT+1)
    except Exception as exc:
        raise RuntimeError("SOURCE_ACQUISITION_FAILED "+pkg+" "+str(exc)) from exc
    if not raw or len(raw)>LIMIT:
        raise ValueError("source archive missing or size exceeds bound: "+pkg)
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=src["sha256"] or actual!=expected["original_source_sha256"]:
        raise ValueError("original archive SHA-256 differs: "+pkg)
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as archive:
        members={}
        for m in archive:
            p=PurePosixPath(m.name)
            if not p.parts or p.is_absolute() or ".." in p.parts or m.issym() or m.islnk():
                raise ValueError("unsafe source archive member: "+pkg)
            if m.isfile():members["/".join(p.parts[1:])]=m
        if not members:raise ValueError("no regular files in original archive")
        def digest(path):
            with archive.extractfile(members[path]) as f:
                data=f.read()
            return hashlib.sha256(data).hexdigest(),data
        has_pyproject="pyproject.toml" in members
        backend=None
        dynamic=[]
        if has_pyproject:
            import tomllib
            _,data=digest("pyproject.toml")
            meta=tomllib.loads(data.decode())
            backend=meta.get("build-system",{}).get("build-backend")
            dynamic=meta.get("project",{}).get("dynamic",[])
        info=None
        for name in ("PKG-INFO",):
            if name in members:
                _,data=digest(name)
                info=BytesParser().parsebytes(data)
        if info:
            original_name=info.get("Name")
            original_version=info.get("Version")
        elif has_pyproject:
            original_name=meta.get("project",{}).get("name")
            original_version=meta.get("project",{}).get("version")
        else:
            original_name=original_version=None
        license_names=sorted(x for x in members if
            x.rsplit("/",1)[-1].upper().startswith(("LICENSE","COPYING","NOTICE")))
        return dict(package=pkg,archive_sha256=actual,
            original_name=original_name,original_version=original_version,
            pyproject=has_pyproject,backend=backend,dynamic_fields=dynamic,
            license_members=license_names[:15],
            original_pyproject_sha256=digest("pyproject.toml")[0] if has_pyproject else None,
            inspected_source_only=True,accepted_native=False)
def main():
    for key in KEYS:
        print("ZOG_RESIDENT312_ORIGINAL "+json.dumps(observe(key),sort_keys=True),flush=True)
if __name__=="__main__":main()

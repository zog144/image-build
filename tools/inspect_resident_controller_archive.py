#!/usr/bin/env python3
"""Inspect immutable public controller archive bytes; read-only GitHub network.

This is an archive-integrity observation, not package selection or licensing approval.
Do not use generated Git commits as substitutes for downloaded SHA-256 bytes.
"""
import hashlib
import io
import json
import pathlib
import tarfile
import urllib.request

SOURCES={
    "box-control":("b513a9bde79135c7569adc7cadb4d45a163c7841",
                   "box-control/pyproject.toml"),
    "root-control":("0c217182d25f05b9cc0f7528ee614bb5669370d3",
                    "pyproject.toml"),
}
MAX_BYTES=30*1024*1024

def inspect(name, revision, marker, opener=urllib.request.urlopen):
    url=f"https://api.github.com/repos/zog144/{name}/tarball/{revision}"
    req=urllib.request.Request(url,headers={
        "User-Agent":"Zog-public-source-integrity/1",
        "Accept":"application/vnd.github+json",
    })
    with opener(req,timeout=45) as stream:
        raw=stream.read(MAX_BYTES+1)
    if not raw or len(raw)>MAX_BYTES:
        raise ValueError("source archive missing or exceeds 30 MiB")
    digest=hashlib.sha256(raw).hexdigest()
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as archive:
        regular={}
        for item in archive:
            p=pathlib.PurePosixPath(item.name)
            if not p.parts or ".." in p.parts or p.is_absolute() or item.issym() or item.islnk():
                raise ValueError("unsafe original archive member")
            if item.isfile():
                regular["/".join(p.parts[1:])]=item
        if marker not in regular or "LICENSE" not in regular or "THIRD-PARTY-NOTICES.md" not in regular:
            raise ValueError("archive lacks expected pinned public project/license members")
        def member_digest(path):
            with archive.extractfile(regular[path]) as stream:
                return hashlib.sha256(stream.read()).hexdigest()
        root_dir=next(iter(archive.getmembers())).name.split("/")[0]
        return {"package":name,"commit":revision,"url":url,
                "archive_sha256":digest,"bytes":len(raw),
                "archive_root":root_dir,
                "project_member":marker,
                "pyproject_sha256":member_digest(marker),
                "license_sha256":member_digest("LICENSE"),
                "third_party_notice_sha256":member_digest("THIRD-PARTY-NOTICES.md"),
                "source_only":True,"redistribution_authorized":False}

def main():
    for name,(revision,marker) in SOURCES.items():
        print("ZOG_CONTROLLER_ORIGINAL",json.dumps(inspect(name,revision,marker),sort_keys=True),flush=True)
if __name__=="__main__":
    main()

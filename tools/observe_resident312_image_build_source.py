#!/usr/bin/env python3
"""Read-only immutable source archive witness; no package publication or execution."""
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import PurePosixPath
REV="1f07e83dbd80dacb9bed0d6494c697375f0e26cd"
URL=f"https://api.github.com/repos/zog144/image-build/tarball/{REV}"
def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"Zog-ResidentB-source-review/1","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=50) as response:
        raw=response.read(24*1024*1024+1)
    if not raw or len(raw)>24*1024*1024:raise ValueError("image-build source archive too large")
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as archive:
        members={}
        for member in archive:
            path=PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
                raise ValueError("unsafe source member")
            if member.isfile():members["/".join(path.parts[1:])]=member
        required=["pyproject.toml","LICENSE","THIRD-PARTY-NOTICES.md","src/zog/image_build/__init__.py"]
        if any(name not in members for name in required):raise ValueError("missing expected original interface source")
        digests={}
        for name in required:
            with archive.extractfile(members[name]) as f:digests[name]=hashlib.sha256(f.read()).hexdigest()
        with archive.extractfile(members["pyproject.toml"]) as f:
            import tomllib
            info=tomllib.loads(f.read().decode())["project"]
            assert info["name"]=="image-build" and info["version"]=="0.2.0.dev5"
        print("ZOG_PINNED_RESIDENT312_IMAGE_BUILD_SOURCE "+json.dumps({
          "revision":REV,"archive_sha256":hashlib.sha256(raw).hexdigest(),"url":URL,
          "member_digests":digests,"status":"observed-source-only-no-native-acceptance"},sort_keys=True))
if __name__=="__main__":main()

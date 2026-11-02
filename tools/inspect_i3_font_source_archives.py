#!/usr/bin/env python3
"""Original archive and embedded license-member inspection, no native acceptance."""
import argparse
import hashlib
import io
import json
import tarfile
from urllib.request import urlopen, Request

SELECTED={
 "harfbuzz":("11.5.0","https://github.com/harfbuzz/harfbuzz/releases/download/11.5.0/harfbuzz-11.5.0.tar.xz"),
 "fribidi":("1.0.16","https://github.com/fribidi/fribidi/releases/download/v1.0.16/fribidi-1.0.16.tar.xz"),
 "libXrender":("0.9.12","https://www.x.org/releases/individual/lib/libXrender-0.9.12.tar.xz"),
}
def inspect(name,blob):
    version,url=SELECTED[name]
    rights={}
    inputs={}
    with tarfile.open(fileobj=io.BytesIO(blob),mode="r:xz") as archive:
        for member in archive.getmembers():
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise ValueError("unsafe original member")
            if not member.isfile() or member.size>1*1024*1024:
                continue
            relative=member.name.partition("/")[2]
            if relative in ("COPYING","COPYING.LESSER","COPYING.LIB","COPYING.GPL",
                            "LICENSE","LICENSE.md","LICENSE.txt") or relative.startswith("LICENSES/"):
                rights[member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            if relative in ("meson.build","meson.options","meson_options.txt","configure.ac","Makefile.am"):
                inputs[member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    if not rights or not inputs:raise ValueError("missing original rights or build metadata")
    return {"package":name,"version":version,"url":url,"sha256":hashlib.sha256(blob).hexdigest(),
            "notice_members":rights,"build_inputs":inputs,
            "status":"source-observed-only-no-native-rights-authorization"}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--package",choices=sorted(SELECTED),required=True)
    name=p.parse_args().package
    with urlopen(Request(SELECTED[name][1],headers={"User-Agent":"Zog-source-inspection/1"}),timeout=90) as resp:
        data=resp.read(18*1024*1024+1)
    if len(data)>18*1024*1024:raise ValueError("archive exceeds read bound")
    print(json.dumps(inspect(name,data),sort_keys=True))

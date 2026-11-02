#!/usr/bin/env python3
"""Read-only original source and primary notice audit for VNC predecessors."""
import hashlib,io,json,tarfile
from urllib.request import Request,urlopen

SOURCES={
 "pixman":{"version":"0.46.4","url":"https://cairographics.org/releases/pixman-0.46.4.tar.xz",
           "expected_sha256":None,
           "expected_sha512":"83b133e7969ba34f883f4e08dcc5d388c4397f43ce836c191c05945fe77c16ff501d531600780c12678a0d08105828a6bdeff2156b63f9c1a84087bc7f40ae9f"},
 "libjpeg-turbo":{"version":"3.2.0","url":"https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.2.0/libjpeg-turbo-3.2.0.tar.gz",
           "expected_sha256":"6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e"}
}
def inspect(name,data):
    spec=SOURCES[name]
    sha=hashlib.sha256(data).hexdigest()
    if spec.get("expected_sha256") and sha!=spec["expected_sha256"]:
        raise ValueError("unexpected exact original archive SHA-256")
    if spec.get("expected_sha512") and hashlib.sha512(data).hexdigest()!=spec["expected_sha512"]:
        raise ValueError("unexpected original pixman archive SHA-512")
    notices={}
    build={}
    with tarfile.open(fileobj=io.BytesIO(data),mode="r:*") as tar:
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in m.name.split("/"):
                raise ValueError("unsafe archive member")
            if not m.isfile() or m.size>1024*1024:
                continue
            rel=m.name.partition("/")[2]
            if rel in ("COPYING","COPYING.md","LICENSE","LICENSE.md","LICENSE.ijg","LICENSE.txt"):
                notices[m.name]=hashlib.sha256(tar.extractfile(m).read()).hexdigest()
            if rel in ("meson.build","meson_options.txt","CMakeLists.txt"):
                build[m.name]=hashlib.sha256(tar.extractfile(m).read()).hexdigest()
    if not notices or not build:
        raise ValueError("original upstream notice/build metadata not found")
    return {"name":name,"version":spec["version"],"url":spec["url"],
            "archive_sha256":sha,"notices":notices,"build_metadata":build,
            "state":"upstream-source-observed-not-native-or-redistribution-approved"}
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--package",choices=sorted(SOURCES),required=True)
    name=p.parse_args().package;spec=SOURCES[name]
    with urlopen(Request(spec["url"],headers={"User-Agent":"Zog-original-source/1"}),timeout=60) as response:
        b=response.read(9*1024*1024)
    if len(b)>=9*1024*1024:raise ValueError("archive exceeds inspection bound")
    print(json.dumps(inspect(name,b),sort_keys=True))

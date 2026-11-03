#!/usr/bin/env python3
"""Read-only original source and primary notice audit for VNC predecessors."""
import hashlib,io,json,tarfile
from urllib.request import Request,urlopen

SOURCES={
 "pixman":{"version":"0.46.4","url":"https://cairographics.org/releases/pixman-0.46.4.tar.xz",
           "expected_sha256":None,
           "expected_sha512":"83b133e7969ba34f883f4e08dcc5d388c4397f43ce836c191c05945fe77c16ff501d531600780c12678a0d08105828a6bdeff2156b63f9c1a84087bc7f40ae9f"},
 "libjpeg-turbo":{"version":"3.2.0","url":"https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.2.0/libjpeg-turbo-3.2.0.tar.gz",
           "expected_sha256":"6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e"},
 "turbovnc":{"version":"3.3.1","url":"https://github.com/TurboVNC/turbovnc/releases/download/3.3.1/turbovnc-3.3.1.tar.gz",
           "expected_sha256":"9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"}
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
    source_feature_checks={}
    expected_original_cmake={
        "CMakeLists.txt":"9588094f823e86b8e3182522e0cfbaa3f473fb11e970d389e8c62c3dd8ab2338",
        "unix/CMakeLists.txt":"993d560352f43e04a916d1a3ca48b1a633689d4254abc4891f3be420bcdf2caf",
        "unix/Xvnc/CMakeLists.txt":"54444d6b340213218d358bec0d10d4633b9683431567f39e3e089200e515d4a3",
        "unix/Xvnc/programs/Xserver/CMakeLists.txt":"4e52b66d996039bb1450690cc694691670c8f5c4cad387d8f057eeaa28feede4",
    }
    expected_notices={
        "LICENSE.txt":"8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643",
        "unix/Xvnc/programs/Xserver/COPYING":"4cc0447a22635c7b2f1a93fec4aa94f1970fadeb72a063de006b51cf4963a06f",
        "unix/Xvnc/lib/libsha1/COPYING":"4c387926596bfeacc5b72ebeb96ab36c299a07568e18592c727a6c11dd512c20",
        "unix/Xvnc/lib/zlib-ng/LICENSE.md":"6c9f0d975b41afaa34d22f55bb8986ce69e5cb7ad327cb2b28820cd425edf5ee",
    }
    review_paths={
        "unix/Xvnc/lib/CMakeLists.txt": (b"if(TVNC_ZLIBNG)",b"ExternalProject_Add(zlib-ng",b"add_subdirectory(libsha1)"),
        "unix/Xvnc/programs/Xserver/hw/vnc/CMakeLists.txt": (b"option(TVNC_USEPAM",b"if(TVNC_DRI3)",b"set(DRI3SRC dri3.c)",b"if(TVNC_USETLS STREQUAL",b"if(TVNC_NVCONTROL)"),
        "unix/Xvnc/programs/Xserver/glx/CMakeLists.txt": (b"glxdriswrast.c",b"target_link_libraries(glx-server OpenGL::GL)"),
    }
    review_seen=set()
    with tarfile.open(fileobj=io.BytesIO(data),mode="r:*") as tar:
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in m.name.split("/"):
                raise ValueError("unsafe archive member")
            if not m.isfile() or m.size>1024*1024:
                continue
            rel=m.name.partition("/")[2]
            if rel in ("COPYING","COPYING.md","LICENSE","LICENSE.md","LICENSE.ijg","LICENSE.txt",
                        "unix/Xvnc/programs/Xserver/COPYING","unix/Xvnc/lib/libsha1/COPYING",
                        "unix/Xvnc/lib/zlib-ng/LICENSE.md"):
                notice=hashlib.sha256(tar.extractfile(m).read()).hexdigest()
                if name=="turbovnc" and rel in expected_notices and expected_notices[rel]!=notice:
                    raise ValueError("changed exact original bundled notice: "+rel)
                notices[m.name]=notice
            if rel in ("meson.build","meson_options.txt","CMakeLists.txt",
                        "unix/CMakeLists.txt","unix/Xvnc/CMakeLists.txt","unix/Xvnc/programs/Xserver/CMakeLists.txt","BUILDING.md",
                        "unix/Xvnc/lib/CMakeLists.txt","unix/Xvnc/programs/Xserver/hw/vnc/CMakeLists.txt",
                        "unix/Xvnc/programs/Xserver/glx/CMakeLists.txt"):
                cmake_source=tar.extractfile(m).read()
                actual=hashlib.sha256(cmake_source).hexdigest()
                if name=="turbovnc" and rel in expected_original_cmake and actual!=expected_original_cmake[rel]:
                    raise ValueError("changed original Xvnc CMake graph: "+rel)
                build[m.name]=actual
                if name=="turbovnc" and rel in review_paths:
                    if any(marker not in cmake_source for marker in review_paths[rel]):
                        raise ValueError("missing upstream feature guard: "+rel)
                    review_seen.add(rel)
                if name=="turbovnc" and rel=="unix/Xvnc/CMakeLists.txt":
                    if b"option(TVNC_DRI3" not in cmake_source:
                        raise ValueError("DRI3 optional feature lost from original TurboVNC source")
                    source_feature_checks["TVNC_DRI3_option_original"]=True
                if name=="turbovnc" and rel=="unix/Xvnc/programs/Xserver/CMakeLists.txt":
                    for marker in (b"if(TVNC_DRI3)",b"add_subdirectory(dri3)",b"glx-server",b"install(TARGETS Xvnc"):
                        if marker not in cmake_source:raise ValueError("original Xvnc CMake graph changed")
                    source_feature_checks["DRI3_requires_explicit_disable"]=True
    if name=="turbovnc" and (set(review_paths)!=review_seen
                           or any(not any(key.endswith("/"+rel) for key in notices)
                                  for rel in expected_notices)
                           or any(not any(key.endswith("/"+rel) for key in build)
                                  for rel in expected_original_cmake)):
        raise ValueError("original selected/bundled source map incomplete")
    if name=="turbovnc" and set(source_feature_checks)!={"TVNC_DRI3_option_original","DRI3_requires_explicit_disable"}:
        raise ValueError("missing selected Xvnc original CMake evidence")
    if not notices or not build:
        raise ValueError("original upstream notice/build metadata not found")
    return {"name":name,"version":spec["version"],"url":spec["url"],
            "archive_sha256":sha,"notices":notices,"build_metadata":build,
            "selected_source_feature_checks":source_feature_checks,
            "state":"upstream-source-observed-not-native-or-redistribution-approved"}
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--package",choices=sorted(SOURCES),required=True)
    name=p.parse_args().package;spec=SOURCES[name]
    with urlopen(Request(spec["url"],headers={"User-Agent":"Zog-original-source/1"}),timeout=60) as response:
        b=response.read(64*1024*1024+1)
    if len(b)>64*1024*1024:raise ValueError("archive exceeds inspection bound")
    print(json.dumps(inspect(name,b),sort_keys=True))

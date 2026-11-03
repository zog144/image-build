#!/usr/bin/env python3
"""Read-only original-source reconnaissance, not an admission or grant.

Keep transport, expected SHA and observed bytes distinct. An unverified
candidate MUST NOT be admitted to the catalogue or executable recipes.
"""
import hashlib
import io
import json
import tarfile
from urllib.request import Request, urlopen

SOURCES = {
 "libev": {"version":"4.33","url":"https://mirrors.omnios.org/libev/libev-4.33.tar.gz",
           "expected_sha256":"507eb7b8d1015fbec5b935f34ebed15bf346bed04a11ab82b8eee848c4205aea"},
 "yajl": {"version":"2.1.0","url":"https://github.com/lloyd/yajl/archive/refs/tags/2.1.0.tar.gz",
           "expected_sha256":None},
 "startup-notification":{"version":"0.12","url":"https://www.freedesktop.org/software/startup-notification/releases/startup-notification-0.12.tar.gz",
           "expected_sha256":None},
 "libxkbcommon":{"version":"1.13.2","url":"https://github.com/lfs-book/libxkbcommon/archive/refs/tags/v1.13.2.tar.gz",
           "expected_sha256":None},
 "xkeyboard-config":{"version":"2.48","url":"https://xorg.freedesktop.org/archive/individual/data/xkeyboard-config/xkeyboard-config-2.48.tar.xz",
           "expected_sha256":"b77041324f0109f77161ee43743fe04baa485866af8460d31e476ad3f7648fd5"}
}
MAX_ARCHIVE = 8*1024*1024
MAX_MEMBER = 1024*1024

def capture(name, payload):
    spec = SOURCES[name]
    actual = hashlib.sha256(payload).hexdigest()
    if spec["expected_sha256"] and actual != spec["expected_sha256"]:
        raise ValueError(name+": archive identity differs from independently published SHA-256")
    notices = {}
    interesting = []
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as tf:
        for entry in tf.getmembers():
            if entry.name.startswith("/") or ".." in entry.name.split("/"):
                raise ValueError("unsafe archive pathname")
            if not entry.isfile():
                continue
            if entry.size > MAX_MEMBER:
                continue
            relative = entry.name.partition("/")[2]
            if relative in ("COPYING","COPYING.md","LICENSE","LICENSE.txt","LICENSE.md",
                            "meson.build","CMakeLists.txt","configure.ac","Makefile.am",
                            "configure","NEWS","README","README.md"):
                if relative.startswith(("COPYING", "LICENSE")):
                    notices[entry.name] = hashlib.sha256(tf.extractfile(entry).read()).hexdigest()
                if len(interesting)<20:interesting.append(relative)
    if not notices:
        raise ValueError(name+": no recognized exact original rights member")
    return {"package":name,"version":spec["version"],"url":spec["url"],
            "sha256":actual,"upstream_digest_independently_expected":bool(spec["expected_sha256"]),
            "notice_members":notices,"build_metadata_seen":interesting,
            "status":"observed-original-archive-not-native-or-rights-approved"}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--single",choices=sorted(SOURCES),required=True)
    name=p.parse_args().single
    request=Request(SOURCES[name]["url"],headers={"User-Agent":"Zog-image-build-exact-source/1"})
    with urlopen(request,timeout=60) as response:
        blob=response.read(MAX_ARCHIVE+1)
    if len(blob)>MAX_ARCHIVE:raise ValueError("archive exceeds bound")
    print(json.dumps(capture(name,blob),sort_keys=True),flush=True)

if __name__=="__main__":main()

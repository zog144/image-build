#!/usr/bin/env python3
"""Read-only selected Cairo/Pango/GLib archive, upstream hash and rights survey."""
import hashlib,io,json,re,tarfile
from urllib.request import Request,urlopen

SOURCES={
 "glib":{"version":"2.86.5",
         "url":"https://download.gnome.org/sources/glib/2.86/glib-2.86.5.tar.xz",
         "digest_url":"https://download.gnome.org/sources/glib/2.86/glib-2.86.5.sha256sum"},
 "pango":{"version":"1.56.4",
          "url":"https://download.gnome.org/sources/pango/1.56/pango-1.56.4.tar.xz",
          "digest_url":"https://download.gnome.org/sources/pango/1.56/pango-1.56.4.sha256sum"},
 "cairo":{"version":"1.18.4",
          "url":"https://cairographics.org/releases/cairo-1.18.4.tar.xz",
          "digest_url":"https://cairographics.org/releases/cairo-1.18.4.tar.xz.sha256sum"}
}
def fetch(url,max_bytes):
    with urlopen(Request(url,headers={"User-Agent":"Zog-source-archive-verification/1"}),timeout=90) as r:
        payload=r.read(max_bytes+1)
    if len(payload)>max_bytes:raise ValueError("upstream response exceeds bound")
    return payload

def inspect(name,blob,published):
    spec=SOURCES[name]
    digest=hashlib.sha256(blob).hexdigest()
    published_text=published.decode("utf-8",errors="strict")
    target=name+"-"+spec["version"]+".tar.xz"
    entries=[line.split() for line in published_text.splitlines()
             if line.split() and len(line.split())==2 and
             line.split()[1].lstrip("*")==target]
    if len(entries)!=1 or not re.fullmatch(r"[a-fA-F0-9]{64}",entries[0][0]) or entries[0][0].lower()!=digest:
        raise ValueError("published original-source hash doesn't bind selected archive")
    rights={}
    meta={}
    options={}
    with tarfile.open(fileobj=io.BytesIO(blob),mode="r:xz") as tf:
        for item in tf.getmembers():
            if item.name.startswith("/") or ".." in item.name.split("/"):
                raise ValueError("unsafe archive entry")
            if not item.isfile() or item.size>2*1024*1024:continue
            rel=item.name.partition("/")[2]
            if rel in ("COPYING","COPYING.LIB","COPYING.LGPL","COPYING.LGPL-2.1",
                       "LICENSE","LICENSE.md","LICENSE.txt") or (rel.startswith("LICENSES/") and rel.endswith(".txt")):
                rights[item.name]=hashlib.sha256(tf.extractfile(item).read()).hexdigest()
            if rel in ("meson.build","meson_options.txt","meson.options"):
                contents=tf.extractfile(item).read()
                meta[item.name]=hashlib.sha256(contents).hexdigest()
                if rel in ("meson_options.txt","meson.options"):
                    options[rel]=sorted(set(re.findall(
                        r"option\\s*\\(\\s*['\\\"]([^'\\\"]+)['\\\"]",
                        contents.decode("utf-8",errors="replace"))))

    if not rights or not meta:raise ValueError("original license or build source absent")
    return {"package":name,"version":spec["version"],"source_url":spec["url"],
            "sha256":digest,"original_notice_members":rights,
            "original_build_metadata":meta,"meson_option_names":options,"published_digest_url":spec["digest_url"],
            "status":"source-identity-observed-text-closure-not-admitted"}

if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser();a.add_argument("--package",choices=sorted(SOURCES),required=True)
    name=a.parse_args().package;spec=SOURCES[name]
    print(json.dumps(inspect(name,fetch(spec["url"],45*1024*1024),
                             fetch(spec["digest_url"],64*1024)),sort_keys=True))

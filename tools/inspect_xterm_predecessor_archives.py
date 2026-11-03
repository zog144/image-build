#!/usr/bin/env python3
"""Read-only xterm Xorg libraries, locale helper and original bitmap font source."""
import argparse,hashlib,io,json,tarfile
from urllib.request import Request,urlopen
SOURCES={
"libXaw":("1.0.16","https://www.x.org/releases/individual/lib/libXaw-1.0.16.tar.xz"),
"libXmu":("1.2.1","https://www.x.org/releases/individual/lib/libXmu-1.2.1.tar.xz"),
"libXpm":("3.5.17","https://www.x.org/releases/individual/lib/libXpm-3.5.17.tar.xz"),
"libXft":("2.3.9","https://www.x.org/releases/individual/lib/libXft-2.3.9.tar.xz"),
"luit":("1.1.1","https://www.x.org/releases/individual/app/luit-1.1.1.tar.bz2"),
"font-misc-misc":("1.1.3","https://www.x.org/releases/individual/font/font-misc-misc-1.1.3.tar.xz"),
"bdftopcf":("1.1.2","https://www.x.org/releases/individual/util/bdftopcf-1.1.2.tar.xz"),
"mkfontscale":("1.2.3","https://www.x.org/releases/individual/app/mkfontscale-1.2.3.tar.xz"),
"xkbcomp":("1.5.0","https://www.x.org/releases/individual/app/xkbcomp-1.5.0.tar.xz"),
}
def inspect(name,content):
    ver,url=SOURCES[name];rights={};build={};selected_font={}
    with tarfile.open(fileobj=io.BytesIO(content),mode="r:*") as tf:
        for member in tf.getmembers():
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise ValueError("unsafe member path")
            if not member.isfile() or member.size>1024*1024:continue
            relative=member.name.partition("/")[2]
            if name=="font-misc-misc" and relative=="6x13.bdf":
                selected_font[member.name]=hashlib.sha256(tf.extractfile(member).read()).hexdigest()
            if relative in ("COPYING","COPYING.LIB","LICENSE","LICENSE.txt"):
                rights[member.name]=hashlib.sha256(tf.extractfile(member).read()).hexdigest()
            if relative in ("configure.ac","Makefile.am","meson.build","meson_options.txt"):
                build[member.name]=hashlib.sha256(tf.extractfile(member).read()).hexdigest()
    if not rights or not build:raise ValueError("original rights/build metadata unavailable")
    if name=="font-misc-misc" and len(selected_font)!=1:
        raise ValueError("selected 6x13.bdf original font missing")
    return {"package":name,"version":ver,"url":url,"sha256":hashlib.sha256(content).hexdigest(),
            "original_license_hashes":rights,"build_members":build,"selected_font_sources":selected_font,"status":"original-source-only-native-HOLD"}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--package",choices=sorted(SOURCES),required=True)
    n=p.parse_args().package
    with urlopen(Request(SOURCES[n][1],headers={"User-Agent":"Zog-source-review/1"}),timeout=75) as r:
        b=r.read(20*1024*1024+1)
    if len(b)>20*1024*1024:raise ValueError("archive exceeds inspection bounds")
    print(json.dumps(inspect(n,b),sort_keys=True))

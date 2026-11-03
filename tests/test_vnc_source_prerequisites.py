"""Source-only Pixman/TurboJPEG first-Workspace predecessor assertions."""
import ast
from pathlib import Path

from zog.image_build.metadata import load_package
from zog.image_build.licensing import load

ROOT=Path(__file__).resolve().parents[1]/"project/package"
PIN={
 "pixman":("0.46.4","a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239",
          "fac9270f0987b96ff4533fca3548c633e02083cbba4a0172a3b149b2e4019793"),
 "libjpeg-turbo":("3.2.0","6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e",
                  "ba6bceebcba0fdd35488477c2cca8c4632ce82c74dbfbc87d886ce6fc4433579"),
}
def lit(path):return ast.literal_eval(path.read_text())

def test_original_source_rights_and_outputs_stay_unadmitted():
    for name,(version,source_sha,notice_sha) in PIN.items():
        directory=ROOT/name
        upstream=lit(directory/"upstream.py")
        source=lit(directory/"stages/final/sources.py")[0]
        license_record=load(directory/"license.py",[source])
        package=load_package(directory/"stages/final")
        assert upstream["version"]==version
        assert upstream["sha256"]==source_sha==source["sha256"]
        assert source["archive"] is True
        assert license_record["evidence"][0]["sha256"]==notice_sha
        assert license_record["components"][0]["status"]=="unresolved"
        assert lit(directory/"package.py")["status"]=="catalogue-only"
        assert package.output_trees==("usr",)
        assert package.outputs

def test_minimal_libjpeg_profile_avoids_unreviewed_assembler_and_java():
    build=lit(ROOT/"libjpeg-turbo/stages/final/build.py")
    text=build["configure"][0][-1]
    for flag in ("-DWITH_SIMD=OFF","-DWITH_JNA=OFF","-DWITH_TOOLS=OFF",
                 "-DWITH_TURBOJPEG=ON","-DENABLE_SHARED=ON","-DENABLE_STATIC=OFF"):
        assert flag in text
    assert "-DWITH_JAVA" not in text
    out=set(lit(ROOT/"libjpeg-turbo/stages/final/produce-manifest.py")["required"])
    assert {"usr/include/turbojpeg.h","usr/lib/libturbojpeg.so"}<=out

def test_pixman_runtime_stays_source_only():
    build=lit(ROOT/"pixman/stages/final/build.py")
    assert "--wrap-mode=nodownload" in build["configure"][0][-1]
    assert "-Ddefault_library=shared" in build["configure"][0][-1]
    assert "share/licenses/pixman/COPYING" in build["install"][0][-1]

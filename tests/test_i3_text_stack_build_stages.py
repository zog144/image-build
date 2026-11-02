"""Source-only GLib/Cairo/Pango library stage and license-origin validation."""
import ast
from pathlib import Path
from zog.image_build.metadata import load_package
from zog.image_build.licensing import load as load_license

ROOT=Path(__file__).resolve().parents[1]/"project/package"
PIN={
"glib":"ce85a947bb8b3c0204dbeff79aec39bcb46371c6fafb64ba5b8726c71e038d5f",
"cairo":"445ed8208a6e4823de1226a74ca319d3600e83f6369f99b14265006599c32ccb",
"pango":"17065e2fcc5f5a5bdbffc884c956bfc7c451a96e8c4fb2f8ad837c6413cb5a01"}
def literal(x):return ast.literal_eval(x.read_text())

def test_text_stages_are_true_source_pins_and_unadmitted():
    for name,sha in PIN.items():
        root=ROOT/name
        source=literal(root/"stages/final/sources.py")[0]
        license_record=load_license(root/"license.py",[source])
        package=load_package(root/"stages/final")
        assert sha==source["sha256"]==literal(root/"upstream.py")["sha256"]
        assert package.sources==(source,)
        assert literal(root/"package.py")["status"]=="catalogue-only"
        assert license_record["components"][0]["status"]=="unresolved"
        assert all(x["source_sha256"]==sha for x in license_record["evidence"])
        required=set(literal(root/"stages/final/produce-manifest.py")["required"])
        script=literal(root/"stages/final/build.py")["install"][0][-1]
        assert all("usr/share/licenses/"+name+"/" in x or x.startswith("usr/lib/") or x.startswith("usr/bin/") for x in required)
        for evidence in license_record["evidence"]:
            assert evidence["path"].split("/",1)[1] in script
        command=literal(root/"stages/final/build.py")["configure"][0][-1]
        assert "--wrap-mode=nodownload" in command
        assert "-Dauto_features=disabled" in command
        assert "PKG_CONFIG_LIBDIR" in command and "ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION" in command
        assert literal(root/"stages/final/integration.py")["native_admission"].startswith("HOLD")
def test_feature_scopes_deny_unreviewed_interpreter_and_optional_modules():
    glib=literal(ROOT/"glib/stages/final/build.py")["configure"][0][-1]
    pango=literal(ROOT/"pango/stages/final/build.py")["configure"][0][-1]
    assert "-Dintrospection=disabled" in glib and "-Dlibmount=disabled" in glib
    assert "-Ddocumentation=false" in glib and "-Dnls=disabled" in glib
    assert "-Dlibthai=disabled" in pango and "-Dxft=disabled" in pango
    assert "-Dintrospection=disabled" in pango and "-Dbuild-testsuite=false" in pango
    assert "harfbuzz-final" in literal(ROOT/"pango/stages/final/dependencies.py")["build"]
    assert "libXrender-final" in literal(ROOT/"cairo/stages/final/dependencies.py")["build"]

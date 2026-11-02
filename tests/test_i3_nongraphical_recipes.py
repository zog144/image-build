"""Five source-only i3 event/configuration/session/keyboard recipes.

Run real metadata and rights validators; no missing monthly pin is fabricated.
"""
import ast
from pathlib import Path
import shutil

from zog.image_build.licensing import load
from zog.image_build.metadata import load_packages, order

BASE = Path(__file__).resolve().parents[1] / "project"
NAMES = ("libev", "yajl", "startup-notification", "xkeyboard-config", "libxkbcommon")
PINS = {
    "libev": ("4.33", "507eb7b8d1015fbec5b935f34ebed15bf346bed04a11ab82b8eee848c4205aea",
              "c4dd1a5bc38b041a320b93c5d6c08f5c41a63f2ce718ee16cfcb757fad448199"),
    "yajl": ("2.1.0", "3fb73364a5a30efe615046d07e6db9d09fd2b41c763c5f7d3bfb121cd5c5ac5a",
             "054bf2c11686c5442850b1da58ad592e3d1d2a236a362e67279b957f8e662f5a"),
    "startup-notification": ("0.12", "3c391f7e930c583095045cd2d10eb73a64f085c7fde9d260f2652c7cb3cfbe4a",
                             "29935974beae046f50da806b5f4e54532401dd7bcfbc696a0b645f4cbcce9dbb"),
    "xkeyboard-config": ("2.48", "b77041324f0109f77161ee43743fe04baa485866af8460d31e476ad3f7648fd5",
                         "fc03f6535d16b3fe9beece45b84214a37e6ca4b6550c03cadaed7e1b951fb294"),
    "libxkbcommon": ("1.13.2", "e5d5eff0ea09d82c44a96aec75c719b6969fdc602da82e6b1c9aa74cac5fd488",
                      "967e97b28658f0037bbe164a237bdfb0c3ec790e67f6c29372ea5b09306f61f3"),
}


def literal(path):
    return ast.literal_eval(path.read_text())


def test_exact_archive_and_original_notice_records_are_source_bound():
    for name in NAMES:
        version, source_sha, notice_sha = PINS[name]
        root = BASE / "package" / name
        upstream = literal(root / "upstream.py")
        sources = literal(root / "stages/final/sources.py")
        license_record = load(root / "license.py", sources)
        assert upstream["version"] == version
        assert upstream["sha256"] == source_sha
        assert sources[0]["sha256"] == source_sha
        assert sources[0]["archive"] is True
        assert license_record["source"]["sha256"] == source_sha
        assert license_record["evidence"][0]["sha256"] == notice_sha
        assert license_record["evidence"][0]["source_sha256"] == source_sha
        assert license_record["components"][0]["status"] == "unresolved"
        assert literal(root / "package.py")["status"] == "catalogue-only"


def test_full_nongraphical_dependency_order_with_actual_loader(tmp_path):
    plan = literal(BASE / "bootstrap/graphics-i3-nongraphical.py")
    staged = tmp_path / "staged"
    staged.mkdir()
    for row in plan["stages"]:
        dest = staged / row["id"]
        dest.mkdir()
        for filename in ("sources.py", "dependencies.py", "build.py", "produce-manifest.py"):
            shutil.copyfile(BASE / "package" / row["recipe"] / filename, dest / filename)
    packages = load_packages(staged)
    names = order(packages, plan["targets"])
    assert names.index("xcb-util-final") < names.index("startup-notification-final")
    assert names.index("xkeyboard-config-final") < names.index("libxkbcommon-final")
    assert packages["libxkbcommon-final"].build_dependencies == ("xkeyboard-config-final",)
    assert packages["startup-notification-final"].build_dependencies == ("xcb-util-final",)
    assert all(name + "-final" in names for name in NAMES)


def test_build_steps_and_install_boundaries_keep_noncanonical_status():
    for name in NAMES:
        root = BASE / "package" / name
        build = literal(root / "stages/final/build.py")
        manifest = literal(root / "stages/final/produce-manifest.py")
        integration = literal(root / "stages/final/integration.py")
        assert manifest["trees"] == ["usr"] and manifest["required"]
        assert "test -n \"$DESTDIR\"" in build["install"][0][-1]
        assert "share/licenses/" + name in build["install"][0][-1]
        assert "Host fallback forbidden" in integration["base_contract"]
        assert integration["patches_complete"] is True
    xkb = literal(BASE / "package/libxkbcommon/stages/final/build.py")["configure"][0][-1]
    assert "-Denable-wayland=false" in xkb and "-Denable-x11=true" in xkb
    assert "-Denable-tools=false" in xkb and "-Denable-docs=false" in xkb
    assert "-Dxkb-config-root=/usr/share/X11/xkb" in xkb
    yajl = literal(BASE / "package/yajl/stages/final/build.py")["install"][0][-1]
    assert 'DESTDIR="$DESTDIR" cmake --install' in yajl

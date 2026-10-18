import ast
from pathlib import Path

import pytest

from zog.image_build.errors import ImageBuildError
from zog.image_build.metadata import load_package


ROOT = Path(__file__).parents[1] / "project/package"

EXPECTED = {
    "greetd": (
        "0.10.3",
        "https://deb.debian.org/debian/pool/main/g/greetd/greetd_0.10.3.orig.tar.gz",
        "ee5cb70e0add4ca9c9fe57e47581ab0002d44c07743fb5492469f3b570db640b",
        "source-pinned-application-plan",
    ),
    "agreety": (
        "0.10.3",
        "https://deb.debian.org/debian/pool/main/g/greetd/greetd_0.10.3.orig.tar.gz",
        "ee5cb70e0add4ca9c9fe57e47581ab0002d44c07743fb5492469f3b570db640b",
        "source-pinned-application-plan",
    ),
    "xorg-server": (
        "21.1.25",
        "https://www.x.org/pub/individual/xserver/xorg-server-21.1.25.tar.xz",
        "6ad4e3c7b59a309b32c92e5c15ce1267110f9e13f1ac78da62361a628da1a0eb",
        "source-pinned-application-plan",
    ),
    "i3": (
        "4.25.1",
        "https://i3wm.org/downloads/i3-4.25.1.tar.xz",
        "4a742bbe81b9e5ee6057f42a8e3c691d88894e93f1a5d81fe239128512ac05c0",
        "source-pinned-application-plan",
    ),
    "firefox-esr": (
        "153.5.0esr",
        "https://archive.mozilla.org/pub/firefox/releases/153.5.0esr/source/firefox-153.5.0esr.source.tar.xz",
        "28714a7d4f9b38c7aafbe38022de7775a3d9cb3c1ebf19a567c26eb761e3410b",
        "source-pinned-application-plan",
    ),
    "turbovnc": (
        "3.3.1",
        "https://github.com/TurboVNC/turbovnc/releases/download/3.3.1/turbovnc-3.3.1.tar.gz",
        "9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da",
        "source-pinned-follow-on-plan",
    ),
    "virtualgl": (
        "3.1.5",
        "https://github.com/VirtualGL/virtualgl/releases/download/3.1.5/VirtualGL-3.1.5.tar.gz",
        "8a3249c4fa8eea928362ca97b8fe16e5b356e3a18cd16d87e3efa72a870750b6",
        "source-pinned-follow-on-plan",
    ),
}


def literal(path):
    return ast.literal_eval(path.read_text())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_graphical_application_catalogue_source_pin_is_exact_and_non_buildable(name):
    version, url, sha256, recipe_status = EXPECTED[name]
    directory = ROOT / name
    catalogue = literal(directory / "package.py")
    sources = literal(directory / "sources.py")

    assert catalogue["schema"] == 1
    assert catalogue["name"] == name
    assert catalogue["status"] == "catalogue-only"
    assert catalogue["recipe_status"] == recipe_status
    assert catalogue["artifact_contract"] == "applications-v1"
    assert catalogue["source_version"] == version
    assert "license_scope" in catalogue
    assert len(sources) == 1
    assert sources[0] == {
        "url": url,
        "sha256": sha256,
        "destination": sources[0]["destination"],
        "archive": True,
    }
    assert sources[0]["destination"]
    assert len(sha256) == 64
    int(sha256, 16)

    with pytest.raises(ImageBuildError, match="catalogue-only"):
        load_package(directory)


def test_greetd_privileged_execution_remains_explicitly_unapproved():
    catalogue = literal(ROOT / "greetd/package.py")
    assert catalogue["activation"] == "privileged-role-not-approved"


def test_greetd_and_agreety_share_source_but_are_distinct_application_plans():
    greetd = literal(ROOT / "greetd/sources.py")
    agreety = literal(ROOT / "agreety/sources.py")
    assert greetd == agreety
    assert literal(ROOT / "greetd/package.py")["name"] == "greetd"
    assert literal(ROOT / "agreety/package.py")["name"] == "agreety"

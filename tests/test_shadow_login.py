import hashlib
from pathlib import Path

from zog.image_build.metadata import load_packages
from zog.image_build.sources import stage
from zog.image_build.stages import stage_recipes


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
SHADOW_SHA = "b89f432b75ae55a2d852b446d0365484795fdf533ab97d550e325fa15594a224"
TOP_MAKEFILE_AM_SHA = "d2005f993f3c7c91e8af820b2cbd802611e8a279a568b6f0318a306a81b7ceda"
SRC_MAKEFILE_AM_SHA = "cd2ad305ef5ad03331620b77c247da1387ed378721e77bc83a0e1baf1166cfcf"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_exact_shadow_source_login_target_and_library_prerequisite(tmp_path):
    recipes = tmp_path / "recipes"
    stage_recipes(
        PROJECT / "bootstrap/boot-a-targeted.py",
        PROJECT / "package",
        recipes,
    )
    package = load_packages(recipes)["shadow-login"]
    assert package.sources[0]["sha256"] == SHADOW_SHA

    source = tmp_path / "source"
    cache = tmp_path / "cache"
    records = stage(package, source, cache)
    assert records[0]["transport"] == "upstream"
    assert _sha256(cache / SHADOW_SHA) == SHADOW_SHA

    upstream = source / "upstream/shadow-4.20.2"
    top_am = upstream / "Makefile.am"
    src_am = upstream / "src/Makefile.am"
    lib_am = upstream / "lib/Makefile.am"
    assert _sha256(top_am) == TOP_MAKEFILE_AM_SHA
    assert _sha256(src_am) == SRC_MAKEFILE_AM_SHA

    top_text = top_am.read_text()
    src_text = src_am.read_text()
    lib_text = lib_am.read_text()

    # Bind the correction to the exact upstream recursive order and targets.
    assert "SUBDIRS = lib" in top_text
    assert "SUBDIRS += src po doc etc tests/unit" in top_text
    assert "noinst_LTLIBRARIES = libshadow.la" in lib_text
    assert "bin_PROGRAMS   = login" in src_text
    assert "login_SOURCES  = \\\n\tlogin.c \\\n\tlogin_nopam.c" in src_text
    assert "$(top_builddir)/lib/libshadow.la" in src_text
    assert "login_LDADD" in src_text

    # Both login translation units require configure's generated config.h.
    assert "AC_CONFIG_HEADERS([config.h])" in (upstream / "configure.ac").read_text()
    assert '#include "config.h"' in (upstream / "src/login.c").read_text()
    assert '#include "config.h"' in (upstream / "src/login_nopam.c").read_text()

    configure = package.steps["configure"][0][-1]
    build = package.steps["build"][0][-1]
    test = package.steps["test"][0][-1]
    install = package.steps["install"][0][-1]

    assert "--without-libpam" in configure
    assert "test -f config.h" in build
    assert "test -f lib/Makefile" in build
    assert "test -f src/Makefile" in build
    assert "make -C lib -j8 libshadow.la" in build
    assert "test -f lib/libshadow.la" in build
    assert "make -C src -j8 login" in build
    assert "make -j8 src/login" not in build

    assert "test -f config.h" in test
    assert "test -f lib/libshadow.la" in test
    assert "test -x src/login" in test
    assert "! readelf -d src/login | grep -q 'libpam'" in test
    assert "readelf -d src/login | grep -q 'libcrypt'" in test
    assert 'install -Dm755 src/login "$DESTDIR/usr/bin/login"' in install

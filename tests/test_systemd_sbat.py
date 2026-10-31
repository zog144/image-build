import hashlib
import shlex
from pathlib import Path

from zog.image_build.metadata import load_packages
from zog.image_build.sources import stage
from zog.image_build.stages import stage_recipes


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
SYSTEMD_SHA = "ed1059ff964f5df35b6056434cc17cc83f86dc913f10489948a0b19b6081c5ec"
BOOT_MESON_SHA = "f0b460eede1245d125ab3f4b63ccf28c8c0f4a4cfed303260ea7c34eef8221a5"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_exact_systemd_source_uses_explicit_zog_sbat_without_os_release_autodetection(tmp_path):
    recipes = tmp_path / "recipes"
    stage_recipes(
        PROJECT / "bootstrap/systemd-core.py",
        PROJECT / "package",
        recipes,
    )
    package = load_packages(recipes)["systemd-final"]
    assert package.sources[0]["sha256"] == SYSTEMD_SHA

    source = tmp_path / "source"
    cache = tmp_path / "cache"
    records = stage(package, source, cache)
    assert records[0]["transport"] == "upstream"
    assert _sha256(cache / SYSTEMD_SHA) == SYSTEMD_SHA

    upstream = source / "upstream/systemd-261.2"
    boot_meson = upstream / "src/boot/meson.build"
    assert _sha256(boot_meson) == BOOT_MESON_SHA
    text = boot_meson.read_text()

    # Bind this regression to the exact upstream branch that failed natively.
    assert "foreach sbatvar : [['sbat-distro', 'ID']," in text
    assert "['sbat-distro-summary', 'NAME']," in text
    assert "['sbat-distro-url', 'BUG_REPORT_URL']]" in text
    assert "if (value == '' or value == 'auto') and not meson.is_cross_build()" in text
    assert "/etc/os-release" in text and "/usr/lib/os-release" in text

    sbat = package.integration["sbat"]
    values = {
        "sbat-distro": sbat["distro"],
        "sbat-distro-summary": sbat["summary"],
        "sbat-distro-url": sbat["url"],
        "sbat-distro-generation": str(sbat["generation"]),
        "sbat-distro-pkgname": sbat["pkgname"],
        "sbat-distro-version": sbat["version"],
    }
    assert all(value not in {"", "auto"} for value in values.values())

    # SBAT remains explicit and independent of host/build os-release data.
    # The resident install now also emits immutable Zog OS-tree metadata because
    # systemd's initrd SwitchRoot safety check requires an os-release marker.
    for option in ("sbat-distro", "sbat-distro-summary", "sbat-distro-url"):
        assert values[option] not in {"", "auto"}
    install = package.steps["install"][0][-1]
    assert 'usr/lib/os-release' in package.outputs
    assert 'etc/os-release' in package.outputs
    assert 'NAME="Zog"' in install
    assert 'ID=zog' in install
    assert 'PRETTY_NAME="Zog"' in install
    assert 'ln -s ../usr/lib/os-release "$DESTDIR/etc/os-release"' in install

    configure = package.steps["configure"][0][-1]
    meson_line = next(line for line in configure.splitlines() if line.startswith("meson setup "))
    argv = shlex.split(meson_line)
    for option, value in values.items():
        assert f"-D{option}={value}" in argv

    sbat_h = (upstream / "src/fundamental/sbat.h").read_text()
    assert (
        'SBAT_PROJECT "-boot" "." SBAT_DISTRO "," STRINGIFY(SBAT_DISTRO_GENERATION) '
        '"," SBAT_DISTRO_SUMMARY "," SBAT_DISTRO_PKGNAME "," SBAT_DISTRO_VERSION '
        '"," SBAT_DISTRO_URL "\\n"'
    ) in sbat_h

    expected_row = (
        "systemd-boot.zog,1,Zog Project,systemd,261.2,"
        "https://github.com/zog144/image-build"
    )
    native_test = package.steps["test"][0][-1]
    assert expected_row in native_test
    assert "objcopy --dump-section .sbat=" in native_test
    assert "build/src/boot/systemd-bootx64.efi" in native_test
    assert "build/src/boot/efi/systemd-bootx64.efi" not in native_test

    # Bind the tested path to the exact upstream Meson custom-target location:
    # src/boot/meson.build emits the target in its own build subdirectory.
    assert "output : name" in text
    assert "name += name.startswith('systemd-boot') ? '.efi' : '.efi.stub'" in text

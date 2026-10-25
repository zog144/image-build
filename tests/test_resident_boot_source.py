from pathlib import Path
import hashlib

from zog.image_build.host_inventory import inspect
from zog.image_build.metadata import literal, load_package


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "project/package"
PROFILE = ROOT / "project/host/bootstrap-profile.py"


def test_boot_a_profile_is_source_candidate_with_resident_b_deferred():
    profile = literal(PROFILE)
    assert profile["status"] == "boot-a-source-candidate"
    assert profile["dependency_closure"] == "boot-a-reviewed-resident-b-incomplete"
    assert profile["boot_a"]["projects"] == [
        "bash",
        "util-linux",
        "systemd",
        "e2fsprogs",
        "kmod",
    ]
    assert profile["boot_a"]["providers"]["/usr/bin/login"] == (
        "util-linux host-additions stage"
    )
    assert profile["resident_b"]["deferred_projects"] == [
        "shadow",
        "box-control",
        "root-control",
    ]
    items = {item["project"]: item for item in profile["items"]}
    assert items["shadow"]["group"] == "resident-b-deferred"
    assert items["box-control"]["group"] == "resident-b-deferred"
    assert items["root-control"]["group"] == "resident-b-deferred"

    report = inspect(PROFILE, CATALOGUE)
    assert report["status"] == "boot-a-source-candidate"
    assert report["installable"] is False
    assert report["source_candidate"] is True
    assert report["boot_a"]["source_recipe_complete"] is True
    assert report["boot_a"]["recipe_gaps"] == []
    assert report["resident_b"]["status"] == "deferred-after-boot-a"


def test_systemd_source_requires_efi_loader_and_getty_units():
    build = literal(
        CATALOGUE / "systemd/stages/final/build.py"
    )
    command = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in build.get(phase, [])
    )
    assert "-Defi=true" in command
    assert "-Dbootloader=enabled" in command
    assert "-Dbootloader=disabled" not in command

    outputs = literal(
        CATALOGUE / "systemd/stages/final/produce-manifest.py"
    )["required"]
    assert "usr/lib/systemd/boot/efi/systemd-bootx64.efi" in outputs
    assert "usr/lib/systemd/system/getty@.service" in outputs
    assert "usr/lib/systemd/system/serial-getty@.service" in outputs


def test_boot_a_login_is_additive_util_linux_stage_not_shadow():
    package = load_package(CATALOGUE / "util-linux/stages/nologin")
    assert package.outputs == ("usr/bin/login", "usr/sbin/nologin")
    assert package.sources[0]["sha256"] == (
        "03a05d3adf9602ef128f2da05b84b3205ce60c351e5737c0370f74000679ce8a"
    )
    commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in package.steps[phase]
    )
    assert "--disable-all-programs --enable-login --enable-nologin" in commands
    assert "--disable-login" not in commands
    assert "./login --version" in commands
    assert 'install -Dm755 login "$DESTDIR/usr/bin/login"' in commands

    shadow = literal(CATALOGUE / "shadow/recipe-plan.py")
    assert shadow["status"] == "resident-b-deferred"
    assert "Not a Boot A login provider" in shadow["notes"]


def test_resident_root_layout_is_bound_to_required_systemd_rebuild():
    package = load_package(CATALOGUE / "systemd/stages/final")
    commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in package.steps[phase]
    )
    assert 'install -d -m 0000 "$DESTDIR/state" "$DESTDIR/applications"' in commands
    assert {"state", "applications"} <= set(package.output_trees)
    assert {"state", "applications"} <= set(package.outputs)


def test_host_boot_plan_selects_only_targeted_boot_a_additions():
    plan = literal(ROOT / "project/bootstrap/host-boot-packages.py")
    stages = {item["id"]: item for item in plan["stages"]}
    assert stages["util-linux-nologin"] == {
        "id": "util-linux-nologin",
        "project": "util-linux",
        "stage": "nologin",
        "recipe": "util-linux/stages/nologin",
    }
    assert "util-linux-nologin" in plan["targets"]

    check = (ROOT / "project/bootstrap/host-boot-packages-check.sh").read_text()
    assert "/usr/bin/login --version" in check
    assert "/usr/sbin/agetty --version" in check
    assert "stat -c '%a' /state" in check
    assert "stat -c '%a' /applications" in check

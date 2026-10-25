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
        "resident-root-layout",
    ]
    assert profile["boot_a"]["providers"]["/usr/bin/login"] == (
        "util-linux-login additive stage"
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
    package = load_package(CATALOGUE / "util-linux/stages/login")
    assert package.outputs == ("usr/bin/login",)
    assert package.sources[0]["sha256"] == (
        "03a05d3adf9602ef128f2da05b84b3205ce60c351e5737c0370f74000679ce8a"
    )
    commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in package.steps[phase]
    )
    assert "--disable-all-programs --enable-login" in commands
    assert "--disable-login" not in commands
    assert "./login --version" in commands
    assert 'install -Dm755 login "$DESTDIR/usr/bin/login"' in commands

    shadow = literal(CATALOGUE / "shadow/recipe-plan.py")
    assert shadow["status"] == "resident-b-deferred"
    assert "not a Boot A login provider" in shadow["notes"]


def test_resident_root_layout_is_provenance_tracked_package():
    stage = CATALOGUE / "resident-root-layout/stages/final"
    package = load_package(stage)
    assert package.outputs == ("applications", "state")
    assert package.output_trees == ("state", "applications")
    assert package.build_dependencies == ()
    assert package.runtime_dependencies == ()

    fixture = stage / "fixtures/layout-v1.txt"
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == (
        "623e1054fbcc5738fc8ee2f557cb76b410b2b455a66ccb1e8cdf2aa84d51ebe9"
    )
    commands = "\n".join(
        " ".join(argv)
        for phase in ("build", "test", "install")
        for argv in package.steps[phase]
    )
    assert 'install -d -m 0000 "$DESTDIR/state" "$DESTDIR/applications"' in commands


def test_host_boot_plan_selects_only_targeted_boot_a_additions():
    plan = literal(ROOT / "project/bootstrap/host-boot-packages.py")
    stages = {item["id"]: item for item in plan["stages"]}
    assert stages["util-linux-login"] == {
        "id": "util-linux-login",
        "project": "util-linux",
        "stage": "login",
        "recipe": "util-linux/stages/login",
    }
    assert stages["resident-root-layout-final"] == {
        "id": "resident-root-layout-final",
        "project": "resident-root-layout",
        "stage": "final",
        "recipe": "resident-root-layout/stages/final",
    }
    assert "util-linux-login" in plan["targets"]
    assert "resident-root-layout-final" in plan["targets"]

    check = (ROOT / "project/bootstrap/host-boot-packages-check.sh").read_text()
    assert "/usr/bin/login --version" in check
    assert "/usr/sbin/agetty --version" in check
    assert "stat -c '%a' /state" in check
    assert "stat -c '%a' /applications" in check

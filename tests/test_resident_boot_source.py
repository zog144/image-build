from pathlib import Path

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
        "shadow",
        "systemd",
        "e2fsprogs",
        "kmod",
    ]
    assert profile["boot_a"]["providers"]["/usr/bin/login"] == (
        "Shadow 4.20.2 login-only stage without PAM"
    )
    assert profile["resident_b"]["deferred_projects"] == [
        "shadow-account-policy",
        "box-control",
        "root-control",
    ]
    items = {item["project"]: item for item in profile["items"]}
    assert items["shadow"]["group"] == "base"
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
    build = literal(CATALOGUE / "systemd/stages/final/build.py")
    command = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in build.get(phase, [])
    )
    assert "-Defi=true" in command
    assert "-Dbootloader=enabled" in command
    assert "-Dbootloader=disabled" not in command

    manifest = literal(CATALOGUE / "systemd/stages/final/produce-manifest.py")
    outputs = manifest["required"]
    assert "usr/lib/systemd/boot/efi/systemd-bootx64.efi" in outputs
    assert "usr/lib/systemd/system/getty@.service" in outputs
    assert "usr/lib/systemd/system/serial-getty@.service" in outputs
    assert {"state", "applications"} <= set(manifest["trees"])


def test_boot_a_login_is_shadow_nonpam_and_util_linux_stays_nologin_only():
    util = load_package(CATALOGUE / "util-linux/stages/nologin")
    assert util.outputs == ("usr/sbin/nologin",)
    util_commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in util.steps[phase]
    )
    assert "--enable-login" not in util_commands

    login = load_package(CATALOGUE / "shadow/stages/login")
    assert login.outputs == ("usr/bin/login",)
    assert login.sources[0]["sha256"] == (
        "b89f432b75ae55a2d852b446d0365484795fdf533ab97d550e325fa15594a224"
    )
    commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in login.steps[phase]
    )
    assert "--without-libpam" in commands
    assert "--disable-logind" in commands
    assert "! readelf -d src/login | grep -q 'libpam'" in commands
    assert 'install -Dm755 src/login "$DESTDIR/usr/bin/login"' in commands

    shadow = literal(CATALOGUE / "shadow/recipe-plan.py")
    assert shadow["status"] == "boot-a-login-authored-resident-b-account-policy-deferred"


def test_resident_root_layout_is_bound_to_required_systemd_rebuild():
    package = load_package(CATALOGUE / "systemd/stages/final")
    commands = "\n".join(
        " ".join(argv)
        for phase in ("configure", "build", "test", "install")
        for argv in package.steps[phase]
    )
    assert 'install -d -m 0000 "$DESTDIR/state" "$DESTDIR/applications"' in commands
    assert {"state", "applications"} <= set(package.output_trees)


def test_generic_host_boot_batch_does_not_claim_login_or_resident_layout():
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
    assert "/usr/bin/login" not in check
    assert "stat -c '%a' /state" not in check
    assert "stat -c '%a' /applications" not in check


def test_targeted_boot_plan_binds_shadow_catalogue_source_and_installed_check():
    plan = literal(ROOT / "project/bootstrap/boot-a-targeted.py")
    shadow = next(item for item in plan["stages"] if item["id"] == "shadow-login")
    assert shadow["pin_policy"] == "catalogue-source"
    assert plan["overlay_targets"] == ["systemd-final", "shadow-login"]
    check = (ROOT / "project/bootstrap/boot-a-targeted-check.sh").read_text()
    assert "! readelf -d /usr/bin/login | grep -q 'libpam'" in check
    assert "systemd-bootx64.efi" in check
    assert "stat -c '%a' /state" in check
    assert "stat -c '%a' /applications" in check

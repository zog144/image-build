"""Negative resident controller service/sockets and executable contract tests."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "resident_install_review",
    ROOT / "tools/verify_resident_b_controller_install_security.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def record(name, part):
    return review.base.data(ROOT/"project/package"/name/"stages/final"/part)


def mutated(name, part, transform):
    value=copy.deepcopy(record(name,part))
    transform(value)
    with pytest.raises(ValueError, match="NOT READY"):
        review.verify(overrides={(name,"stages/final/"+part): value})


def test_positive_source_only_boundary_preserves_native_hold():
    assert review.verify() == {
        "source_install_contract": "EXACT_STAGE_AND_PRIVILEGE_BOUNDARY_REVIEW",
        "root_service": "DISABLED_ROOT_ONLY",
        "box_control": "ONE_SHOT_NONROOT_UNSELECTED",
        "socket_group": "NOT_PROVISIONED_BY_IMAGE",
        "state_identity": "REQUIRES_PROTECTED_NATIVE_RECEIPT",
        "native_install": "NO_GO",
    }


@pytest.mark.parametrize("option,replacement", [
    ("User=root", "User=nobody"),
    ("Group=root", "Group=box-control"),
    ("Type=exec", "Type=simple"),
    ("ExecStart=/usr/bin/root-control", "ExecStart=/usr/bin/box-control"),
    ("RuntimeDirectory=zog", "RuntimeDirectory=tmp"),
    ("RuntimeDirectoryMode=0755", "RuntimeDirectoryMode=0777"),
    ("UMask=0007", "UMask=0000"),
    ("ConditionPathIsMountPoint=/state", "ConditionPathExists=/state"),
    ("RequiresMountsFor=/state", "RequiresMountsFor=/tmp"),
    ("Restart=no", "Restart=always"),
    ("Environment=ROOT_CONTROL_JOURNAL_BARRIER=0", "Environment=ROOT_CONTROL_SOCKET_GID=1234"),
])
def test_mismatched_root_service_identity_mount_and_socket_policies_fail(option,replacement):
    def change(stage):
        assert option in stage["install"][0][-1]
        stage["install"][0][-1]=stage["install"][0][-1].replace(option,replacement)
    mutated("root-control","build.py",change)


@pytest.mark.parametrize("insert", [
    "\n[Install]\nWantedBy=multi-user.target",
    "\nEnvironmentFile=-/state/private.env",
    "\nSupplementaryGroups=users",
    "\nExecStartPre=/usr/bin/true",
    "\nSocketGroup=users",
    "\nEnvironment=ROOT_CONTROL_SOCKET_GID=42",
])
def test_root_service_must_not_gain_activation_grants_or_extra_options(insert):
    def change(stage):
        terminal="\nZOG_ROOT_CONTROL_UNIT"
        assert terminal in stage["install"][0][-1]
        stage["install"][0][-1]=stage["install"][0][-1].replace(terminal,insert+terminal)
    mutated("root-control","build.py",change)


@pytest.mark.parametrize("name",["box-control","root-control"])
def test_wrong_installed_binary_path_rejected(name):
    def change(stage):
        stage["install"][0][-1]=stage["install"][0][-1].replace(
            f"$DESTDIR/usr/bin/{name}",f"$DESTDIR/usr/local/bin/{name}")
    mutated(name,"build.py",change)
    def change_manifest(stage):
        stage["required"].remove(f"usr/bin/{name}")
        stage["required"].append(f"usr/local/bin/{name}")
    mutated(name,"produce-manifest.py",change_manifest)


@pytest.mark.parametrize("name,missing", [
    ("box-control", "python-resident312-final"),
    ("box-control", "resident312-dbus-next-final"),
    ("box-control", "resident312-image-build-final"),
    ("root-control", "box-control-final"),
    ("root-control", "python-resident312-final"),
    ("root-control", "resident312-dbus-next-final"),
    ("root-control", "resident312-image-build-final"),
    ("root-control", "systemd-final"),
])
def test_missing_runtime_predecessor_denied(name,missing):
    def change(stage):
        stage["runtime"].remove(missing)
    mutated(name,"dependencies.py",change)


@pytest.mark.parametrize("field,value",[
    ("runtime_uid", "root"),
    ("working_directory","/state/shared"),
    ("root_control_socket","/tmp/root-control.sock"),
    ("socket_access","world-writable socket"),
    ("unit_installed",True),
    ("auto_enable",True),
])
def test_box_control_cannot_become_privileged_daemon_or_receive_shared_state(field,value):
    def change(stage):
        stage[field]=value
    mutated("box-control","integration.py",change)


@pytest.mark.parametrize("field,value",[
    ("runtime_uid","nobody"),
    ("runtime_gid","users"),
    ("socket_path","/tmp/root-control.sock"),
    ("socket_group","any local user"),
    ("unit_auto_enabled",True),
    ("state","/tmp"),
    ("native_accepted",True),
])
def test_root_control_service_and_socket_contract_cannot_be_forged(field,value):
    def change(stage):
        stage[field]=value
    mutated("root-control","integration.py",change)


def test_no_box_control_daemon_unit_and_no_root_baked_socket_gid():
    box=record("box-control","build.py")["install"][0][-1]
    root=record("root-control","build.py")["install"][0][-1]
    assert "systemctl" not in box
    assert "ROOT_CONTROL_SOCKET_GID" not in root
    assert "EnvironmentFile=" not in root
    assert "WantedBy=" not in root


def test_root_daemon_source_requires_private_socket_and_explicit_positive_gid():
    import os
    selected=os.getenv("ZOG_REVIEW_ROOT_DAEMON")
    if not selected: pytest.skip("upstream source-only checkout required for this test")
    source=Path(selected).read_text()
    review.check_source_daemon(source)
    for old,new in [
        ('"/run/zog/root-control.sock"','"/tmp/root-control.sock"'),
        ("os.chmod(self.socket_path, 0o660)","os.chmod(self.socket_path, 0o666)"),
        ("if self.socket_group_gid is not None:","if True:"),
        ("socket_group_gid < 1","socket_group_gid < 0"),
    ]:
        assert old in source
        with pytest.raises(ValueError, match="NOT READY"):
            review.check_source_daemon(source.replace(old,new))


def test_box_cli_source_is_one_shot_unprivileged():
    import os
    selected=os.getenv("ZOG_REVIEW_BOX_CLI")
    if not selected: pytest.skip("upstream source-only checkout required for this test")
    source=Path(selected).read_text()
    review.check_source_cli(source)
    with pytest.raises(ValueError, match="NOT READY"):
        review.check_source_cli(source.replace("BoxControl.discover().evaluate()",
                                               "RootControlDaemon().serve()"))


def test_unit_parser_does_not_accept_extra_section_key_or_weakening():
    script=record("root-control","build.py")["install"][0][-1]
    unit=review.unit_from_recipe(script)
    assert review.verify_systemd_unit(unit)
    for rewritten in [
        unit.replace("Group=root","Group=users"),
        unit.replace("ExecStart=/usr/bin/root-control", "ExecStart=/usr/local/bin/root-control"),
        unit + "\n[Install]\nWantedBy=multi-user.target\n",
        unit.replace("RuntimeDirectoryMode=0755","RuntimeDirectoryMode=0777"),
    ]:
        with pytest.raises(ValueError,match="NOT READY"):
            review.verify_systemd_unit(rewritten)

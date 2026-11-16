"""Real host-install PR43 offline sysusers against disposable Boot A compositions.

When the public companion source is checked out, these tests execute the
reviewed source file and the real OS-owned systemd-sysusers against a temporary
rootfs. No compiler-host account is created or changed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import pytest

from zog.image_build import resident_boot_accounts as service
from zog.image_build.errors import ImageBuildError
from zog.image_build.metadata import identity
from zog.image_build.staging_durability import inventory


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "companions/host-install-resident-accounts/src/zog/host_install/resident_accounts.py"
)


def _binding():
    if not SOURCE.is_file():
        if os.environ.get("REQUIRE_HOST_INSTALL_ACCOUNTS") == "1":
            pytest.fail("exact host-install PR43 companion source is required")
        pytest.skip("host-install PR43 checkout is provided by focused CI")
    tool = shutil.which("systemd-sysusers")
    if not tool:
        pytest.fail("real systemd-sysusers must be available")
    return service.source_binding(SOURCE, str(Path(tool).resolve()))


def _candidate(tmp_path, *, accounts=True):
    root = tmp_path / "disposable-unpublished-root"
    for d in ("etc", "usr/lib/sysusers.d", "usr/lib/systemd", "usr/bin"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "usr/lib/os-release").write_text(
        'NAME="Zog"\nID=zog\nPRETTY_NAME="Zog"\n'
    )
    (root / "etc/os-release").symlink_to("../usr/lib/os-release")
    for p in ("usr/lib/systemd/systemd", "usr/bin/dbus-daemon"):
        (root / p).write_text("fixture executable")
        (root / p).chmod(0o755)
    (root / "usr/lib/sysusers.d/systemd-journal.conf").write_text(
        "# vendor systemd 261.2\ng systemd-journal - -\n"
    )
    (root / "usr/lib/sysusers.d/dbus.conf").write_text(
        '# vendor dbus 1.16.2\nu messagebus - "System Message Bus" /nonexistent\n'
    )
    if accounts:
        (root / "etc/passwd").write_text(
            "root:x:0:0:root:/root:/bin/sh\n"
            "zog-system:x:970:970:existing service:/var/lib/zog:/usr/sbin/nologin\n"
        )
        (root / "etc/group").write_text(
            "root:x:0:\nzog-system:x:970:\n"
        )
    plan = {
        "schema": 1,
        "expected_outputs": inventory(root),
        "parent": {"generation": "fixture"},
    }
    work = tmp_path / "operation"
    work.mkdir()
    return root, work, plan


def test_pinned_source_and_offline_service_accounts_integrate_with_final_inventory(tmp_path):
    binding = _binding()
    root, work, plan = _candidate(tmp_path)
    before_passwd = (root / "etc/passwd").read_bytes()
    before_group = (root / "etc/group").read_bytes()
    receipt = service.materialize(root, work, plan, binding)
    assert receipt["source"]["host_install_commit"] == service.SOURCE_COMMIT
    assert receipt["verification"]["materialized"] is True
    assert receipt["materialization"]["after"]["created_users"] == ["messagebus"]
    assert receipt["materialization"]["after"]["created_groups"] == [
        "messagebus", "systemd-journal",
    ]
    assert (root / "etc/passwd").read_bytes().startswith(before_passwd)
    assert (root / "etc/group").read_bytes().startswith(before_group)
    assert receipt["delta"] == sorted(set(receipt["delta"]))
    assert "etc/passwd" in receipt["delta"]
    assert "etc/group" in receipt["delta"]
    assert inventory(root) == receipt["final_outputs"]
    frozen = (work / service.RESULT).read_bytes()
    assert service.materialize(root, work, plan, binding) == receipt
    assert (work / service.RESULT).read_bytes() == frozen
    assert service.verify_materialized(root, work, plan, binding) == receipt
    for data in ("etc/passwd", "etc/group"):
        assert "certbot-build" not in (root / data).read_text()


def test_missing_base_database_has_explicit_minimal_root_source_contract(tmp_path):
    binding = _binding()
    root, work, plan = _candidate(tmp_path, accounts=False)
    result = service.materialize(root, work, plan, binding)
    prepared = json.loads((work / service.PREPARED).read_text())
    assert prepared["base"]["mode"] == "minimal-root"
    assert prepared["base"]["contract"] == service.BASE_CONTRACT
    assert (root / "etc/passwd").read_bytes().startswith(service.BASE_PASSWD)
    assert (root / "etc/group").read_bytes().startswith(service.BASE_GROUP)
    assert result["verification"]["materialized"] is True


def test_partial_account_base_is_held_before_any_sysusers_write(tmp_path):
    binding = _binding()
    root, work, plan = _candidate(tmp_path, accounts=False)
    (root / "etc/passwd").write_bytes(service.BASE_PASSWD)
    plan["expected_outputs"] = inventory(root)
    with pytest.raises(ImageBuildError, match="partial resident base"):
        service.materialize(root, work, plan, binding)
    assert not (work / service.RESULT).exists()


def test_interrupted_after_preparation_resumes_without_recomposing(tmp_path, monkeypatch):
    binding = _binding()
    root, work, plan = _candidate(tmp_path)
    original = service._account_command

    def interrupted(action, *_args):
        if action == "inspect":
            raise ImageBuildError("fixture interruption after durable prepare")
        return original(action, *_args)

    monkeypatch.setattr(service, "_account_command", interrupted)
    with pytest.raises(ImageBuildError, match="fixture interruption"):
        service.materialize(root, work, plan, binding)
    assert (work / service.PREPARED).is_file()
    assert not (work / service.RESULT).exists()
    monkeypatch.setattr(service, "_account_command", original)
    result = service.materialize(root, work, plan, binding)
    assert result["verification"]["materialized"] is True
    assert service.verify_materialized(root, work, plan, binding) == result


def test_recovered_materialized_output_refuses_non_account_changes(tmp_path):
    binding = _binding()
    root, work, plan = _candidate(tmp_path)
    service.materialize(root, work, plan, binding)
    (root / "usr/bin/dbus-daemon").write_text("tampered service executable")
    with pytest.raises(ImageBuildError, match="inventory changed"):
        service.verify_materialized(root, work, plan, binding)


def test_unreviewed_vendor_fragment_refused_before_publication(tmp_path):
    binding = _binding()
    root, work, plan = _candidate(tmp_path)
    (root / "usr/lib/sysusers.d/dbus.conf").write_text(
        "u messagebus -\nu compiler-worker -\n"
    )
    plan["expected_outputs"] = inventory(root)
    with pytest.raises(ImageBuildError, match="refused: inspect"):
        service.materialize(root, work, plan, binding)
    assert not (work / service.RESULT).exists()


def test_rejected_compiler_user_and_source_substitution(tmp_path):
    binding = _binding()
    root, work, plan = _candidate(tmp_path)
    (root / "etc/passwd").write_text(
        (root / "etc/passwd").read_text() +
        "certbot-build-worker:x:24202:24202:rejected:/nonexistent:/usr/sbin/nologin\n"
    )
    plan["expected_outputs"] = inventory(root)
    with pytest.raises(ImageBuildError, match="refused: inspect"):
        service.materialize(root, work, plan, binding)
    changed = tmp_path / "altered-source.py"
    changed.write_text(SOURCE.read_text() + "\n# added\n")
    with pytest.raises(ImageBuildError, match="differs"):
        service.source_binding(changed, binding["sysusers_executable"])


def test_new_targeted_producer_requires_account_receipt_before_verification():
    from zog.image_build import resident_boot_targeted as producer
    source = Path(producer.__file__).read_text()
    assert "accounts.materialize(root, work, composition, account_source)" in source
    assert source.index("accounts.verify_materialized(root, work, composition, account_source)") < source.index("verify_installed(" , source.index("def run("))
    assert "resident_service_accounts" in source
    assert "account_material" in source
    assert "resident_accounts_receipt_sha256" in source
    assert "final_expected_outputs" in source

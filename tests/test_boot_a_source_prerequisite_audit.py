"""Boot A source may be complete while native successor and resident B are on HOLD."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("boot_a_audit",ROOT/"tools/verify_boot_a_source_prerequisites.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
AUDIT=json.loads((ROOT/"project/host/boot-a-source-prerequisite-audit.json").read_text())

def test_boot_a_source_contract_without_native_generation_acceptance():
    result=mod.inspect(AUDIT)
    assert result["source_contract"]=="PASS"
    assert result["native_generation"]=="UNVERIFIED"
    assert result["boot_a"]=="NOT_AUTHORIZED"

@pytest.mark.parametrize("field,value",[
    ("selected_successor_generation_id","a"*64),
    ("installed_generation_verification",{"fake":"approved"}),
    ("boot_admission_authorized",True),
    ("boot_native_pass",True),
    ("successor_build_submission_authorized",True),
    ("historical_failure","PASS"),
    ("resident_b_status","PASS"),
])
def test_refuses_invented_successor_or_early_admission(field,value):
    altered=copy.deepcopy(AUDIT)
    altered[field]=value
    with pytest.raises(ValueError):
        mod.inspect(altered)

def test_rejects_missing_kmod_and_required_efi_os_release_producers():
    stages={name:mod.literal(path/"produce-manifest.py") for name,path in {
        "systemd-final":mod.PACKAGE/"systemd/stages/final",
        "shadow-login":mod.PACKAGE/"shadow/stages/login",
        "kmod-final":mod.PACKAGE/"kmod/stages/final",
        "e2fsprogs-final":mod.PACKAGE/"e2fsprogs/stages/final",
    }.items()}
    for name,item in (("kmod-final","usr/bin/kmod"),
                      ("systemd-final","usr/lib/os-release"),
                      ("systemd-final","usr/lib/systemd/boot/efi/systemd-bootx64.efi"),
                      ("systemd-final","etc/os-release")):
        modified=copy.deepcopy(stages)
        modified[name]["required"].remove(item)
        with pytest.raises(ValueError,match="missing source package output"):
            mod.inspect(AUDIT,stages=modified)

@pytest.mark.parametrize("missing",["test -f /usr/lib/os-release","readlink /etc/os-release",
                                     "stat -c '%a' /state","systemd-bootx64.efi"])
def test_installed_check_cannot_omit_boot_prerequisite(missing):
    s=(ROOT/"project/bootstrap/boot-a-targeted-check.sh").read_text().replace(missing,"OMITTED")
    with pytest.raises(ValueError,match="missing installed Boot A check"):
        mod.inspect(AUDIT,installed_check=s)

def test_foreign_kernel_record_is_historical_not_a_new_native_acceptance():
    altered=copy.deepcopy(AUDIT)
    altered["foreign_al2023_provider"]["status"]="approved-for-next-boot"
    with pytest.raises(ValueError,match="foreign kernel"):
        mod.inspect(altered)
    altered=copy.deepcopy(AUDIT)
    altered["foreign_al2023_provider"]["initramfs_sha256"]="fake"
    with pytest.raises(ValueError,match="foreign boot-bundle"):
        mod.inspect(altered)

def test_mode_0000_mounts_not_relaxed():
    altered=copy.deepcopy(AUDIT)
    altered["mountpoints"]["state"]["mode"]="0755"
    with pytest.raises(ValueError,match="non-restrictive"):
        mod.inspect(altered)

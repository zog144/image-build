#!/usr/bin/env python3
"""Read-only Boot A *source* inspection; never accept a native generation here."""
import ast
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/"project/package"
AUDIT=ROOT/"project/host/boot-a-source-prerequisite-audit.json"
HEX64=re.compile(r"[0-9a-f]{64}")

def literal(path):
    return ast.literal_eval(Path(path).read_text())

def inspect(record, *, stages=None, installed_check=None):
    if record.get("schema")!="zog-boot-a-source-prerequisite-audit-v1":
        raise ValueError("unrecognized Boot A source contract")
    if record.get("selected_successor_generation_id") is not None or record.get("installed_generation_verification") is not None:
        raise ValueError("source CI cannot authenticate an invented Boot A successor generation")
    if any(record.get(x) is not False for x in ("boot_admission_authorized","boot_native_pass",
              "successor_build_submission_authorized","certificate_dependency")):
        raise ValueError("source-only audit claims unauthorized native boot or certification dependency")
    if record.get("historical_failure")!="REJECTED_SWITCH_ROOT_OS_TREE_MISSING":
        raise ValueError("historical switch-root failure has been misclassified")
    if record.get("historical_rejected_generation")!="5af34ec67cbfdcd1e7936bf70e3cf2f5c6945c7e3de5f95993918325f6e29c44":
        raise ValueError("historical failed generation identity changed")
    if record.get("resident_b_status")!="DEFERRED_UNVERIFIED":
        raise ValueError("Resident B prematurely accepted")
    for key in ("reviewed_image_build_unstable_before_audit","reviewed_boot_a_source_correction","host_install_source_contract"):
        if not isinstance(record.get(key),str) or not HEX64.fullmatch(record[key]):
            raise ValueError("unbound original source revision: "+key)
    foreign=record.get("foreign_al2023_provider",{})
    if foreign.get("status")!="historically_observed_in_failed_generation_reverify_for_successor":
        raise ValueError("foreign kernel incorrectly promoted to successor")
    for key in ("kernel_sha256","initramfs_sha256","modules_inventory_sha256","kernel_config_sha256"):
        if not HEX64.fullmatch(foreign.get(key,"")):
            raise ValueError("missing exact foreign boot-bundle hash: "+key)
    if not {"root=PARTUUID=","ext4 read-only","NVMe/virtio","switch-root"}.issubset(
        {s for s in ("root=PARTUUID=","ext4 read-only","NVMe/virtio","switch-root")
         if any(s in v for v in foreign.get("native_required",[]))}):
        raise ValueError("foreign initramfs boot capability obligation missing")
    if any(record.get("mountpoints",{}).get(n)!={"type":"directory","mode":"0000","owner":"root:root","empty":True}
           for n in ("state","applications")):
        raise ValueError("mutable/non-restrictive resident mountpoint")
    required=record.get("boot_a_required",{})
    if set(required)!={"systemd-final","shadow-login","e2fsprogs-final","kmod-final"}:
        raise ValueError("required native OS package predecessor missing")
    paths={"systemd-final":PACKAGE/"systemd/stages/final",
           "shadow-login":PACKAGE/"shadow/stages/login",
           "e2fsprogs-final":PACKAGE/"e2fsprogs/stages/final",
           "kmod-final":PACKAGE/"kmod/stages/final"}
    stages=stages or {name:literal(path/"produce-manifest.py") for name,path in paths.items()}
    for name,outputs in required.items():
        if not set(outputs).issubset(set(stages[name].get("required",[]))):
            raise ValueError("missing source package output prerequisite: "+name)
    systemd=literal(paths["systemd-final"]/"build.py")
    commands={phase:"\n".join(step[-1] for step in systemd.get(phase,[])) for phase in ("configure","test","install")}
    for flag in record["efi"]["required_build_options"]:
        if flag not in commands["configure"]:
            raise ValueError("EFI and SBAT source configuration missing: "+flag)
    if "-Dbootloader=disabled" in commands["configure"]:
        raise ValueError("EFI bootloader accidentally disabled")
    if "objcopy --dump-section .sbat=" not in commands["test"]:
        raise ValueError("missing actual EFI SBAT section test")
    if "ln -s ../usr/lib/os-release" not in commands["install"] or 'ID=zog' not in commands["install"]:
        raise ValueError("missing immutable resident OS-tree marker")
    if 'install -d -m 0000 "$DESTDIR/state" "$DESTDIR/applications"' not in commands["install"]:
        raise ValueError("non-restrictive resident mountpoint install")
    installed_check=installed_check if installed_check is not None else (
        ROOT/"project/bootstrap/boot-a-targeted-check.sh").read_text()
    for marker in ("test -f /usr/lib/os-release", "test -L /etc/os-release",
                   "readlink /etc/os-release", "stat -c '%a' /state",
                   "stat -c '%a' /applications", "systemd-bootx64.efi",
                   "test -x /usr/bin/login"):
        if marker not in installed_check:
            raise ValueError("missing installed Boot A check: "+marker)
    if not set(record["boot_a_parent_inherited_unverified"])=={
        "usr/bin/bash","usr/sbin/agetty","usr/bin/findmnt"}:
        raise ValueError("unverified inherited Boot A programs concealed")
    if len(record.get("expected_resident_b_paths",[]))<15:
        raise ValueError("Resident B requirements concealed")
    return {"source_contract":"PASS", "native_generation":"UNVERIFIED", "boot_a":"NOT_AUTHORIZED",
            "resident_b":"DEFERRED", "historical_generation":"REJECTED"}

if __name__=="__main__":
    print(json.dumps(inspect(json.loads(AUDIT.read_text())),sort_keys=True))

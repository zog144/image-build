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
GIT_SHA40=re.compile(r"[0-9a-f]{40}")


ROOT_FIELDS = frozenset((
    "schema","reviewed_image_build_unstable_before_audit",
    "reviewed_boot_a_source_correction","host_install_source_contract",
    "source_contract","selected_successor_generation_id","installed_generation_verification",
    "historical_rejected_generation","historical_failure","efi","boot_a_required",
    "boot_a_parent_inherited_unverified","expected_resident_b_paths",
    "resident_b_status","os_tree","mountpoints","immutable_generation_forbids",
    "foreign_al2023_provider","boot_admission_authorized","boot_native_pass",
    "successor_build_submission_authorized","certificate_dependency",
    "early_userspace_evidence_status","protected_successor_requirements",
))
SOURCE_REVISIONS = {
    "reviewed_image_build_unstable_before_audit":"1f07e83dbd80dacb9bed0d6494c697375f0e26cd",
    "reviewed_boot_a_source_correction":"68d6397ca20c4651df8f13c8a840dc8f77d55034",
    "host_install_source_contract":"cf3ca569d6109ab75e5082dd4109698680155984",
}
EFI_FLAGS = frozenset(("-Defi=true","-Dbootloader=enabled",
                       "-Dsbat-distro=zog","-Dsbat-distro-generation=1"))
EFI_PATH = "usr/lib/systemd/boot/efi/systemd-bootx64.efi"
REQUIRED_OS_TREE = {
    "regular_file":"usr/lib/os-release",
    "symlink":"etc/os-release",
    "target":"../usr/lib/os-release",
    "identity":'NAME="Zog"\nID=zog\nPRETTY_NAME="Zog"\n',
    "required_by":"initrd switch-root safety check with /usr/lib/systemd/systemd",
}
REQUIRED_BOOT_A = {
    "systemd-final": frozenset((
        "usr/lib/systemd/systemd","usr/lib/systemd/systemd-journald",
        "usr/lib/systemd/systemd-udevd","usr/bin/systemctl",
        "usr/bin/journalctl","usr/bin/udevadm",
        "usr/lib/systemd/system/getty@.service",
        "usr/lib/systemd/system/serial-getty@.service",
        EFI_PATH,"usr/lib/os-release","etc/os-release")),
    "shadow-login":frozenset(("usr/bin/login",)),
    "e2fsprogs-final":frozenset(("usr/sbin/fsck.ext4",)),
    "kmod-final":frozenset(("usr/bin/kmod",)),
}
HISTORICAL_FOREIGN = {
    "release":"6.18.44-99.149.amzn2023.x86_64",
    "kernel_sha256":"1faf0278011e0d62f01b28ddf81fc32af9e3fd032be0b805a1d38d981933431b",
    "initramfs_sha256":"06bca6e41de36109384ba019212ab1be72643a578d0afb9f3fa3c561a190f599",
    "modules_inventory_sha256":"8dbf40e1497ff8857a6a0602e66626155e897cfd54b6731aa1eea8f842899da4",
    "kernel_config_sha256":"de3812ae0e81108f86550781cac8302c8b400bf7bfefe5ea23e115074b6e0ef6",
    "dracut":"102-3.amzn2023.0.4.x86_64",
}
REQUIRED_RESIDENT_B = frozenset((
    "usr/lib/systemd/systemd-networkd","usr/lib/systemd/systemd-resolved",
    "usr/lib/systemd/systemd-timesyncd","usr/bin/networkctl","usr/bin/resolvectl",
    "usr/bin/python3","usr/bin/dbus-daemon","usr/sbin/ip","usr/sbin/ss",
    "usr/sbin/tc","usr/sbin/mkfs.ext4","usr/sbin/e2fsck",
    "usr/bin/host-install","usr/bin/host-discover",
    "usr/bin/box-control","usr/bin/root-control","usr/lib/systemd/system/dbus.service",
))
FORBIDDEN_IN_ROOTFS = frozenset((
    "machine-id","Host identity private key",
    "installation-specific GPT/partition UUID","station credentials",
    "Cloudflare credentials"
))

def literal(path):
    return ast.literal_eval(Path(path).read_text())

def inspect(record, *, stages=None, installed_check=None):
    if set(record)!=ROOT_FIELDS:
        raise ValueError("unreviewed Boot A admission field or missing contract")
    if record.get("schema")!="zog-boot-a-source-prerequisite-audit-v1":
        raise ValueError("unrecognized Boot A source contract")
    if record.get("source_contract")!="source-checked-native-successor-and-boot-not-accepted":
        raise ValueError("source-only contract wrongly promoted")
    if record.get("early_userspace_evidence_status")!="HISTORICAL_PARTUUID_RO_EXT4_SWITCH_ROOT_REACHED_BUT_RESIDENT_PID1_NOT_REACHED":
        raise ValueError("rejected first-boot early userspace evidence reclassified")
    if len(record.get("protected_successor_requirements",[]))!=7:
        raise ValueError("protected successor provenance requirements omitted")
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
        if not isinstance(record.get(key),str) or record[key]!=SOURCE_REVISIONS[key]:
            raise ValueError("unbound original source revision: "+key)
    if record.get("os_tree")!=REQUIRED_OS_TREE:
        raise ValueError("immutable OS-tree exact identity/target changed")
    efi=record.get("efi",{})
    if (efi.get("producer")!="systemd-final" or
        efi.get("selected_source_recipe")!="project/package/systemd/stages/final/build.py" or
        efi.get("required_stage_output")!=EFI_PATH or
        set(efi.get("required_build_options",[]))!=EFI_FLAGS or
        efi.get("native_verified") is not False):
        raise ValueError("EFI/SBAT source or native authority contract changed")
    if (not isinstance(record.get("boot_a_required"),dict) or
        {k:frozenset(v) for k,v in record["boot_a_required"].items()} != REQUIRED_BOOT_A):
        raise ValueError("missing required Boot A program or OS-tree prerequisite")
    if frozenset(record.get("expected_resident_b_paths",[]))!=REQUIRED_RESIDENT_B:
        raise ValueError("Resident B required source paths changed")
    if frozenset(record.get("immutable_generation_forbids",[]))!=FORBIDDEN_IN_ROOTFS:
        raise ValueError("installation identity or secrets cannot enter rootfs")
    foreign=record.get("foreign_al2023_provider",{})
    if foreign.get("status")!="historically_observed_in_failed_generation_reverify_for_successor":
        raise ValueError("foreign kernel incorrectly promoted to successor")
    for key, expected in HISTORICAL_FOREIGN.items():
        if foreign.get(key)!=expected:
            raise ValueError("historical foreign boot-bundle identity changed: "+key)
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
    for flag in EFI_FLAGS:
        if flag not in commands["configure"]:
            raise ValueError("EFI and SBAT source configuration missing: "+flag)
    if "-Dbootloader=disabled" in commands["configure"]:
        raise ValueError("EFI bootloader accidentally disabled")
    if "objcopy --dump-section .sbat=" not in commands["test"] or "systemd-boot.zog,1,Zog Project,systemd,261.2," not in commands["test"]:
        raise ValueError("missing actual EFI SBAT section test")
    if ("ln -s ../usr/lib/os-release" not in commands["install"] or
        any(fragment not in commands["install"] for fragment in ('NAME="Zog"','ID=zog','PRETTY_NAME="Zog"'))):
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
    shadow=literal(paths["shadow-login"]/"build.py")
    shadow_cmd="\n".join(step[-1] for phase in ("configure","build","test","install")
                         for step in shadow.get(phase,[]))
    if ("--without-libpam" not in shadow_cmd or
        "make -C lib -j8 libshadow.la" not in shadow_cmd or
        "make -C src -j8 login" not in shadow_cmd or
        'install -Dm755 src/login "$DESTDIR/usr/bin/login"' not in shadow_cmd):
        raise ValueError("Shadow non-PAM login source prerequisite missing")
    kmod=literal(paths["kmod-final"]/"build.py")
    if ("meson compile -C build" not in kmod["build"][0][-1] or
        "build/kmod --version" not in kmod["test"][0][-1]):
        raise ValueError("Kmod tool build/test prerequisite missing")
    return {"source_contract":"PASS", "native_generation":"UNVERIFIED", "boot_a":"NOT_AUTHORIZED",
            "resident_b":"DEFERRED", "historical_generation":"REJECTED"}

if __name__=="__main__":
    print(json.dumps(inspect(json.loads(AUDIT.read_text())),sort_keys=True))

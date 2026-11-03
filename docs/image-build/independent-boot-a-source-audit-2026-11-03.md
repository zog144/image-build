# Independent Boot A source prerequisite audit — 2026-11-03

Scope: image-build draft PR #10 against `unstable`, image-build issue #6, host-install issue #4; source-only. The existing rejected rootfs generation `5af34ec67cbfdcd1e7936bf70e3cf2f5c6945c7e3de5f95993918325f6e29c44` reached AL2023 kernel/initramfs, HOST-A PARTUUID ext4 read-only and switch-root but did **not** reach resident systemd PID1. The historical failure is `REJECTED_SWITCH_ROOT_OS_TREE_MISSING`. The immutable source correction at `68d6397ca20c4651df8f13c8a840dc8f77d55034` must produce an entirely **new** successor before any second Boot A installation plan is eligible.

## Source-contract verification

| Prerequisite | Source evidence checked | Still requires protected generation/native proof |
| --- | --- | --- |
| EFI and SBAT | Real systemd 261.2 stage requires `-Defi=true` and `-Dbootloader=enabled`, explicit Zog SBAT generation, original `.sbat` section extraction test and exact `usr/lib/systemd/boot/efi/systemd-bootx64.efi` output | New installed EFI bytes, their content hash, original image/provenance and identical ESP copy |
| OS-tree marker | Install stage creates `usr/lib/os-release` with exact `NAME="Zog"`, `ID=zog`, `PRETTY_NAME="Zog"` lines and symlinks `etc/os-release -> ../usr/lib/os-release` | New immutable installed root and switch-root acceptance; do not patch the historical generation |
| Early userspace | systemd/journald/udevd, getty and serial-getty units, Shadow non-PAM `usr/bin/login`, Kmod `usr/bin/kmod` and e2fsprogs `fsck.ext4` are mandatory stage outputs. Bash/agetty/findmnt are retained-parent requirements not yet re-attested | Full installed program/dependency closure, successful PID1, journal, getty and fail-safe recovery |
| Mounts | `/state` and `/applications` source install mode 0000; audit demands empty `root:root` directories | Authenticated installed inventory must prove exact owner/mode and emptiness. The source declaration alone cannot certify it |
| AL2023 first-boot provider | Retained kernel/initramfs/modules/config/dracut identities are **historical** pinned inputs; prior boot reached ext4 read-only HOST-A but failed later | Reverify matching bytes and module set, storage driver, exact selected PARTUUID and safe switch-root before later disposable boot |
| Resident B | Python SSL/SQLite/CA, networkd/resolved, D-Bus, iproute2 and host controllers remain listed | Deferred; not required to accept a minimal Boot A source contract and not inferred installed |

## Negative-readiness regression findings

The initial source audit allowed mutable `efi.required_build_options`, mutable os-release descriptors and extra unrecognized approval fields. The independent revision now pins required EFI flags and source revisions, exact original OS-tree lines and symlink target, exact required Boot A and Resident B path sets, and historical foreign kernel digests. It refuses `efi.native_verified=true`, `native_ready=true`, additional accepted-generation aliases, fake signed-looking IDs, a copy of the rejected generation as successor, an arbitrary 64-hex replacement kernel digest, omitted Shadow/Kmod/udevd/journald/getty paths, changes to the mountpoint contract, and silent removal of prohibited host identity/credential material.

The corrected audit also tests the actual Shadow non-PAM library→login build targets and Kmod executable build/test declarations; an authored source stage remains different from a built program. **No source audit validator is permitted to consume a supplied success receipt as protected evidence.** Real generation ID, canonical rootfs export, installed inventory and boot must be checked independently.

**Decision:** source prerequisites and review logic reconciled, independent compiler/boot witness not run. Neither image-build Regular nor host-install Regular is authorized here to publish or select a new rootfs generation. There is no certificate/ACME/DNS requirement for Boot A. The next native job and installation are separately authorized Work tasks.

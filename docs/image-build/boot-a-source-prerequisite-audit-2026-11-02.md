# Boot A and Resident B source prerequisite reconciliation — 2026-11-02

**Source audit only. No new generation, native verification or device write.**

This is a cross-owner audit against [image-build #6](https://github.com/zog144/image-build/issues/6) and [host-install #4](https://github.com/zog144/host-install/issues/4). It reads the actual `unstable@1f07e83dbd80dacb9bed0d6494c697375f0e26cd` source stages. The accepted target for source correction is `68d6397ca20c4651df8f13c8a840dc8f77d55034`; the historical installed generation `5af34ec67cbfdcd1e7936bf70e3cf2f5c6945c7e3de5f95993918325f6e29c44` is **rejected** for missing OS-tree marker, not reactivated or patched.

## Exact source findings

| Requirement | Source disposition | Unresolved real-generation evidence |
| --- | --- | --- |
| EFI systemd-boot | The selected systemd 261.2 recipe uses `-Defi=true -Dbootloader=enabled`, explicit Zog SBAT, EFI `.sbat` extraction, and requires `usr/lib/systemd/boot/efi/systemd-bootx64.efi`. Earlier `-Dbootloader=disabled` is corrected. | Reopen exact new generation, verify EFI PE image/SBAT bytes and installation-specific ESP copy |
| Resident switch-root OS identity | `usr/lib/os-release` is generated with exact Zog ID, `etc/os-release` symlinks to it; installed check verifies both. | Fresh successor must actually contain both (historical generation does not) |
| PID1/udev/journal/getty | systemd manifest declares PID1, journald, udevd, systemctl/journalctl/udevadm, getty and serial-getty units. Shadow 4.20.2 provides narrow non-PAM `usr/bin/login`. | Confirm all installed executables, serial/getty readiness and shutdown-failure recovery in actual boot |
| ext4/Kmod/core | e2fsprogs manifest requires `fsck.ext4`, `mkfs.ext4`, `e2fsck`. Kmod source test builds `kmod`; the manifest is corrected to require **`usr/bin/kmod`**, not merely libkmod headers. | Verify `usr/bin/bash`, `usr/sbin/agetty`, `usr/bin/findmnt` from inherited parent; audit kmod binary in native output |
| Fail-closed mounts | systemd-final installs empty mode-0000 `/state` and `/applications`. Staging durability and installed check preserve restrictive modes. | Re-open successor rootfs inventory to prove root:root owner, emptiness, mode and separate writable mounts |
| Foreign AL2023 bundle | Rejected first boot reached exact HOST-A read-only ext4 and initrd switch-root under AL2023 `6.18.44-99.149.amzn2023.x86_64`. Machine contract records historical kernel/initramfs/modules/config SHA-256 and dracut version. | Independently reverify retained bytes, matching module release, root=PARTUUID, NVMe/virtio/ext4 and the next switch-root outcome |
| Resident B | Systemd service and network paths included in source manifests; Python ssl/sqlite/CA, DBus, iproute2, host-install, host-discover and controllers still require the actual selected-generation inventory and protected admission. | **DEFERRED**; source recipe presence is not installed byte evidence |

Full requirement/obligation ledger: `project/host/boot-a-source-prerequisite-audit.json`. The read-only `tools/verify_boot_a_source_prerequisites.py` audits actual package manifests, selected EFI/SBAT configuration, OS-tree install, restrictive mounts, foreign provenance binding, and deliberate lack of an accepted successor ID. Adversarial tests reject missing kmod/EFI/os-release, modified source checks, fake generation IDs, false native acceptance and widened mountpoint permissions.

## Authorization boundary

Boot A remains certificate-independent. The exact foreign kernel/initramfs/modules may be reused only after ordinary protected byte/provenance verification. The accepted old generation is **not** a new boot target. Required next sequence remains: image-build Work publishes a distinct successor with source-corrected OS identity → image-build source/installed provenance is independently reopened → host-install Regular binds the new immutable artifact into an explicitly new five-partition plan → host-install/host-deploy Work performs disposable native Boot A. No Work execution or manual generation ID is part of this source PR.

# Native host package completion

`project/bootstrap/host-boot-packages.py` builds additions on an accepted systemd
core generation. It does not mutate that generation or activate host services.

- util-linux 2.42.2: the existing additive host stage remains nologin-only and
  preserves the accepted native util-linux output. Work preflight proved util-linux
  login requires PAM headers, conversation support and runtime policy that are absent
  from the retained root, so Boot A does not broaden into a PAM stack.
- Shadow 4.20.2: a late-reviewed login-only stage uses the exact unchanged October
  catalogue source pin and configures `--without-libpam`. It publishes only
  `/usr/bin/login`; the broader Shadow account-management program/policy set remains
  deferred to Resident B. The late-stage pin policy permits this only when URL+SHA256
  exactly equal the original monthly catalogue source.
- systemd final additionally materializes empty `/state` and `/applications`,
  both mode 0000, as Zog resident-HOST integration output while it is already being
  rebuilt for systemd-boot. These underlying mountpoints contain no installation
  identity or writable state; host-install later mounts installation-specific
  partitions over them. The generic application-runtime `/applications` scaffold
  remains a separate contract and is not changed.
- D-Bus 1.16.2: the reference daemon is the selected system-bus provider, with
  libsystemd integration and system service files. No X11, security-module or
  documentation generator dependencies. Meson default available tests run;
  GLib-dependent modular tests are unavailable in this profile. A private session
  bus round trip is required after installation. This is not live system-bus acceptance.
- iproute2 7.1.0: native tools with BPF disabled and the dependencies available in
  the exact base. Optional Berkeley DB/libmnl functionality is not claimed. Version
  probes run; upstream tests that mutate network namespaces/routes require a separate
  privileged disposable-host test and are not run by this build.
- libseccomp 2.6.0: shared library, full default `make check`, and an installed C
  probe that loads a filter and verifies the selected syscall returns EPERM.
- e2fsprogs 1.47.4: shared libraries, ext4 tools, full `make check`, then creation
  and read-only checking of a disposable regular-file filesystem. Existing
  util-linux libblkid/libuuid/fsck remain the providers; no block device is touched.
  LFS reports possible environment-sensitive failures; none are waived here.

For Boot A source selection, systemd final is now required to build EFI support and
systemd-boot and to publish exact `getty@.service`, `serial-getty@.service` and
`systemd-bootx64.efi` outputs. The targeted build plan
`project/bootstrap/boot-a-targeted.py` selects systemd-final plus the non-PAM
Shadow login provider. `resident_boot_targeted` then overlays only those verified
runtime outputs onto the exact retained parent, freezes all collisions/additions,
permits no implicit removals, requires installed verification, and preserves the
parent's historical provenance gap in the canonical generation graph. The host bootstrap profile is a
`boot-a-source-candidate`: Shadow, box-control and root-control are explicitly
Resident-B deferred and do not block the first UEFI→PID1 experiment. Exact native
generation, EFI bytes and foreign Amazon Linux kernel/initramfs/modules evidence are
still required before host-install may bind a generation.

The exact release archives and inspected licensing evidence are SHA256-pinned.
No upstream source patch is applied. License status is declared, not release-reviewed.
The source archives and original notices must remain available for later audit.

The next stage rebuilds systemd with libseccomp enabled and verifies `+SECCOMP`;
installing libseccomp alone does not enable systemd syscall filtering. Coordinated
`zog.*` runtime packaging follows separately from this external-source batch.
Host-install owns account materialization (including messagebus), service enablement,
machine identity, kernel/initramfs and disk/mount/network composition.

References: LFS 13.1-systemd chapter 8 package pages for D-Bus, IPRoute2 and
E2fsprogs; BLFS libseccomp 2.6.0; exact release build definitions and notices.

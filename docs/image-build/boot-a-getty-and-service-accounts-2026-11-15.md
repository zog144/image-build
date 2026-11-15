# Boot A serial/getty and core service account follow-up (2026-11-15)

## Native observation

The disposable boot reached resident systemd and journald, but serial getty failed because
the unit referenced `/usr/bin/agetty` while the installed util-linux binary is
`/usr/sbin/agetty`. The journal access socket reported missing
`systemd-journal` group and the system D-Bus service reported missing
`messagebus` user.

## image-build source correction

- Retain util-linux native installation with `--sbindir=/usr/sbin`; require
  `usr/sbin/agetty` in that package's native output.
- Configure the existing systemd 261.2 stage with
  `-Dagetty-path=/usr/sbin/agetty` (it otherwise derives `/usr/bin/agetty`
  with `-Dsplit-bin=false`). Require both generated getty templates to use
  the actual binary, with no post-install unit rewriting or compatibility alias.
- Require the upstream systemd `usr/lib/sysusers.d/systemd-journal.conf`
  output declaring `systemd-journal` and upstream D-Bus
  `usr/lib/sysusers.d/dbus.conf` declaring `messagebus`.
  Package staging checks fail if these definitions are absent.

## Required host-install Regular integration (not performed here)

The immutable HOST root is read-only at first boot. Merely shipping sysusers
fragments does **not** create `/etc/group` or `/etc/passwd` entries early
enough for journald's access socket and the system bus. The booted image must
already carry the corresponding named accounts/group, produced from the
selected systemd and D-Bus vendor sysusers definitions during **offline,
prepublication image composition** (for example via an isolated staged-root
`systemd-sysusers --root=<staged-root>` procedure). This operation must
never mutate the compiler Host's account database.

Reconcile with existing root/group entries and the host-install fixed Zog
service-account map. Do not change `host-discover`/`box-control` IDs,
invent numerical IDs for `messagebus` or `systemd-journal`, or reinstate
the rejected compiler owner/worker users. Verify that the final image's
`/etc/passwd` resolves `messagebus` and `/etc/group` resolves
`systemd-journal` before allowing it into the disposable installation.
If local sysusers configuration introduces additional required service
identities, resolve them from the exact selected vendor fragments, not a
separate default-user scheme.

Use source assertions and an actual staged-root inspection to check:
`getty@.service` and `serial-getty@.service` both target an executable
`/usr/sbin/agetty`; `getent`/database readers resolve the named identities
inside the final root; journald access socket and D-Bus can start.
Preserve the original accepted Boot A generation unchanged. Publish a
distinct corrected successor only after native package and generation
verification. Run the actual serial getty, journal sockets, D-Bus,
reboot and shutdown tests in the Work connection.

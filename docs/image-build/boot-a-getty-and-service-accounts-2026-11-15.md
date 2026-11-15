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

## host-install source and image-build producer integration (reviewed, source-only)

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

## Implemented producer invocation and recovery

`resident_boot_targeted.run` and its CLI now require both
`--resident-accounts-source /ABSOLUTE/PATH/TO/host-install/src/zog/host_install/resident_accounts.py`
and `--sysusers-executable /usr/bin/systemd-sysusers`. The former is the **exact
reviewed PR #43** module: the producer recomputes its original Git blob identity
`de9a161913959780a3097266d8936e0f7a1391b7` before *each* execution.
The host-install source commit is fixed to
`4fcccb441fec851530c412f619bc02699b8a87b1`. The latter must be the
root-owned OS-provided systemd-sysusers program; its path and SHA256 are
frozen in the producer's intent, along with the module source binding.
Neither input is an instruction to change the running Host.

The targeted overlay plan still freezes only the original package changes;
the distinct `resident-accounts-prepared.json` binds the exact pre-account
rootfs inventory and known base-account policy. The reviewed source is invoked
with `--inspect`, `--materialize` and `--verify` against **only** the
unpublished staged root. After successful verification, the producer
records `resident-accounts-result.json`, including the final account-aware
output inventory. The `composition.json` marker is now schema 2 and binds the
full final output inventory and the separate materialization receipt's SHA256.
The account source/receipt is also included in canonical Build Record
composition materials and immutable image owner inputs.

If both `etc/passwd` and `etc/group` are missing, the reviewed
`zog-resident-minimal-root-account-base-v1` contract first creates only the
standard root database rows in the **unpublished** root. Partial existing
account databases are refused. Existing root and Zog account rows are
preserved by the host-install materializer. No compiler users or alternate
execution identity are created. Sysusers' mode-0000 shadow/gshadow files are
normalized to 0400 (root-only read permission after immutable image publication)
so the unprivileged owner can hash the staged root, while the upstream
temporary `.pwd.lock` and `passwd-`/`group-` account backup files are
discarded from the unpublished stage only, never from the active Host.

An interrupted operation without the durable account preparation refuses
reuse; with preparation it can resume materialization and reverify the exact
restricted account-only delta. Once the result receipt exists, retries
reopen and verify it without inventing new UIDs or silently rewriting the
rootfs. Before installed verification, archive creation and publication,
the recorded account materialization is verified again.

**Source CI:** `43770302726` PASS on Python 3.12 and 3.13, executing the
actual reviewed host-install module with native systemd-sysusers against
disposable unpublished rootfs fixtures. This is neither native package
compilation nor a disposable EC2 boot acceptance. Work must compile/publish
a fresh successor, retain `273de2a0...` unchanged, and test its serial
console, journal sockets, D-Bus, read-only HOST-A and reboot/shutdown.

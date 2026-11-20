# Boot A producer successor — inherited-peer v2 source and native admission hold

**Source date:** 2026-11-20  
**Target:** image-build issue #22, PR #25; box-control issue #19 / PR #21;
root-control issue #48 / PR #54; host-install PR #43.

## Outcome and retained source

This source **retains** the exact PR #25 corrected resident Boot A producer,
account-aware final inventory and recovery scheme. The selected predecessor
is image-build commit
`cb73951000a3e7774ab798f58240c2a8f24d82bb`. The checked
`project/host/boot-a-inherited-peer-v2-source-selection.json` pins
**eleven exact Git blobs** from PR #25: the original
`resident_boot_targeted.py`, `resident_boot_accounts.py`, util-linux,
systemd and D-Bus build/manifest outputs, and the corresponding actual
getty, account, inventory and recovery regression tests. The source-byte
verifier refuses accidental changes to those blobs.

The original installer/source contract remains host-install PR #43, exact
revision `4fcccb441fec851530c412f619bc02699b8a87b1`, installed
`zog.host_install.resident_accounts` original source blob
`de9a161913959780a3097266d8936e0f7a1391b7`. The real OS-managed
`systemd-sysusers` executable must still materialize `systemd-journal`
and `messagebus` only in the unpublished staged root **after composition
and before final installed inventory and generation publication**. The
corrected `-Dagetty-path=/usr/sbin/agetty` and the actual getty unit
checks are unchanged. PR #25's separate preparation and result receipts,
final account-inclusive inventory, interrupted-operation recovery and
historical parent validation remain unchanged.

Historical failed/precompile R4/R5 requests, earlier unknown execution
records, accepted predecessor generations and exact archive/manifest
receipts are *evidence*, never silently retried, rewritten or re-identified
as inherited-peer v2. A successor must publish a **distinct immutable
generation**, never patch an already sealed image.

## New producer execution contract

The selected new box-control v2 source is PR #21 commit
`ad61fa6a4e9c3176149720868cb008e0512dbec9`.
The source-selection document pins all **52** reviewed runtime source
files and their Git blob IDs. Both packaged `*.py` and native source
members are compared byte-by-byte to their pins.

The producer now:
- Requires deployed `controller.json` to contain exactly
  `execution_identity: "inherit"`; extra `execution_user_id`,
  `execution_group_id`, `User` or `Group` selectors are rejected.
  The runtime adapter's selected wire contract must equal
  `zog-build-inherited-peer-v2`.
- Refuses an effective-root user or group before an attempted registration
  or controller operation. Root-control must **independently** derive the
  actual execution peer from the AF_UNIX socket's kernel credential
  evidence; this local guard is not child credential attestation.
- Saves `schema: 2`, `execution_contract:
  "zog-build-inherited-peer-v2"` in *new* package resources,
  registration-pending records, command checkpoints and checkpoint bindings.
  Original request IDs, input manifests, command arguments, read-only-root
  / no-network controls, resource limits and cgroup arguments are
  retained unchanged.
- Rejects a schema-1 or old identity-bearing command, resource or
  registration marker **before creating even a lock file**, then rechecks
  beneath the operation lock. Does not invent/translate a numerical
  execution UID/GID or turn a historical checkpoint into a fresh operation.
- Requires new box-control registration/job responses to carry the exact
  inherited-peer v2 marker. Cleanup/release also refuses old resources and
  requires the non-root caller, preventing an old operation from being
  activated through the release/recovery lane.

The source tests exercise new v2 command/registration identities, lack of
caller identity selectors, preserved read-only/network isolation, old
registration/checkpoint no replay, root caller rejection and unrelated
Boot A source behavior.

## Exact source and installed-byte verification

`tools/verify_boot_a_inherited_source_tuple.py` reads the source pin and
reopens the **exact clean Git commits**, verifies every original selected
source member (byte-identical Git blobs, file modes), retains the
PR25 source ancestry/eleven blobs and optionally compares the actual
installed module trees to those same hashes. Its source-only test uses
distinct checkout directories as disposable installed-byte fixtures; it
does not claim those fixtures are original Host installation evidence.

**Current root-control is explicitly not a suitable v2 controller.**
The inspected latest combined source root-control PR #54 is commit
`119c50c11a73663a446ad07551fa662936856913`, which retains
systemd 252 literal-argv fixes but still omits authenticated non-root
`SO_PEERCRED` identity from its worker/build dispatch. It can run a
finite compiler under systemd's default/root credentials. Its **26**
selected source files are pinned only as a **rejected historical candidate**,
not an executable admission pin. The source verifier rejects its use for
native execution even if all those bytes match.

**Native first-Fonts and Boot A execution remains HOLD** until
root-control Regular delivers issue #48 in the same issuer/Task C capable
controller source, including systemd 252 dollar escaping from PR #54.
The root successor must:
1. Bind build RPC v2 envelope (all eight lifecycle operations) to
   kernel-authenticated accepted AF_UNIX PID/UID/GID, with no root peer.
2. Reject selected User/Group/UID/GID fields and never use root-control's
   own effective UID/GID as the compiler identity.
3. Verify project access and process continuity and derive any transient
   systemd `User=`/`Group=` fields server-side from the peer, with
   no new compiler user accounts.
4. Make old root-control operation records inspection-only, not
   replayable by register/prepare/start/recovery/cleanup, and test actual
   EUID/EGID, PID, cgroup and readonly/network controls.
5. Provide its **exact immutable commit**, source file blobs, installed
   RECORD/module-byte attestation and durable v2 native test evidence.

Once that revision is reviewed, update the source selection to replace the
rejected root-control predecessor with the **new root v2 commit** and rerun
the complete image-build cross-program tests. Do not weaken the verifier
with an operator override to enable a v1 root daemon.

## CI / Work completion boundaries

The new source workflow checks the full PR25 account/getty and
`resident_boot_targeted` publication/recovery tests and current box
v2 adapter on Python 3.12 and 3.13. It opens the source and installed-byte
fixtures by exact SHA and verifies that the pre-v2 root cannot gain native
admission. These source tests do not establish native child credentials.

**Image-build Work may begin only after source and controller review:**

- Authenticate the exact producer commit, box-control v2 revision,
  reviewed root-control #48 successor and host-install #43 revision.
  Verify all actual installed files and signed installation/Build Record
  receipts in the selected environments, not merely GitHub CI fixtures.
- Select a nonroot controller caller with access to the selected Project.
  Verify root-control's actual accepted `SO_PEERCRED`, systemd 252
  ExecStart dollar-literal handling, inherited child EUID/EGID,
  cgroup and project access in a **distinct disposable controller job**.
- Preserve all pre-v2 operations and original parent generation
  `45a81ec3…`/original accepted Boot A generation `273de2a0…`
  unchanged. Use a **new targeted operation ID** and resume only under
  the new compatible v2 contract after native controller attestation.
- Run selected `systemd-final` and `shadow-login` as needed, compose
  PR25 outputs in a **fresh unpublished root**, invoke host-install #43
  offline accounts and verify resulting NSS/shadow files before the
  canonical final frozen inventory, archive digest and immutable output
  publication. Maintain all original package source, pins and recovery
  records. Do not publish over an existing generation.
- Test serial `/usr/sbin/agetty` console, journald access socket/group,
  D-Bus messagebus, readonly HOST-A, reboot and clean shutdown.

The former uncertain R5 controller operation
`0111471e2132a31f052621e0fbab31f6` remains an immutable prior
record; no direct-SSM or direct-systemd bypass is acceptable.

**Source status:** image-build v2 producer hardening and PR25 preservation
source-tested. **Native v2 controller agreement:** NOT ACCEPTED (root-control
#48 pending). **New Boot A generation:** NOT BUILT/PUBLISHED. Therefore
image-build issue #22 must remain open until the root v2 source is integrated,
reviewed and its installed-byte/child credential acceptance completed.

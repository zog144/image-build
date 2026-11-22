# Boot A producer successor — inherited-peer v2 source and native admission hold

**Source date:** 2026-11-20; **0:0 compatibility correction:** 2026-11-22  
**Target:** image-build issue #22, PR #25; box-control issue #19 / PR #21;
root-control issue #48 / PR #55 (including PR #54 fixes); host-install PR #43.

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
- Accepts the existing process's exact `0:0` effective UID/GID pair
  or a positive UID/GID pair, matching root-control PR #55. Rejects
  `0:positive`, `positive:0`, invalid values or out-of-range values
  **before** attempting registration or controller mutation. The local
  process-credential check is merely a shape check, **not** proof of the
  socket peer or child. Root-control must still obtain authenticated
  `SO_PEERCRED` from the accepted AF_UNIX socket and bind the child to
  that exact kernel-supplied pair.
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
  requires a valid same-process credential pair, including exact `0:0`,
  preventing an old operation from being activated through the
  release/recovery lane.

The source tests exercise new v2 command/registration identities, lack of
caller identity selectors, preserved read-only/network isolation, old
registration/checkpoint no replay, `0:0` acceptance, mixed-zero
rejection, unchanged v2 wire mismatch rejection, exact root-control
socket-kernel credential checks, and unrelated Boot A source behavior.

## Exact source and installed-byte verification

`tools/verify_boot_a_inherited_source_tuple.py` reads the source pin and
reopens the **exact clean Git commits**, verifies every original selected
source member (byte-identical Git blobs, file modes), retains the
PR25 source ancestry/eleven blobs and optionally compares the actual
installed module trees to those same hashes. Its source-only test uses
distinct checkout directories as disposable installed-byte fixtures; it
does not claim those fixtures are original Host installation evidence.

**Current root-control v2 source is now selected.** Draft
[root-control PR #55](https://github.com/zog144/root-control/pull/55)
commit `a672f007b33f83bf70970e3a571fd443366bd93f` contains the
issuer/Task C functionality and systemd 252 literal-dollar finite-argv fix
inherited from PR #54, plus authenticated `0:0` or positive peer
execution from issue #48. The source-pinned revision changes the
`build.py` and `journal_barrier.py` blobs to accept the exact
kernel-authenticated root pair while retaining the journal stop-hook
protection. All **26** selected root-control runtime source files are
pinned and checked byte-for-byte by the source/installed-module verifier.
The older PR #54 commit
`119c50c11a73663a446ad07551fa662936856913` remains in the
source-selection evidence solely as a **rejected predecessor**, never
selected as the executable root daemon for v2 compilation.

The new server implementation accepts the exact box-control v2
`build_contract` top-level envelope, captures `SO_PEERCRED` on the
actual accepted Unix socket before dispatch, permits the actual `0:0`
caller while rejecting mixed-zero/invalid or forged peers, and injects
the private server-only `_peer` into the build lifecycle. It binds new
schema-2 records to that exact kernel-authenticated pair, makes historical records
inspection-only, checks existing Project/workspace access, and derives any
transient systemd User/Group settings from that authenticated principal.
Live observation verifies the actual kernel child EUID/EGID, PID1's
Unit User/Group and cgroup. No extra compiler account is created and no
caller-chosen numeric UID/GID is accepted. The exact root-control PR55
source CI passed 427 tests with 17 skipped per Python version, plus
one dedicated root-only `0:0` test per Python version; the build is
still source-only. The producer's exact source integration test exercises
the server-only `_peer` register signature, 0:0 policy and
`SO_PEERCRED` source path.

**Native first-Fonts and Boot A execution remains HOLD**, but the reason
is now **native deployment and acceptance**, not an absent source
implementation. Root-control Work + box-control Work must prove:
1. The actual installed box-control caller uses a kernel-authenticated
   `0:0` pair (the approved existing root caller) or a valid positive
   UID/GID pair, and is permitted on root-control's socket. Mixed-zero
   or requester-selected identity remains forbidden.
2. The exact root-control PR55, box-control PR21 and this image-build
   successor source and installed bytes are attested in their actual
   environments (not merely CI checkout source fixtures).
3. A **new disposable** bounded finite job traverses the normal
   box-control/root-control path on real systemd 252, checking source
   argv/literal dollar characters, child EUID/EGID, systemd properties,
   network/read-only-root/cgroup and matching InvocationID at both live
   and terminal observation through
   `root-control/acceptance/build_peer_bound_live.py`.
4. Existing historical operation state is never rewritten, selected as
   a v2 checkpoint or submitted for replay. The previous uncertain R5
   request remains unknown until explicitly reconciled; no direct SSM
   or systemd bypass is acceptable.

The command-line source verifier deliberately fails
`--native-admission` until **the separate genuine installed-root and
live child-evidence receipts** are accepted. Exact matching source blobs
are necessary but insufficient. Review/integration of source may proceed
without authorizing native compilation.

## CI / Work completion boundaries

The new source workflow checks the full PR25 account/getty and
`resident_boot_targeted` publication/recovery tests and current box
v2 + root-control PR55 server-only peer injection on Python 3.12 and
3.13. It opens the selected source and installed-byte fixtures by
exact SHA and verifies that source-only CI cannot claim native execution
admission. These tests do not establish native child credentials.

**Image-build Work may begin only after source and controller review:**

- Authenticate the exact producer commit, box-control v2 revision,
  reviewed root-control PR55 successor and host-install #43 revision.
  Verify all actual installed files and signed installation/Build Record
  receipts in the selected environments, not merely GitHub CI fixtures.
- Use the selected existing root `0:0` caller (or a separately
  verified positive UID/GID pair) with access to the selected Project.
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

**Source status:** producer v2 and PR25 preservation source-reviewed
candidate, selecting the exact box-control PR21 and root-control PR55
v2 implementations. **Native controller acceptance:** NOT YET COMPLETED
(actual installed package bytes, authenticated `0:0` socket peer,
real systemd252 child EUID/EGID 0/0, InvocationID and terminal receipt pending). **New Boot A generation:** NOT
BUILT/PUBLISHED. Image-build issue #22 remains open until the reviewed
producer successor and matching installed controller triple are
accepted and native Boot A publication succeeds.

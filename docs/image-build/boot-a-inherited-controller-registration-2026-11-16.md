# Boot A source integration: inherited-identity finite-build registration (2026-11-16)

## Failure retained — not a native compile failure

The Work attempt at image-build producer source `92cd7311de484f82b55b9c1270425a22d4ecafdf`
failed during build-root registration with
`BuildBackend.register() got an unexpected keyword argument 'execution_user_id'`.
No native package compilation command was submitted. This failed operation,
its controller checkpoints and earlier setup failures remain historical evidence.
**Do not edit the old `intent.json`, `controller-resources.json`, registration,
request, package attempt, recovery or approval records to make them pass under
a changed execution protocol.** Start a new distinct targeted producer operation
after reviewed deployment selection.

The mismatch was concrete: old image-build PR #25's
`box_control_adapter.py` carried `execution_user_id` and
`execution_group_id` in its `register_build_root` call and finite build request.
The identity-free source already existed in image-build PR #23.

## Source correction selected on PR #25

Image-build PR #25 now incorporates the **exact identity-free
`box_control_adapter.py` and `configuration.py` from PR #23** into the
existing account-aware Boot A producer. The separate remote-operations
diagnostic execution path likewise no longer forwards UID/GID selectors.
`tests/test_source_build.py` rejects the obsolete controller JSON fields.

In this protocol:
- `register_build_root` receives only `resource_id`,
  `prepared_root`, `source_directory`, `output_directory`,
  and `input_manifest_id`. No execution identity.
- Canonical build requests include resource/workspace identities, command,
  environment, working directory, timeouts, limits, read-only root and
  network prohibition. No `execution_user_id`, `execution_group_id`,
  `User` or `Group` overrides.
- Legacy `controller.json` with user/group selectors is rejected; do not
  silently drop its fields in an existing retained operation.
- A retained identity-bearing `controller-resources.json` is rejected
  for a new protocol rather than rewritten or resubmitted.

The actual service identity is a property of the **installed running
controllers/systemd environment**, not a request parameter. With the
system systemd manager, omission of `User=`/`Group=` ordinarily means
the transient systemd unit runs as root. Native acceptance must inspect
the root-control daemon and child process EUID/EGID and complete job
lifecycle; **source parity alone does not establish identity inheritance
for a non-root service**.

## Combined controller source selection

The original identity-free candidates are:
- image-build PR #23 `620378bdd8075daeb5eaad45eedea4af7db36423`;
- box-control PR #20 `fdafbfb3032847b73c77abd9d90d769e43fddf85`;
- root-control PR #49 `f3d05f50f86ca4d80f734458966976a553dbf8ea`.

For the **current combined issuer-capable resident controller source**, select
the superseding compatible pair rather than reverting related Certbot/Task C
functionality:
- box-control PR #21 `c886e7a90bb4ea74e771a6c5dcefaa2069539ec7`
  (identity-free canonical build protocol blob
  `a334aec4865eaad003f9e02b638b5260c352b8ab`);
- root-control PR #51 `d9dfd6c02a5a96750f1213bf663cdceab72f1efd`
  (identity-free BuildBackend source blob
  `33303c38d4cc8e13b742cac1510dc52c4544f2f9`).

These combined revisions retain issuer support, local Task C and
identity-free finite build. Use one reviewed pair; do not install PR #49
alone if that would remove required issuer functionality.

Boot A additionally requires host-install PR #43
`4fcccb441fec851530c412f619bc02699b8a87b1`, the materializer
source already pinned in PR #25's account-aware producer. Keep the exact
`--resident-accounts-source` and `--sysusers-executable` selection in
the new producer invocation.

## Source tests and native handoff

`tests/test_boot_a_finite_build_identity.py` tests a registration against
a strict receiver matching `BuildBackend.register`, checks the actual
companion root-control method signature and box-control canonical request,
rejects injected UID/GID fields and verifies a legacy identity-bearing
registration is untouched and not resubmitted. Focused GitHub source CI
checks out the exact combined controller revisions and runs these tests
alongside account-materialization/producer tests. No live Host is mutated.

**Work sequence:** install/activate and read back the exact combined
controller pair, deploy the corrected image-build source and an identity-free
`controller.json`, inspect the actual running service and wire protocol,
retain old failed attempts without modification, then submit a **new**
targeted Boot A operation ID. Verify registration and only then permit
the approved compile. After package completion, the existing account-aware
composition and canonical publication checks remain required; only a
distinct verified Boot A successor can be selected for Resident B.

This source work does **not** authorize a new compile, approve a
signing/issuer identity, mutate existing generations, change private
Host/accounts, or claim successful native boot.

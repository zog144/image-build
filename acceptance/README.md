# Generation provenance live acceptance

## Journal barrier and controller-loss extension

Use box-control `3f03e0fb3df673df3ea5c2bdfcfac0de493458ae` and install its reviewed
static helper following `JOURNAL-BARRIER.md`. Before freezing inputs, enable
`ROOT_CONTROL_JOURNAL_BARRIER=1` on a dedicated restartable
`provenance-root-control.service` running `python -m zog.root_control.daemon`, with
`ROOT_CONTROL_SOCKET` set to the test socket and automatic restart disabled.
The extension kills this exact test service; never use it on a shared host.

Run the source/patch phases below, replacing `publish` with
`barrier_provenance.py publish-recovered` (same arguments, expected exit 76).
It waits for the first library command to exit, kills the controller before
result collection, confirms unit absence and restarts the controller. After
`materials`, run `barrier_provenance.py inspect-recovered`. This checks the
recovered outcome, exact command/job/invocation, strict logs, barrier status and
owner exit-hook evidence after ordinary release. No RefUnit keeper is installed.

Initialize a second fresh project with the source/patch driver's `init`, then run
`barrier_provenance.py unknown`. The broker is absent through the first command's
exit. Require unknown outcome, null exit code, unconfirmed barrier and blocked
recovery. A repeated resume must preserve the frozen binding and job count.
Explicit cancellation releases resources while preserving unknown. No generation
is accepted. Log availability is independent of outcome evidence.

Capture both projects' evidence before terminating the disposable host. Trace
shows recovered outcomes and recovery uncertainty; `journal_barrier` and
`exit_evidence_source` remain box-control fields referenced by the same job ID.

## Base driver

`generation_provenance.py` is an opt-in driver for an **isolated disposable Linux
host** with systemd, journald, root-control and a separately configured box-control
execution user (UID/GID 21001). It does not provision or upgrade hosts. Never run
it in an existing compiler project. Source/runtime upload and host lifecycle need
operator authorization. Dependencies are the compatible image-build, build-record,
build-trace and box-control source trees plus dbus-next.

Provide a distribution bootstrap root containing a C compiler, static libc,
binutils, shell and coreutils. Remove set-id bits from this disposable seed as
required by box-control admission. This is explicitly host-seeded acceptance,
not self-hosting or a bootable-system acceptance. Run a dedicated root-control
daemon on its own socket; leave it running across driver exits. The generation
serializer deliberately rejects extended attributes, including automatically added
`security.selinux` labels. Use a disposable host/filesystem that creates unlabeled
files (SELinux disabled at boot on Amazon Linux); permissive mode still adds labels.
Do not strip attributes from frozen outputs to make a failed run pass. Preserve the
failed project and use a fresh project after fixing the environment.

Use one new absolute project path under the invoking root user's home. Every
phase must use the same `--root` and `--socket`. Run phases in order:

1. `init --seed /absolute/disposable-seed`: creates and commits a private local
   fixture catalogue, captures its exact monthly pin revision and source archives,
   and imports the distribution seed. Git must be installed.
2. `cancel`: submits a real job and cancels it through box-control, retaining the
   cancelled result and releasing resources.
3. `prepare`: starts a new retry with the original inputs and exits **75** after
   immutable provenance preparation, before command submission.
4. `publish`: changes the current catalogue/pin, resumes the saved pipeline,
   compiles/tests both packages and exits **76** immediately after durable canonical
   generation finalization, before owner generation publication.
5. `recover`: resumes the same pipeline, checks preparation/result identities and
   unchanged job count, executes the resulting static binary (42), and imports
   accepted package outputs for reuse.
6. `reuse`: creates a second generation containing the original library output,
   with no new execution jobs and no invented producer attempt.
7. `verify`: checks both canonical graphs and retained artifacts, inspects each
   export in a separate interpreter with only build-record available, checks
   paged trace membership and the real test journal, and rejects missing/corrupt
   recipe material in disposable copies.

Example invocation (repeat with the required phase):

```sh
python acceptance/generation_provenance.py init \
  --root /root/provenance-acceptance --socket /run/provenance-acceptance.sock \
  --seed /root/disposable-seed
```

Exit 75/76 are intentional process crashes, not passing normal exits. Do not
rerun a completed phase: preserve its evidence and use the next recovery phase.
Failures retain state for diagnosis; the driver never converts failures to success.
`evidence/result.json` exists only after all final assertions pass. The exports
remain explicitly incomplete where the producer declares bootstrap/runtime or
upstream provenance gaps. Cancellation is an execution fault, not a recipe edit.
There is no physical power-loss, reboot, release-readiness or UI claim.

Collect compact evidence and exact source revisions before deleting the disposable
host. Use host-deploy ownership checks for termination and verify disk deletion.
Keep pass reports in know-file, not this source directory.

## Source and patch material inspection (build-trace 0.7)

`source_patch_provenance.py` extends the same isolated-host driver. The bootstrap
seed additionally needs `patch`. Its generated original C sources and two original
patches live only in the disposable project. Real local Git commits identify the
source declarations; archive and patch SHA256 values are captured before dispatch.
No fixture archive or compiled output belongs in this repository.

Use this driver for all seven phases above, then run `changed` and `materials`.
Preparation also temporarily removes/corrupts the retained and staged patch bytes,
asserts that re-preparation blocks without new jobs, restores the exact saved bytes,
and confirms the same immutable binding before the intentional exit 75. Only this
explicitly disposable test state is damaged; accepted records are never rewritten.

The `changed` phase deliberately selects new source bytes and a new monthly Git
commit in a new pipeline, changes one patch's bytes and reverses the order of two
independent patches. The new binary must print 43; the earlier one prints 42.
`materials` checks one-row paging against canonical source/patch records, original
producer identity on reuse, changed upstream/archive/patch descriptors and positions,
unchanged historical export bytes, independent build-record inspection, verified
retained bytes and the new real test journal. `materials-result.json` records the provenance checks and the separate journal
assertion before enforcing the final gate. A false `passed` value remains a failed
run (nonzero exit); do not interpret a report file alone as acceptance. These extra phases are not automatically rerunnable.

Local fixture validation tests patch application and affected-file hashes. It does
not establish live acceptance. Host provisioning and security changes remain
separately authorized operations: on Amazon Linux the existing serializer needs
an unlabeled filesystem, so disabling SELinux at boot requires explicit approval.
Do not weaken the serializer or strip attributes from frozen material to bypass
that requirement. This driver itself does not change host security configuration.

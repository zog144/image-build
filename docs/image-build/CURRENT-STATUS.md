# Historical image-build status checkpoints (September 25 – October 1, 2026)

**Historical scope.** This page summarizes bounded development/test checkpoints
recorded during the first source-toolchain bootstrapping work. It is **not** an
up-to-date report of the active compiler host, the state of its job queue, deployed
services, acceptance of a new generation, or release readiness. Earlier raw
operator evidence and job-specific identifiers were retained separately in the
private historical records before this portable summary replaced the old
chronological log. They are not inputs to a public installation.

Consult the maintained [image-build technical manual](README.md),
[bootstrap pipeline](guide/bootstrap-pipeline.md),
[recovery and verification](guide/recovery-and-verification.md), and
[controller integration](CONTROLLER-INTEGRATION.md) for the contracts applicable
to a selected source revision. Check actual job and generation state using the
authenticated owner controller before performing any continuation.

## Recorded work and limits

| Historical phase | What was observed | What was **not** established |
| --- | --- | --- |
| Final Glibc | The final-stage suite and installed composition were reported accepted after separate test-environment and publication corrections | Compiler self-hosting and general workload support |
| Final arithmetic and Info dependencies | GMP, MPFR, MPC and Info support stages received source/parser, environment and output-manifest corrections | Acceptance of every subsequent Binutils/GCC stage |
| Binutils and compiler support | A Binutils phase was accepted after addressing licensing, output evidence and dependency issues | A passing full GCC test/installation/promotion chain |
| Gawk and Zstd recovery | Compiler dependency ordering and locale fixtures were corrected; jobs were prepared and selectively retried | General permission to restart uncertain jobs or substitute new source inputs |
| GCC compilation and tests | A GCC compilation completed; testing required a separate bounded stack-limit/test-environment retry. The corrected test worker used a 256 MiB stack limit and retained the original compilation and failed evidence | Production generation promotion or self-hosting based on compilation success alone |
| GCC hardening diagnostics | A later diagnostic run retained an unresolved set of 75 unexpected entries, without installing or promoting that result | A clean hardening verdict, completed live diagnostics, or release acceptance |
| Host-install artifact integration | Offline export/verification and fixture interfaces were prepared and tested to their stated scope | A bootable physical host or permission to erase a target disk |

These are distinct observations on different source, environment and job
revisions. A historical **passed** local test is not a live runtime acceptance;
an operation that was prepared, launched, or whose logs were retained is not
necessarily an accepted output. Never merge outcomes from different revisions
into an invented successful end-to-end run.

## Durable recovery constraints

- Jobs are durable operations. Recover the **same** frozen source pins, request
  identity, runtime/generation identity and selected environment; inspect owner
  ledger, journald results and failure evidence before considering any retry.
  A non-response or disconnected client is not proof that submission failed.
- Test retries must not overwrite the original pipeline's failed result, silently
  rebuild completed inputs, fabricate passing test observations, or convert
  unknown/failed evidence to passed. Separate test-only retries do not
  automatically install or publish.
- Unexpected tests, unresolved hardening diagnostics, incomplete patch/license
  provenance, source/output inventory differences, and missing runtime
  dependencies continue to block the relevant promotion. Diagnostic visibility
  is not an exception mechanism.
- Every generation publication requires exact source/content bindings, the
  reviewed output manifest and verified controller execution evidence.
  Host-install, station-access and downstream observation consumers have
  independent acceptance requirements.
- Do not infer a currently running build, pending cleanup, or a useful next job
  from this dated chronology. Inspect the present system through its authorized
  interfaces before changing host state.

## Current maintained reference

New rootfs and application software generation work belongs to the
[immutable artifacts and generations](guide/immutable-artifacts-and-generations.md)
and [publication recovery](publication-recovery.md) contracts. Monthly source
selection is documented in [monthly pins](MONTHLY-PINS.md). Cryptographic,
Python and graphical recipes have separate reviewed stages; no single dated
status report supersedes their individual tests, provenance or license checks.

This historical summary intentionally omits private host IDs, account details,
workspaces, source transfer locations, logs and private acceptance links. It
neither asserts that those records were public nor replaces the required
independently verified release evidence.

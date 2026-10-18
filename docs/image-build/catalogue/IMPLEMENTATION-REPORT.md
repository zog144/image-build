# Source foundation checkpoint — September 13, 2026

The interrupted source work was recovered and its test environment restored.
This is a **historical September 13, 2026 checkpoint**, not a description of the current runtime, production integration, or present build acceptance. The original, complete operational evidence was preserved in the private history before sanitization of this public-context synopsis. Later implementation may supersede the limitations below; consult the canonical [technical manual](../README.md) and source revision tests.

## Results

- Latest local suite after removing deprecated backends: **28 passed**.
- Remote Amazon Linux 2023 suite on the earlier intermediate source: **25 passed**.
- AWS authentication, independent EC2 provisioning, SSM readiness, generic job
  submission, status and verified evidence collection worked through host-deploy.
- The disposable, independently owned AWS test host was reported stopped at that checkpoint; its test disk was retained for controlled cleanup. The host identity and resource details are intentionally omitted from this portable history. No other project's host was changed.

## Corrected implementation error

The old extraction's Podman runner was carried forward, then Docker support was
added when Amazon Linux's repositories did not provide Podman. This was the
wrong architecture. The user clarified that image-build execution must use
systemd through box-control. Both backends and their execution jobs/tests have
been removed. A caller-side controller port now fails closed when no adapter is
supplied. No direct systemd fallback was substituted.

The remote experiments are diagnostic evidence only:

1. First job installed development packages, then failed because Podman was not
   available in the configured Amazon Linux repository.
2. Second job installed Docker and prerequisites, passed 25 tests, then failed
   during seed assembly on dangling RPM debug-index links. It did not establish
   container build acceptance. The unsubmitted third candidate was discarded.

The stopped disposable test host retains those experimental packages. They are
not dependencies of the corrected image-build implementation or test recipe.

## Actual integration blocker

At the recorded checkpoint, the then-reviewed controller integration validated published generations and controller mounts but lacked the required temporary build-root/network/deadline/exit-result operation. See BOX-CONTROL-BUILD-EXECUTION-REQUEST.md for the concrete request.
The existing checks are preserved. No fabricated manifest or unsupported API
was used to force execution.

## What is implemented

Literal package metadata, source verification/staging, dependency ordering,
per-package root/output assembly, output inventory/composition, generation
identity/publication, two-stage bootstrap orchestration, host preparation,
optional DNF4 source evidence, retained failure records, and the explicit
controller execution port with receipt validation.

## Not established

A working box-control build executor, real systemd build isolation, a complete
source-toolchain recipe set, full self-hosting, and compatibility with existing
box-control image readers. Tests of the execution port are simulated. The native
C example is only a recipe/compilation check.

Other deferred features: automatic build crash recovery/storage-fault latching,
recursive source-package conversion, DNF5 discovery, ownership/capability
metadata, reproducibility comparison, and security-network publication.
Credentials are excluded from source, job definitions and all deliverables.

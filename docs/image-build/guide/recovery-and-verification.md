# Recovery and verification

## Recovery uses frozen identities, not current defaults

A pipeline, selected generation, recipe snapshot and build job are different durable identities. An interrupted pipeline continues against the **original materialized recipes, pin digest, execution policy, selected base and controller checkpoints**. It does not use today's catalogue, branch, source mirror, current active generation or a replacement build job to "repair" unknown outcomes.

Box-control and root-control own finite command admission, privileged build-root registration and observation of systemd identities. Image-build owns package attempts, immutable source/output evidence, generation composition and canonical provenance. A lost controller reply is not proof that the command did not execute. After an uncertain build-root registration, read [registration progress and reconciliation](../registration-recovery.md) or [durable registration continuation](../registration-continuation.md); only an authoritative `ready` result permits reconciliation of the same resource. `importing` and `absent` are not authorization for a new registration call.

## Four publication recovery rules

The [immutable publication contract](../publication-recovery.md) distinguishes rootfs generations, recipe snapshots, application artifacts and application views. Their behavior depends on which frozen bytes remain reconstructible. Published content-addressed objects are authoritative, always verified before reuse, and never rewritten merely because a result acknowledgement was lost.

- **Rootfs generation:** exact valid staging is reused; partial staging is reconstructed from still-bound inputs; a valid conflicting manifest is an integrity fault.
- **Recipe snapshot:** unpublished candidates may be rematerialized from the exact frozen recipe request, revision and pin.
- **Application artifact:** a frozen candidate may contain the **only** exact installed runtime bytes; a corrupt candidate blocks rather than being regenerated from source metadata.
- **Application view:** an unpublished candidate can be recomposed from retained artifact identities and the frozen symlink plan.

Published objects are not reclaimed by any of these recovery paths. The separate [immutable reference inspection](../immutable-objects.md) is read-only and always reports `reclamation_authorized: false`; box-control's live/cleanup inputs and external owner protection sets must be reconciled before any future deletion authority exists.

## Executions, observations and evidence gaps

Execution success, installed-output verification, immutable generation publication, canonical build-record completeness and **selected observation snapshot** are separate facts. Build-record stores immutable canonical records, while image-build publishes and explicitly selects an observation snapshot for a generation. A snapshot is not inferred from "newest" timestamps or the mere presence of records. Retained-generation backfill adds observation evidence without rebuilding or modifying the generation.

The [integration observation producer](../integration-observations.md) exports facts about packages, sources, relationships, named verification executions and declared gaps. It inspects frozen inputs and the immutable generation, not a mutable checkout. Candidate verification evidence also covers failed, unpublished generations without presenting them as published rootfs identities. The v1/v2 verification observation contracts and execution-environment provenance are different schema versions; a v1 environment digest is legacy opaque evidence, not a fabricated v2 environment report.

A test returning zero does not imply full suite or production readiness. Report which tests ran, fixture/platform constraints, skips and missing evidence. Build-trace can navigate observations; integrate-observe compares declared facts without inferring causation, regression, severity, or policy.

## Acceptance ladder

| Evidence | What it supports | What it does not support |
|---|---|---|
| Source/pin and recipe CI | Well-formed metadata, selected source closure | Compilation or target runtime execution |
| Finite compiler job | Command status for one recorded invocation | Self-hosted compiler and complete upstream testing |
| Output manifest and installed probes | Specific package/output integrity and behavior | Host boot, service operation or optional device coverage |
| Published immutable generation | Exact producer-owned rootfs identity | Active host adoption, boot or release acceptance |
| Canonical generation/observation records | Recorded provenance and named test/coverage facts | Unobserved completeness or automatically accepted release policy |
| host-deploy/host-install live acceptance | Specifically executed host/disk/service observations | Any deferred platform, crash/power-loss or broader certification |

The historical [validation log](../VALIDATION.md) and [current-status chronology](../CURRENT-STATUS.md) contain dated results, with some explicit failures and later follow-ups. They are retained evidence, **not** live status dashboards. An earlier failed glibc fixture does not prove all later work is failed; an earlier passing static test does not prove full current boot acceptance.

## Recovery operator procedure

1. Identify exact source revision, owner operation, selected pin/snapshot, generation, controller request/job and provenance records.
2. Read stored status and read-only recovery inspection before mutating. Preserve journals, command invocation IDs, frozen candidates and original result receipts.
3. Separate pending command, unknown service start, corrupt input, failed verification, incomplete publication and pending cleanup. Do not treat them as the same retry case.
4. Restore **only the bound material** if safe; follow the owning program's reconcile/continuation API with its original identity.
5. For terminal failure, authorize a genuinely new attempt with explicit predecessor/retry evidence rather than replacing immutable failure history.
6. Before a release or production cutover, obtain separately owned acceptance from release-build and the relevant host controller/operator.

### Preserved references

- [Controller integration, seed checks and interruption handling](../CONTROLLER-INTEGRATION.md)
- [Publication and exact recovery](../publication-recovery.md)
- [Read-only immutable reference protection](../immutable-objects.md)
- [Registration recovery](../registration-recovery.md) and [continuation](../registration-continuation.md)
- [Canonical integration observations](../integration-observations.md)
- [Snapshot publication and selection](../observation-snapshot-publication.md)
- [Historical verification reports](../VALIDATION.md) and [dated implementation chronology](../CURRENT-STATUS.md)

This guidance does not retry a blocked operation or imply a production host was changed.

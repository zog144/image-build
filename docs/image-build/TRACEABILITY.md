# image-build documentation traceability

**Migration stage:** chapter navigation added; no original source is deleted or reclassified as deployed behavior.

| Existing document | Canonical chapter(s) | Treatment |
|---|---|---|
| [BOOTSTRAP-STAGES.md](BOOTSTRAP-STAGES.md) | Bootstrap pipeline | Detailed original retained; review unique requirements and status |
| [CONTROLLER-INTEGRATION.md](CONTROLLER-INTEGRATION.md) | Overview and architecture | Detailed original retained; review unique requirements and status |
| [CURRENT-STATUS.md](CURRENT-STATUS.md) | Overview and architecture; Recovery and verification | Detailed original retained; review unique requirements and status |
| [LICENSING.md](LICENSING.md) | Sources and monthly pins | Detailed original retained; review unique requirements and status |
| [MONTHLY-PINS.md](MONTHLY-PINS.md) | Sources and monthly pins | Detailed original retained; review unique requirements and status |
| [NATIVE-BUILD-ENVIRONMENT.md](NATIVE-BUILD-ENVIRONMENT.md) | Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [VALIDATION.md](VALIDATION.md) | Recovery and verification | Detailed original retained; review unique requirements and status |
| [application-software-artifacts.md](application-software-artifacts.md) | Immutable artifacts and generations | Detailed original retained; review unique requirements and status |
| [archive-mirror-sources.md](archive-mirror-sources.md) | Sources and monthly pins | Detailed original retained; review unique requirements and status |
| [boot-build-tools.md](boot-build-tools.md) | Bootstrap pipeline | Detailed original retained; review unique requirements and status |
| [build-record-integration.md](build-record-integration.md) | Provenance and observation publication | Detailed original retained; review unique requirements and status |
| [build-trace-contract.md](build-trace-contract.md) | Provenance and observation publication | Detailed original retained; review unique requirements and status |
| [catalogue/BOX-CONTROL-BUILD-EXECUTION-REQUEST.md](catalogue/BOX-CONTROL-BUILD-EXECUTION-REQUEST.md) | Reference and schemas | Detailed original retained; review unique requirements and status |
| [catalogue/HOST-DEPLOY-HANDOFF.md](catalogue/HOST-DEPLOY-HANDOFF.md) | Reference and schemas | Detailed original retained; review unique requirements and status |
| [catalogue/IMAGE-BUILD-ARCHITECTURE.md](catalogue/IMAGE-BUILD-ARCHITECTURE.md) | Overview and architecture; Reference and schemas | Detailed original retained; review unique requirements and status |
| [catalogue/IMPLEMENTATION-REPORT.md](catalogue/IMPLEMENTATION-REPORT.md) | Reference and schemas | Detailed original retained; review unique requirements and status |
| [catalogue/SEED-GENERATION.md](catalogue/SEED-GENERATION.md) | Reference and schemas | Detailed original retained; review unique requirements and status |
| [catalogue/TOOLCHAIN-CATALOGUE.md](catalogue/TOOLCHAIN-CATALOGUE.md) | Toolchains and language runtimes; Reference and schemas | Detailed original retained; review unique requirements and status |
| [cryptography-bootstrap.md](cryptography-bootstrap.md) | Bootstrap pipeline; Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [graphics-foundation.md](graphics-foundation.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [graphics-recipe-status.md](graphics-recipe-status.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [graphics-rpm-review.md](graphics-rpm-review.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [host-boot-packages.md](host-boot-packages.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [host-enrollment-bootstrap.md](host-enrollment-bootstrap.md) | Bootstrap pipeline; Remote execution and gateway | Detailed original retained; review unique requirements and status |
| [host-readiness.md](host-readiness.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [http-signatures-bootstrap.md](http-signatures-bootstrap.md) | Bootstrap pipeline; Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [immutable-objects.md](immutable-objects.md) | Immutable artifacts and generations | Detailed original retained; review unique requirements and status |
| [integration-observations.md](integration-observations.md) | Provenance and observation publication | Detailed original retained; review unique requirements and status |
| [maturin-bootstrap.md](maturin-bootstrap.md) | Bootstrap pipeline; Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [observation-snapshot-publication.md](observation-snapshot-publication.md) | Provenance and observation publication | Detailed original retained; review unique requirements and status |
| [payload-paths.md](payload-paths.md) | Immutable artifacts and generations | Detailed original retained; review unique requirements and status |
| [publication-recovery.md](publication-recovery.md) | Immutable artifacts and generations; Recovery and verification | Detailed original retained; review unique requirements and status |
| [python-enrollment.md](python-enrollment.md) | Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [python-libraries.md](python-libraries.md) | Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [python-runtime.md](python-runtime.md) | Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [registration-continuation.md](registration-continuation.md) | Remote execution and gateway | Detailed original retained; review unique requirements and status |
| [registration-recovery.md](registration-recovery.md) | Remote execution and gateway; Recovery and verification | Detailed original retained; review unique requirements and status |
| [remote-operations.md](remote-operations.md) | Remote execution and gateway | Detailed original retained; review unique requirements and status |
| [retained-compiler.md](retained-compiler.md) | Bootstrap pipeline | Detailed original retained; review unique requirements and status |
| [runtime-facilities.md](runtime-facilities.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [rust-bootstrap.md](rust-bootstrap.md) | Bootstrap pipeline; Toolchains and language runtimes | Detailed original retained; review unique requirements and status |
| [systemd-core.md](systemd-core.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [systemd-native.md](systemd-native.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |
| [systemd-prerequisites.md](systemd-prerequisites.md) | Recipes, graphics and runtime facilities | Detailed original retained; review unique requirements and status |

**Coverage:** 44/44 existing Markdown documents assigned. Machine-readable schemas/examples remain at their existing paths. A later consolidation must validate internal links, exact contract versions, historical claims and tests before removing duplicates.

## Editorial consolidation progress — 2026-10-12

This pass replaces the listed canonical chapter placeholders with substantive summaries of current source contracts. The original reference documents remain at their stable paths for exact schemas, historical status and implementation-specific details. A synthesized chapter is not yet a deletion authorization for any referenced file.

| Synthesized reader chapter | Primary preserved evidence | Status |
|---|---|---|
| [Sources and monthly pins](guide/sources-and-monthly-pins.md) | MONTHLY-PINS.md · archive-mirror-sources.md · LICENSING.md | Reader synthesis committed; original detail preserved |
| [Immutable artifacts and generations](guide/immutable-artifacts-and-generations.md) | application-software-artifacts.md · publication-recovery.md · immutable-objects.md · payload-paths.md | Reader synthesis committed; original detail preserved |
| [Provenance and observation publication](guide/provenance-and-observation-publication.md) | build-record-integration.md · observation-snapshot-publication.md · build-trace-contract.md · integration-observations.md | Reader synthesis committed; original detail preserved |

**Editorial boundary:** The remaining manual chapters still need full synthesis. The retained documents must be compared line-by-line for unique requirements, example validity, duplicate claims, implemented-versus-historical status and explicit acceptance evidence before any source deletion. Machine-readable schemas and release provenance remain standalone. Source change does not establish production deployment or stable-release readiness.

## Editorial consolidation progress — 2026-10-12, continuation

The following chapter entry points now contain substantive synthesis of the preserved detailed sources. Unique versioned contracts, source evidence and historical acceptance declarations remain under their existing paths; the prose has **not** authorized deletion of any original document or production deployment.

| Reader chapter | Important preserved sources | Status |
|---|---|---|
| [Bootstrap pipeline](guide/bootstrap-pipeline.md) | BOOTSTRAP-STAGES.md · NATIVE-BUILD-ENVIRONMENT.md · retained-compiler.md | Synthesized; detailed contract retained |
| [Toolchains and language runtimes](guide/toolchains-and-language-runtimes.md) | python-libraries.md · python-runtime.md · python-enrollment.md · rust-bootstrap.md · maturin-bootstrap.md · cryptography-bootstrap.md | Synthesized; detailed contract retained |

**Unresolved editorial work:** Reconcile source claims and examples against the current implementation before replacing detailed files; complete the remaining chapter summaries; audit duplicate or superseded requirements separately from live acceptance. This is documentation review, not a component release candidate.

## Editorial consolidation progress — 2026-10-12, remote and graphics

Two additional chapters are synthesized for the public reading path. The exact producer operation, source pin, graphics-recipe and runtime-facility contracts remain in their original independently addressable documents.

| Chapter | Preserved source details | Current editorial disposition |
|---|---|---|
| [Remote execution and gateway](guide/remote-execution-and-gateway.md) | remote-operations.md; registration-recovery.md; registration-continuation.md; CONTROLLER-INTEGRATION.md | Synthesis committed; exact API/schema version retained in source |
| [Recipes, graphics and runtime facilities](guide/recipes-graphics-and-runtime-facilities.md) | graphics-foundation.md; graphics-recipe-status.md; graphics-rpm-review.md; runtime-facilities.md | Synthesis committed; recipe maturity is not live acceptance |

No exact contracts, tests, evidence or operational ledgers were deleted by this editorial pass.

## Editorial consolidation progress — 2026-10-12, enrollment and contracts

Two further reader chapters replace placeholders with reviewed conceptual synthesis. Detailed source contracts and immutable schemas remain at their original paths, including older dated implementation and acceptance reports. Where later sources supersede an earlier limitation, the consolidated chapter names the change in scope without deleting the historical evidence.

| Consolidated chapter | Preserved contract or evidence | Treatment |
|---|---|---|
| [Recovery and verification](guide/recovery-and-verification.md) | publication-recovery.md · registration-recovery.md · integration-observations.md · VALIDATION.md · CURRENT-STATUS.md | Synthesis committed; original authoritative sources retained |
| [Reference and schemas](guide/reference-and-schemas.md) | schemas/* · integration-observations.md · build-record-integration.md · observation-snapshot-publication.md | Synthesis committed; original authoritative sources retained |

**Evidence boundary:** This editorial work makes no production cutover, host mutation, rootfs publication, source-pin update or new acceptance claim. Remaining chapters and line-by-line reconciliation of redundant historical notes are separate tasks.

## Requirement-family reconciliation — 2026-10-12

The architecture and verification chapters now consolidate the active conceptual model. This matrix identifies requirement families that must survive before dated checkpoint or log documents can be archived; an older status report is not authoritative current deployment evidence.

| ID and requirement family | Reader synthesis | Retained detailed sources | Deduplication disposition |
|---|---|---|---|
| **IB-ARCH-01** — Reviewed source identity, exact recipe/pin selection, immutable pipeline inputs | [Overview](guide/overview-and-architecture.md), [Source pins](guide/sources-and-monthly-pins.md) | [Architecture checkpoint](catalogue/IMAGE-BUILD-ARCHITECTURE.md), [Current status](CURRENT-STATUS.md) | Keep checkpoint as historical; compare original seed/recipe assertions against current source before archiving |
| **IB-EXEC-02** — Finite controller execution, registered roots, identities and uncertainty | [Remote interface](guide/remote-execution-and-gateway.md), [Recovery](guide/recovery-and-verification.md) | [Controller integration](CONTROLLER-INTEGRATION.md), [Registration recovery](registration-recovery.md) | Keep executable owner contract; retain unique timeout and replay behavior verbatim |
| **IB-PUB-03** — Immutable generation/artifact/view identities and distinct recovery | [Immutable products](guide/immutable-artifacts-and-generations.md) | [Publication recovery](publication-recovery.md), [Application artifacts](application-software-artifacts.md) | Keep versioned manifests and recovery matrices independent |
| **IB-OBS-04** — Named verification, execution environment and selected observation snapshots | [Provenance](guide/provenance-and-observation-publication.md), [Schemas](guide/reference-and-schemas.md) | [Integration observations](integration-observations.md), [Snapshot selection](observation-snapshot-publication.md) | Keep wire JSON schemas and producer contracts; v1 is not automatically v2 |
| **IB-VAL-05** — Per-revision acceptance facts, skips, failures and external live-host evidence | [Recovery/verification](guide/recovery-and-verification.md) | [Validation chronology](VALIDATION.md), [Current status](CURRENT-STATUS.md), [Implementation report](catalogue/IMPLEMENTATION-REPORT.md) | Candidate to archive dated results under know-file after stable evidence links; not delete or merge test outputs as current facts |
| **IB-REL-06** — Licensing and release provenance separate from source/download success | [Schema reference](guide/reference-and-schemas.md), [Sources](guide/sources-and-monthly-pins.md) | [Licensing](LICENSING.md) | Keep license/patch declarations and unresolved coverage independently auditable |

**Retirement gate:** Before removing a source file, enumerate every `MUST`, `MUST NOT`, API field, error/status meaning, request identity, example path, test limit, unique historical result and licensing notice. Verify each surviving destination against the exact reviewed implementation and version. Keep an immutable know-file reference for dated evidence, update all inbound links, run source/packaging checks, and obtain an explicit commit review. No original documents are retired by this matrix.

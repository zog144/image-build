# Reference and schemas

## Find the authoritative contract

The manual's topic chapters explain responsibilities and reader workflows. **Versioned machine-readable schemas and frozen source/operation manifests remain independently addressable**: do not simplify a schema by paraphrasing the manual, change its wire shape, or reinterpret an historical record as a new protocol version.

Use these reference categories rather than guessing from filenames:

| Area | Primary source | Ownership and evidence |
|---|---|---|
| Monthly source selection | [Monthly pins](../MONTHLY-PINS.md) | Original pin, per-recipe closure, exact source digests |
| Remote producer operations | [Remote operation contract](../remote-operations.md) | Closed `image-build-remote-operation-v1` requests and capability discovery |
| Box-control build boundary | [Controller integration](../CONTROLLER-INTEGRATION.md) | Durable build-job resources, command identity, cleanup, and seed checks |
| Package/generation provenance | [build-record integration](../build-record-integration.md) | Canonical records, exact input closure, terminal attempts, generations |
| Integration observations | [Producer interface](../integration-observations.md) | Named verification, source/artifact relationships and explicit coverage |
| Snapshot selection | [Publication contract](../observation-snapshot-publication.md) | Explicit owner snapshot receipt and selected identity |
| Application software | [Artifacts and views](../application-software-artifacts.md) | `applications-v1`, `application-software-view-v1` and consumer binding |
| Immutable object inspection | [Read-only report](../immutable-objects.md) | Local protections, unknown references; never deletion authorization |
| Host/runtime facilities | [Facility normalization](../runtime-facilities.md) | Frozen empty scaffolds and runtime-created children |
| Package licenses | [Licensing](../LICENSING.md) | Scoped terms, retained notices, unresolved reviews |

## Machine-readable verification contracts

The JSON Schema documents remain at their current stable paths:

- [Candidate verifications, v1](../schemas/candidate-verifications-v1.schema.json) — owner-scoped candidate verification data, including failures before generation publication.
- [Integration observations, v1](../schemas/integration-observations-v1.schema.json) — observed relationships and completeness declarations for a selected owner context.
- [Verification observation, v1](../schemas/verification-observation-v1.schema.json) — legacy observation form.
- [Verification observation, v2](../schemas/verification-observation-v2.schema.json) — newer observation form with explicit execution-environment evidence.

Schemas are validated and versioned by their producers and consumers; a reader must not infer that records using v1 silently possess fields required by v2. The retained [integration observation guide](../integration-observations.md) explains what requires rootfs bytes, provenance configuration and a trusted readelf/inspection environment, and what remains unavailable.

## Lifecycle of a verification fact

An image-build owner captures a named execution/test/check along with its identity and actual observed result. Where provenance is configured, build-record receives immutable canonical facts; image-build publishes an exact selected observation snapshot. Build-trace requires that exact caller-selected snapshot and exposes read-only fact traversal. Integrate-observe operates on selected worlds/comparisons; it does not automatically pick the latest or reinterpret missing facts as a pass.

This path is separate from box-control's operational history and journald logs. A log reference may identify the original command without guaranteeing unlimited retention of its text, and a failed candidate can carry verifications without becoming a published rootfs generation.

## Scope of historical catalogues

The [architecture checkpoint](../catalogue/IMAGE-BUILD-ARCHITECTURE.md), [implementation report](../catalogue/IMPLEMENTATION-REPORT.md), [toolchain catalogue](../catalogue/TOOLCHAIN-CATALOGUE.md), [validation log](../VALIDATION.md) and [status chronology](../CURRENT-STATUS.md) retain historical source reviews and dated acceptance evidence. They often mention limitations that later source may have closed. Use exact source revisions and contemporary CI/live evidence to decide which limitations remain current; do not erase historical reports in order to make the manual shorter.

The Zog aggregate should copy the selected **reviewed source revision** of `docs/image-build/` into the same final path. Component `unstable` changing is not the same as publication in the release-build candidate. Keep release provenance, notice/license information, source-to-destination mapping and schema bytes checked during export.

## Consumer rules

1. Require the exact schema/contract version published by the producer; reject missing required fields and do not invent compatibility conversions.
2. Preserve the authority distinction: current configuration, selected generation, canonical record, selected snapshot, observed systemd state and release acceptance are different facts.
3. Keep hashes, source-pin identities and observation coverage as separate fields. A recorded digest is not a complete security or license review.
4. Use bounded read-only inspection for navigation and diagnostics; authorization to mutate belongs to the owning service.
5. Carry references and historical version/status declarations forward when synthesizing prose. Do not delete source documents until every unique requirement, example and evidence path is accounted for.

### Reading paths

- [Provenance and publication](provenance-and-observation-publication.md)
- [Immutable software stores and reclamation](immutable-artifacts-and-generations.md)
- [Recovery and verification](recovery-and-verification.md)
- [Sources and pins](sources-and-monthly-pins.md)
- [Technical traceability](../TRACEABILITY.md)

This reference is not a substitute for the schema files themselves or for verification against a deployed producer version.

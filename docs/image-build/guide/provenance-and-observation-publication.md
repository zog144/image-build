# Provenance and observation publication

## Producer, store and consumer boundaries

Image-build is the **owner and producer** of build provenance; build-record validates and stores immutable canonical records, build-trace exposes read-only structured inspection, and integrate-observe compares caller-selected evidence. A completed build does not automatically imply a complete provenance graph; missing or unverified evidence must be explicit.

For configured owner pipelines, image-build binds the original pin bytes and repository revision, toolchain/project identity, consumed source hashes, command/environment inputs and retries. It publishes a canonical attempt-start before dispatch. Prepared record pointers preserve exact original inputs across controller recovery. A failed command can have an immutable failed result; a lost or ambiguous execution must not be misreported as successful or automatically replayed.

## Generation records versus observation snapshots

A canonical generation record represents selected immutable build output. An **observation snapshot** is a separately published and **explicitly selected** collection of canonical verification/integration observations for that generation. Its publication sequence freezes an owner intent, writes required records, writes the snapshot last, verifies closure, stores a receipt and atomically selects the exact snapshot ID.

A record merely present in build-record is not a publication receipt. A receipt is not an owner selection. The selected snapshot is not inferred from a timestamp or by scanning for a "latest" record. A reused generation preserves its existing selection; later observations need an explicit refresh. If a publication/pointer response is uncertain, recovery resumes the exact frozen envelope before a subsequent refresh.

The documented inspection/read methods are `selected_observation_snapshot(generation)` and `observation_snapshots(generation)`. `generation.inspect` exposes the selected build-trace snapshot ID when available, or explicit `missing_evidence`; it does not manufacture a selection.

## Coverage and reproducible comparison

The producer records what was examined and what remains unknown. Build-trace's public contract distinguishes reference closure, declared evidence gaps and observation coverage, which are not one interchangeable completeness boolean. An integrate-observe comparison preserves that distinction and does not itself assert chronology, regression, causation or policy.

Backfilling a retained generation's observation snapshot needs its original compatible provenance configuration, immutable generation and required inspection tools. It does **not** rerun packages or change the generation manifest/inventory. Canonical snapshot IDs remain exact inputs to independent consumers.

## Reference contracts

- [Producer ordering, recovery and scope](../build-record-integration.md)
- [Snapshot publication, selection and backfill](../observation-snapshot-publication.md)
- [Build-trace integration contract](../build-trace-contract.md)
- [Integration observation formats](../integration-observations.md)
- [Machine-readable schema files](../schemas/)

Historical version claims in detailed sources are retained for audit and must be checked against the deployed dependencies before a live acceptance claim.

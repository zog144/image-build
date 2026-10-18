# Sources and monthly pins

## Contract and ownership

Normal image-build pipelines select a **reviewed monthly source set**; they do not resolve a mutable upstream default branch at launch. The authoritative source selection comprises the recipe revision and declared source URL, SHA-256, destination and archive information. A source pin is **not** by itself evidence of build acceptance or license review.

The maintained pin sets live in `project/pins/YYYY-MM-01/commit-pin.py`, using Python literal data parsed with `ast.literal_eval`; `project/pins/current.py` explicitly selects the normal default. The October 2026 set was recorded on October 2 and deliberately does not claim a verified October 1 upstream snapshot. Exact version exceptions and unknown upstream commit IDs must remain visible rather than guessed. See [monthly pins](../MONTHLY-PINS.md).

## Bound source identity over a build lifetime

Recipe materialization freezes the selected `commit-pin.py` alongside staged recipes. A regular pipeline records the source-pins digest and recipe inventory. Changes to the current month, original pin file or catalogue **do not retarget** an already prepared pipeline; resume checks the frozen selection. Missing/altered `recipe:` bundled inputs and unpinned custom recipes fail before download/dispatch.

Maintainers preparing a new month copy the previous literal set, review exact upstream revisions, hashes, license/patch changes and exceptions, validate affected recipes, and commit the new set. Corrections within a month change both its digest and source revision, but cannot rewrite an existing bound operation.

## Source acquisition is a separate transport decision

For ordinary HTTPS sources the documented acquisition order is:

1. Verify an existing local content-addressed cache entry.
2. Try ready, authorized archive-mirror providers.
3. Fetch from the recipe's canonical upstream location.

Only bytes matching the pinned digest enter the ordinary SHA-256 cache. A corrupt local cache is a **hard fault**, not permission to silently re-download. Mirror readiness, authorization, redirect, size or hash failures can be recorded as transport observations and may fall through to another authorized provider or upstream. `recipe:` and explicit `file:` sources have distinct local transport rules.

Mirror evidence records sanitized provider/result categories and the source request without storing bearer credentials. Whether acquisition came from mirror or upstream does not change the recipe or generation identity. The documented archive-mirror automatic collector initially handled monthly Git-tree archives, not every upstream release tarball; confirm deployed provider capabilities independently. See [archive-mirror source acquisition](../archive-mirror-sources.md).

## Provenance, verification and boundaries

Image-build may retain source-selection and build-input records in build-record, but transport observations, source IDs, canonical attempt records, package fingerprints and generation IDs are **different identities**. Do not substitute a cache hit for a provenance claim or an upstream SHA-256 for a complete license audit. A future multi-host source attestation check must compare independently verified declared bytes and signing evidence; it must not silently revise the monthly pin.

## Authoritative details

- [Monthly pin format, exceptions and refresh procedure](../MONTHLY-PINS.md)
- [Mirror configuration, authentication and source-acquisition evidence](../archive-mirror-sources.md)
- [Licensing boundaries](../LICENSING.md)
- [Canonical build-record producer integration](../build-record-integration.md)

The overview is maintained guidance. Exact pin schema and recorded implementation constraints in the references remain authoritative.

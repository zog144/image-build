# Integration observations: producer contracts

This read-only interface supplies build facts to build-record and build-trace.
It performs no regression analysis, compatibility judgment, release policy or
human decision tracking. JSON Schemas live in `docs/schemas/`.

## Export and consumption

```
python -m zog.image_build.integration_observations \
  --state /path/to/project/state \
  --provenance-config /path/to/frozen-operation/intent.json \
  --selection /path/to/generation \
  --output /path/to/integration-observations.json
```

The config argument accepts either a provenance configuration or an owner intent
containing `provenance`. Scope must match the canonical generation. The exporter
verifies canonical closure, retained material hashes and current generation bytes.
It does not read the current recipe catalogue or monthly branch head. `--readelf`
selects a trusted inspection-host tool; target executables are never run.

`--candidate <64-hex-owner-generation>` instead of `--selection` exports captured
verification outcomes, including failed candidates that were never published.
A candidate identifier is `identity(frozen owner inputs)`, not a published root
assertion. Python APIs are `export_generation(provenance, selection)` and
`export_candidate(provenance, candidate_id)`.

The generation export context binds canonical generation ID/record and root
inventory digest. It is explicitly a **post-build inspection**, not a retrofit of
pre-execution evidence. Import this envelope as a producer artifact in build-record
or expose it read-only in build-trace; do not invent a canonical record kind until
build-record owns that schema. Existing canonical generations remain unchanged.

## Named verification

For newly executed installed checks under `image-build-installed-verification-v1`,
`seed_build.verify` captures terminal outcomes automatically. The stable logical
ID is `image-build/<frozen verification_check>/command/<ordinal>`; absent check
names use the existing `installed-trust` default. Identity is scoped to a named
command check, not each individual upstream test hidden inside its shell command.
Recipe authors must preserve logical names and ordinal meaning; a new logical
check requires a new name. Compare `definition_digest` separately: a recognizable
logical check can change its command definition between generations.

Verification observations have two immutable producer versions.

`image-build-verification-observation-v1` is legacy evidence. Its
`environment_digest` remains the historical broad digest of image-build's complete
operation policy. That value is truthful audit evidence but is **opaque for execution
comparability** and is never reinterpreted or rewritten.

Newly prepared named installed verifications freeze
`image-build-verification-observation-v2`. Each v2 row retains the content-derived
`id`, check ID, independent command `definition_digest`, candidate/root subject,
host/project/attempt identity, sequence, terminal outcome, execution identity and
evidence refs. It additionally contains:

- `execution_environment.contract = image-build-verification-environment-v1`;
- `execution_environment.descriptor`, containing only normalized facts that affect
  execution semantics;
- `execution_environment.digest`, the digest of the complete descriptor;
- `producer_policy_digest`, the separate broad image-build operation-policy digest.

V2 deliberately has **no** `environment_digest` field. That field remains a v1-only
legacy opaque identity so consumers cannot accidentally treat old broad policy hashes
as equivalent to the new versioned execution-environment digest.

The execution-environment descriptor uses the coordinated build-record domains
`isolation`, `user`, `root`, `network`, `timeout`, and `runtime`. It binds
box-control build-job mode, mount/user-namespace policy, explicit execution UID/GID,
read-only-root and network policy, an opaque digest of any device profile, guest
working directory, the complete controlled process environment, execution/startup/
termination timeouts, and resource limits. Numeric limits that can exceed portable
JSON integer bounds are normalized as decimal strings.

It excludes command argv, generation/root identity, attempt/runtime/invocation/job
IDs, journal locators, host filesystem root/source/output paths, timestamps,
project/socket locators, provenance configuration, source-mirror configuration and
dependency-replacement metadata.

Therefore:

```text
definition identity
!= execution-environment identity
!= producer-policy identity
!= execution/subject identity
```

A command change changes `definition_digest`; it does not by itself change the
execution environment. A provenance/source-mirror change changes
`producer_policy_digest`; it does not by itself make otherwise identical command
execution conditions incomparable. Conversely, timeout, network, read-only-root,
execution identity, device policy or resource-limit changes produce a different v2
environment digest.

The v2 descriptor is frozen before first submission and reconstructed from the exact
retained execution request/controller binding after completion. If those differ,
capture fails closed. Secret-like process environment is rejected rather than
serialized. Pending/unknown execution still produces **no terminal observation**.

`PASS` means a cleaned-up exit 0; `FAIL` means a terminal nonzero exit; `ERROR`
means a terminal signal/timeout/controller fault/cancellation. `SKIP` is reserved by
the schemas; this producer does not currently emit it. Absence never means SKIP or
test removal.
Sequence orders commands within an attempt. New captures freeze an `observed_at`
timestamp for observation ordering, explicitly distinct from execution time.
Execution timestamps are null
when not present in owner evidence; consumers must not invent chronology from
hash IDs or filenames. Canonical attempt/job records provide further ordering.
Historical report projections have null observation time; no historical timestamp
is manufactured.

Material is retained in the existing build-record artifact store. A descriptor
is saved beside the verification attempt and indexed by candidate identity under
`build-record/observation-index`. Consumers use the export API, not that layout.
Repeated capture reuses exact bytes; a conflicting outcome for a saved command
fails closed. Runtime IDs, invocation IDs, journal references and build-trace
references identify execution evidence; log contents are not copied into reports.

Existing canonical installed-verification reports retain their historical broad
`policy_digest` and are projected only as v1 PASS observations. Image-build does not
manufacture a v2 environment descriptor from those reports because the exact original
execution-relevant request/configuration is not guaranteed to be reconstructable.
Their descriptor and canonical generation remain evidence. New v2 captures take
precedence for the same check/invocation; conflicting outcomes are rejected. Legacy
generations without named reports carry an explicit gap. Initial coverage excludes
package upstream suite subcases and anonymous old verification jobs.

## Artifact and package relationships

ELF inspection emits `needs-library` (DT_NEEDED), `provides-soname` (DT_SONAME),
and `elf-interpreter` (PT_INTERP). Shebang inspection emits `script-interpreter`
and preserves the optional argument. `/usr/bin/env python3` reports `/usr/bin/env`
plus its argument; it does not resolve the command using the inspection host PATH.
Subjects include installed path, content SHA256 and matching package owners.
Symlinks are not followed. Missing readelf, malformed ELF, inspection limits and
unsupported shebangs produce explicit gaps. Readelf executable digest identifies
the inspection implementation. No loader search, dlopen, RPATH resolution, ABI
judgment or service analysis is claimed. An empty relation list is not proof of
no dependencies: consumers must inspect coverage/gaps.

Frozen recipe dependencies produce `declares-build-dependency`,
`declares-test-dependency`, and `declares-runtime-dependency`. Canonical resolved
input bindings independently produce `used-build-output`, retaining exact output
record references. Declarations and resolved build inputs are not interchangeable.

## Sources

Each source observation identifies package/project (where recorded), exact output,
build-input and source-selection records, monthly pin, archive name/hash/size,
frozen download declaration, and upstream repository/revision declarations.
`revision_type` distinguishes full Git commits, explicit tags, opaque strings and
unknowns. Explicit `tag` is now supported in source-provenance.py and exported in
`release_tags`; opaque values are not guessed to be tags. Canonical build-record's
current narrower upstream fields remain unchanged; the complete declaration is
retained in frozen recipe bytes. Unknown origins remain unknown.

Archive bytes are authoritative. Repository/revision association is a reviewed
metadata declaration, not independently verified reproduction from Git. No current
catalogue origin is substituted for legacy records. Patch records remain in the
canonical closure; this export does not interpret patch semantics.

## Identity and evolution

Schema names are explicit dispatch keys; v1 and v2 verification rows are distinct
immutable contracts. Reject unsupported versions. IDs are `sha256:` plus image-build
`identity(payload-without-id)` (sorted compact JSON, Python's default ASCII escaping).
Reference strings and artifact descriptors retain build-record's own contract.
Producer implementation digest covers the observation modules. Required structures are
described by JSON Schema; opaque canonical references are validated by the owning
build-record reader.

The coordinated build-record `unstable` contract accepts
`image-build-verification-observation-v2`, validates
`image-build-verification-environment-v1`, and preserves v1
`environment_digest` records as legacy opaque evidence. Image-build never downgrades
or synthesizes one contract from the other.

This version is sufficient for early consumer development, not exhaustive test
coverage or a complete dependency graph. Further observations should use explicit
new schema versions or separately dispatched observation types.

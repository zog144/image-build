# Immutable object reference and reclamation inspection

Image-build publishes several immutable object classes that have different consumers:

- rootfs generations;
- remote recipe snapshots;
- application-software artifacts;
- application-software views.

The read-only module:

```text
zog.image_build.immutable_objects
```

produces:

```text
image-build-immutable-object-report-v1
```

It verifies the published object stores, builds image-build's locally provable
reference graph, and exports the exact locally protected object set.

It is deliberately **not** a deletion/reclamation API.

## Command

```sh
python -m zog.image_build.immutable_objects \
  --state-dir /absolute/project/state
```

The report is deterministic for unchanged state and contains no observation timestamp.

## Object classes

The report enumerates and verifies:

```text
generation
recipe-snapshot
application-view
application-artifact
```

Each published object is resolved with the same existing reader used by normal
image-build consumption. Inventory, manifest identity, package/pin binding, view
composition, symlink safety, and other store-specific checks therefore remain owned by
their original producer contracts.

A corrupt object is reported with:

```text
classification = integrity-fault
reclamation = blocked-integrity-fault
```

It is never exposed as a reclamation candidate.

## Local references and protection

The current report recognizes these durable reference sources:

- `active` and `toolchain-active` generation selections;
- pipeline input generation;
- pipeline output generation;
- pipeline-owned recipe snapshot;
- unresolved remote-operation generation/selection/recipe-snapshot inputs;
- unresolved remote-operation recipe-snapshot bindings;
- completed and pending application publication receipts;
- application view -> artifact composition.

Pipeline inputs and recipe snapshots are locally protected while the pipeline is
`prepared`, `running`, or `pending`.

Completed/released pipeline history remains a reference but is not, by itself, treated
as an image-build-local reclamation prohibition.

A retained application view always protects its referenced artifacts because removing
one would invalidate the immutable view.

A publication with frozen identity but no durable result receipt protects the
published object identity while recovery remains unresolved.

## Classification

Each valid object is classified as exactly one of:

```text
protected
referenced
apparently-unreferenced
unknown
```

`protected` has at least one image-build-local protection reason.

`referenced` has retained local references, but none currently establish a local
reclamation prohibition.

`apparently-unreferenced` means no reference was found in the locally understood
image-build state.

`unknown` means some reference-bearing state was unreadable or otherwise invalid, so
image-build refuses to conclude that an otherwise unprotected object is unreferenced.

The report also exports grouped:

```text
protection_set
apparent_candidates
```

These are inspection outputs, not deletion authorization.

## Fail-closed reference completeness

If a pipeline record, remote-operation record, application publication record, or
generation-selection pointer cannot be interpreted safely, then:

```text
reference_complete = false
```

All otherwise unprotected objects become `unknown`; none remain in
`apparent_candidates`.

A reference to an unavailable published object is likewise a reference-completeness
fault.

This intentionally favors over-retention.

## Reclamation authority

Every report contains:

```json
"reclamation_authorized": false
```

Image-build cannot independently know all live box-control runtime, prepared-operation,
cleanup, retained-history, host-deploy, or station-access protections.

Before any future reclamation implementation removes an object, an owner must combine
this local report with the relevant external protection set and an explicit retention
policy.

In particular, `apparently-unreferenced` means only:

> image-build found no local reference it currently understands.

It does **not** mean:

> safe to delete.

## Read-only guarantee

The inspection path does not instantiate the mutating application/software stores,
does not create missing directories, does not write result files, and does not prune
staging.

If an existing `image-build.lock` is present it is opened read-only and held with a
shared flock for the report. The report never creates the lock file.

The report itself includes a `report_digest` over all report fields except the digest.

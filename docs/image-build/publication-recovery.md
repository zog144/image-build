# Immutable publication and recovery

Image-build publishes several content-addressed immutable stores.  Their recovery
rules follow one common principle:

> A successfully published immutable object is authoritative.  Unpublished staging
> may be reconstructed only when the exact source needed to reconstruct it remains
> durably bound and available.  Corrupt staging that contains the only frozen bytes
> fails closed.

This document covers rootfs generations, remote recipe snapshots, application-software
artifacts, and application-software views.

## Generation publication

Generation identity is derived from immutable generation inputs.

Generation publication staging now uses:

```text
state/image-build/publication/<generation-id>/
```

rather than a random staging identity.

Before publication image-build freezes the expected root inventory and complete
generation manifest.  If the deterministic staging directory already exists:

- a valid staging generation with the exact expected manifest is reused;
- a partial/unreadable staging tree is discarded and rebuilt from the still-bound
  caller source root;
- a valid staging generation whose manifest differs is an integrity fault and is
  retained for investigation.

The final namespace transition is one atomic replace into:

```text
state/image-build/generations/<generation-id>/
```

If the replace succeeded but the caller lost the response, retry sees the published
generation first, verifies it, and reuses the exact identity.  It never creates a
second generation for the same inputs.

## Recipe snapshots

Recipe snapshots keep operation-local staging below:

```text
state/image-build/recipe-snapshots/candidates/<operation-id>/
```

A candidate is explicitly non-authoritative.  The exact remote request plus immutable
deployed source revision/monthly pin are sufficient to materialize it again, so stale
or partial candidate staging is rebuilt.

Publication is an atomic replace into the content-addressed snapshot store.

If publication succeeded but the response was lost, an identical retry rematerializes
the exact candidate, discovers the already-published content identity, verifies the
published snapshot, removes the redundant candidate, and returns the existing
snapshot.

The remote-operation binding remains the durable caller-facing identity once it has
been written.

## Application-software artifacts

Application artifact staging differs from recipe snapshots.

After freeze, the producer's installed runtime tree is moved from the operation staging
root into the publication candidate.  That candidate may therefore contain the only
remaining copy of the exact frozen installed bytes.

Consequently:

- an intact candidate resumes publication;
- a corrupt candidate fails closed;
- image-build does **not** discard and rebuild corrupt artifact candidates from source
  metadata, because doing so would silently substitute new installed bytes.

Publication atomically replaces the candidate into the content-addressed artifact
store.

If that replace succeeds but the result receipt is lost, retry verifies the published
artifact against the frozen manifest, records the missing result receipt, and returns
the same artifact identity.

## Application-software views

Views are deterministic symlink compositions of already-published immutable artifacts.
They contain no unique producer output bytes.

Therefore stale/corrupt unpublished view candidates may be discarded and recomposed
from the frozen view manifest and exact referenced artifact IDs.

Published views remain immutable and are always verified before reuse.

The existing lost-response recovery rule remains: if atomic publication succeeded
before response loss, retry resolves and verifies that same content-addressed view and
writes the missing operation result.

## Fault-injection coverage

The publication recovery suite covers:

- response loss immediately after generation namespace publication;
- partial stale generation staging;
- valid-but-conflicting generation staging;
- response loss immediately after recipe-snapshot publication;
- stale recipe-snapshot candidate reconstruction;
- response loss immediately after application-artifact publication;
- corrupt application-artifact candidate fail-closed behavior;
- stale application-view candidate deterministic recomposition.

Existing store-specific tests continue to cover published-object tampering, changed
frozen inputs, view lost-response recovery, immutable prior views/artifacts, and
consumer integrity checks.

No recovery test authorizes deletion of published immutable objects.  Reclamation is a
separate owner/policy decision described in `docs/immutable-objects.md`.

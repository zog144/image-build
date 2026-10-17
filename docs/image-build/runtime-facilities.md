# Runtime facility roots in application images

Contract: `image-build-runtime-facility-intent-v1`.

Application-image generations and runtime controller facilities have separate
ownership. The immutable generation supplies software; box-control/root-control own
`/applications`, `/run`, `/proc`, `/sys` and `/dev` inside each private runtime
scaffold.

Package builds remain factual. If an accepted package output contains an empty
runtime directory such as D-Bus's `/run/dbus`, image-build does **not** rewrite that
package output or its provenance record. During application-image composition only,
image-build:

1. verifies every package object at or below a facility root is a real directory;
2. rejects files, symlinks, special objects, facility-root mode changes and
   conflicting nested directory modes;
3. records each nested directory with its exact mode and contributing packages in
   `runtime_facility_intent`;
4. omits those directory-only facility trees from the application-image copy;
5. creates the five facility roots as empty real 0755 directories.

Nested entries are marked `materialization: runtime-owner`. This records that the
directory is ephemeral and must be recreated by the runtime owner when the software
actually requires it; it is not immutable application-image content. Facility roots
are marked `controller-private-scaffold` and are always supplied by the controller.

The exact intent is frozen both in generation inputs (therefore generation identity)
and the immutable manifest, and is retained as
`application-runtime-facilities.json` in canonical assembly materials. Package
provenance still points to the unmodified accepted output containing the original
directory.

This policy never edits an already-published generation. A corrected generation is
a new immutable publication assembled from the same accepted package outputs.

## Consumer boundary

The coordinated controller contract is the strict private-scaffold implementation:

- box-control `b61f0f1c3f697db33e1edf61c84bfae85d7a7e16`;
- root-control `39ece63e33e6ec71463216eb6eea908ba81a244c`.

Those controllers accept a facility root only when it is absent or an empty real
directory; they reject non-empty content and symlinks. Image-build CI tests the
normalized image against the actual box-control scaffold reader at that pin.

No controller gate is weakened by this policy.

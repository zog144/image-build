# Immutable application data targets

Contract: `image-build-application-data-targets-v1`.

Application data remains controller-owned writable storage. Image-build owns only
the immutable **mount target directories** that must exist before box-control may
overlay that storage.

The current reviewed production application image declares exactly:

- `/var/lib/archive-mirror`, mode 0755;
- `/var/lib/station-access`, mode 0755.

Each target is recorded as
`materialization: immutable-empty-mount-target`.

Publication freezes the complete contract in both generation inputs and the
immutable manifest under `application_data_targets`. The canonical assembly
materials also retain `application-data-targets.json`.

## Safety rules

A publication may add an absent target, or retain an already-existing empty real
directory with the required mode. It refuses publication when an accepted runtime
already contains:

- a file or symlink at a target;
- a non-directory ancestor such as a redirected `/var/lib`;
- any descendant content beneath a target;
- a target with a conflicting mode.

After composition image-build verifies both targets are empty real directories
beneath real parents. It never removes accepted data to make a target appear empty.

This rule is independent of the controller-owned runtime facilities
`/applications`, `/run`, `/proc`, `/sys`, and `/dev`. Their existing
`image-build-runtime-facility-intent-v1` normalization is unchanged.

## Consumer evidence

The live blocker was observed with box-control
`d913e70585ab241696ebf771b93a398d5337217c`. Its
`zog-mounts-v1` policy calls mount validation with `require_targets=True` during
persistent application preparation and refuses to create a missing target inside a
published image.

The exact reviewed consumer source blob is pinned by
`tests/fixtures/application-data-target-controller-contract.json`.

## Publication boundary

This change does not mutate generation
`3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc`
or any other existing generation. A Work/live pass must republish a **new** immutable
application image from the exact retained accepted runtime/component inputs using
the corrected image-build source revision.

No toolchain recompilation is implied by this layout-only publication change.

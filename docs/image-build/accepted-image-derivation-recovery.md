# Accepted image derivation for certify-manage runtime recovery

This is the producer-side recovery path for the retained Certbot target image whose
historical package-output/base closure is no longer available.

It is **not** a substitute for `runtime_image.publish`, does not relabel an image as
a toolchain, and does not claim that missing historical provenance has been
recovered.

## Production recovery profile

`zog.image_build.accepted_image_derivation.CERTIFY_MANAGE_RECOVERY` binds:

- retained parent generation:
  `3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc`;
- exact retained parent manifest SHA256:
  `ebc8b392d9faf628f4264c64b011cf4f25ce1efb6f1dae74876635bff4bc2132`;
- exact parent output count: **40,945**;
- recorded missing historical base:
  `f07ee7f1422c04af4f1d5c5c5685bea9efc9cf046214737e6fb82e46ed063513`;
- recorded missing component-output count: **54**;
- required newly materialized target:
  `/var/lib/zog-certify-manage`, mode `0700`;
- the retained review-record revision/path that established those facts.

At execution time the operation also copies the exact 54 component-output names and
recorded absolute roots from the retained parent's immutable publication inputs into
the new `image-build-historical-provenance-gap-v1` record. They are evidence of
missing historical inputs, not reconstructed dependencies.

If the historical base generation or **any** recorded component output has become
available again, the recovery operation refuses to run. The provenance-complete
publisher must be used instead.

## Transformation

The parent is reopened through normal `read_selection`, which verifies:

- generation/input identity;
- complete current root inventory against the retained 40,945-entry manifest;
- rootfs compatibility and other generic generation contracts.

The manifest file is then independently checked against the exact SHA256 above.

The operation copies the immutable root to caller-owned staging and may add only
directories required by the current
`image-build-application-data-targets-v1` contract. The certify-manage directory
must be absent in the parent and newly created by this operation.

Because the current target contract also includes archive-mirror and station-access,
a parent that lacks either of those empty targets may gain them at the same time.
No file, symlink, existing directory mode, executable, library or other retained
payload entry may change.

The candidate is accepted only when:

- every parent inventory record is byte/mode/target identical in the candidate;
- the only new inventory entries are reviewed empty data-target directories;
- every target is a real empty directory with its exact required mode;
- the exact parent `application_software_compatibility` descriptor remains
  unchanged;
- fresh candidate inventory identity/count are recorded.

The new generation inputs contain
`image-build-accepted-image-derivation-v1` plus
`image-build-accepted-image-derivation-acceptance-v1`. The generation identity
therefore binds the parent, parent manifest digest, complete parent inventory
identity, exact missing historical inputs, exact transformation, producer source
revision and fresh structural acceptance.

## Provenance and verification claims

The resulting generation explicitly records:

- `historical_provenance_complete=false`;
- `verification_inherited_from=<parent generation>`;
- `image-build-historical-provenance-gap-v1` with status `incomplete`;
- forbidden claims including fresh runtime verification, complete historical
  package-output closure, available historical base, or parent-as-toolchain.

No canonical `build_record` is fabricated.

The fresh acceptance proves only deterministic image derivation/inventory/ABI
preservation. It does **not** rerun the parent's compiler/runtime acceptance or
Certbot application acceptance.

## Durability and recovery

Operations live below:

`STATE/image-build/accepted-image-derivations/<operation-name>/`

with durable:

- `intent.json` — frozen source/profile/parent/gap binding;
- `status.json` — prepared/assembled/complete phase;
- `acceptance.json` — candidate preservation/delta evidence;
- `derived-root/` — disposable deterministic staging;
- `result.json` — completed generation receipt.

A retry with changed source/profile/parent fails closed. A retry after interruption
revalidates the parent, recreates disposable staging deterministically and reuses
image-build's atomic publication candidate/generation machinery.

The immutable-object reference graph protects the retained parent while the
derivation is pending. Once the derived generation exists, that generation itself
retains a protecting `accepted-image-parent` reference to the parent. This closes
the retention gap that motivated this recovery.

Publication is inactive: the operation does not update `active`,
`toolchain-active`, box-control selection, service state or application runtime.

## Live execution owned by Work

Regular implementation cannot produce the actual derived generation ID because the
operation must reopen the retained parent bytes on the compiler host.

After this source revision is independently reviewed/deployed, Work may run the
finite local operation against the exact existing image-build state directory:

```
python -m zog.image_build.accepted_image_derivation \
  --state-dir <protected-existing-image-build-state> \
  --operation-name certify-manage-runtime-recovery-2026-10-22 \
  --source-revision <exact-reviewed-image-build-commit>
```

No AWS, network, package download, compiler execution or package catalogue is needed
by the derivation itself.

Work must retain and review:

1. parent generation/readback identity;
2. exact parent manifest SHA256 and 40,945-entry count;
3. frozen intent and explicit 54-component provenance gap;
4. acceptance record and exact added-directory list/modes;
5. new generation ID/manifest SHA/inventory count;
6. unchanged ABI descriptor;
7. immutable-object protection report for both parent and new generation;
8. idempotent rerun result;
9. negative test showing a changed parent/source/profile is rejected.

Only after that evidence exists should certify-manage/host-deploy decide whether the
new inactive generation is acceptable for issuer-rootfs/application admission.

# Immutable artifacts and generations

## Four immutable object classes

Image-build publishes separate classes of objects: **rootfs generations**, **remote recipe snapshots**, **application-software artifacts**, and **application-software views**. They have different production and recovery rules, even when all are content-addressed. Rootfs generations supply read-only system software. Application artifacts supply installed runtime application bytes. Views compose existing artifacts without copying or overwriting them. Persistent databases, credentials and writable application data belong to controller-owned state, not any immutable software store.

## Publication is an identity-bearing transaction

The producer freezes an exact manifest and relevant inventory before an atomic transition into the published namespace. Publishing a candidate is not the same as preparing it; an incomplete candidate is never a published identity. If the response is lost **after** publication, a retry verifies the exact existing object and returns its same ID, rather than creating a substitute.

Recovery depends on where the unique bytes still live:

| Object | Unpublished candidate after interruption |
|---|---|
| Rootfs generation | Reuse exact valid staging; rebuild partial staging only from bound source root; conflicting valid staging is an integrity fault |
| Remote recipe snapshot | Rematerialize from the exact frozen request, source revision and monthly pin |
| Application software artifact | Resume an intact frozen candidate; **fail closed** on corruption, because those installed bytes may be the only exact copy |
| Application software view | Recompose deterministic symlink output from the frozen manifest and exact retained artifact IDs |

See [immutable publication and recovery](../publication-recovery.md) for exact on-disk paths and fault-injection coverage.

## Application staging and software views

The explicit `ApplicationSoftwareStore.begin()` operation supplies an installation staging root. Only runtime material **installed within that root** can be published: executable entry points, runtime Python/Django dependencies, compiled frontend assets, immutable defaults and notices. Build-only caches, frontend source trees, mutable secrets and databases do not belong in the artifact. Publication validates inventory, compatibility and required notices and binds the frozen result to the durable operation.

`ApplicationSoftwareViewStore` deterministically combines referenced `applications-v1` artifacts into a separate `application-software-view-v1` identity. Every path has one owner; incompatible directory modes or file/symlink/parent collisions fail rather than introducing layer precedence. Published views consist of directories and deterministic symlinks to read-only artifacts under `/applications/.store/<artifact-hex>/`; the consumer sees conventional `/applications/<application>/` paths **without OverlayFS**.

Before exporting `application-software-consumer-v1`, image-build checks the entire view, every artifact and selected rootfs compatibility. Box-control then consumes a verified fixed binding without invoking image-build at runtime. See [application software and views](../application-software-artifacts.md).

## References are not deletion authorization

The read-only `zog.image_build.immutable_objects` inspection reports classes of `protected`, `referenced`, `apparently-unreferenced` or `unknown` based on image-build-local evidence. Unreadable referencing state makes `reference_complete=false` and prevents an otherwise unprotected object from being labeled an apparent candidate. A retained view protects all its referenced artifacts.

**Every report states `reclamation_authorized: false`.** Image-build cannot independently see all box-control runtimes, prepared operations, pending cleanup or host-deploy/station-access dependencies. Even an apparently unreferenced object is not safe to delete without external protection reconciliation and explicit owner policy.

## Reference contracts

- [Software artifact, view and consumer manifests](../application-software-artifacts.md)
- [Recovery rules for the four object stores](../publication-recovery.md)
- [Read-only immutable reference report](../immutable-objects.md)
- [Rootfs payload path and inventory semantics](../payload-paths.md)

This chapter is a synthesis, not an authorization to reclaim data or mutate running applications.

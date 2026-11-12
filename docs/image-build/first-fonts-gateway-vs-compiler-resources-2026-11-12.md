# First Fonts separation of responsibilities — November 12, 2026

**PR #17: PREPARED_NOT_SUBMITTABLE.** This is an exact source-preparation reference, not a native resource admission or GitHub-triggering issue.

## Gateway — install small catalogue only

Selected host-deploy PR #7 commit `277da9174f633d09c792dce595ff76ab1e6a0298` removes all local resource-inspection callbacks and actual reservation arguments from `graphics_catalogue_owner.prepare` and `install_native`. The trusted gateway `host-registry` writes only the small, immutable, root-owned Fonts catalogue and receipt at `/var/lib/zog/fonts`, using the exact reviewed accepted compiler identity, retained input evidence and checksum. No 32 GiB free-space, directory project quota, XFS filesystem, separate storage disk, EBS partition, loop image or S3 authority is required on `host-registry`.

The immutable 30 GiB work + 2 GiB external and six-hour limits remain the **compiler-task policy**, not a local catalogue install capacity assertion. The installed receipt states `resource_admission_location=compiler-host-before-build` and `compiler_resource_admitted=false`.

## Compiler Host — inspect actual build resources

The separate `fonts_resource_admission` module is available as a **compiler-Host-local** inspection contract; it must never be called by the gateway installer. Work must bind actual compiler Host identity and inspect its current free capacity, writable mount roots, enforced quotas or independently reviewed equivalent resource bounds, and 21,600-second deadline before starting the build. The existing XFS project-quota reader supports only an already configured compiler XFS filesystem. For ext4/no project quota or inadequate native evidence, remain HOLD and review a compiler-side enforcement alternative; never resize or reconfigure `host-registry` to satisfy compiler storage.

At present, source checks do **not** establish a live image-build preallocation gate consuming this native observation, so Work must validate this boundary before authorizing a real job. A successful gateway catalogue install cannot imply runtime resource admission.

## Exact frozen source and CI

- Original image-build producer `1f07e83dbd80dacb9bed0d6494c697375f0e26cd`, immutable October source pin `d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`.
- Independent compiler-purpose reader PR #20 `1616f192ef9d8964a8f37f32a86c69c0242a213c`, compiler consumer PR #29 `b3ac93cd92df1b280f087fbb748263d3371750aa`.
- Host-deploy PR #7 source selection `277da9174f633d09c792dce595ff76ab1e6a0298`; compiler catalogue owner Git blob `da84649531c2b69a5f961eefeb21a3276eaeed39`. Resource reader Git blob remains separately frozen `7c8820b3f7685d83ad6a3e31fd43a0b7341fad5b`.
- [PR #7 source checks](https://github.com/zog144/host-deploy/actions/runs/43224436137): 119 source + 3 disposable root tests PASS on Python 3.12 and 3.13.
- [PR #17 source checks](https://github.com/zog144/image-build/actions/runs/43224658208): 70 PASS. [Public source checks](https://github.com/zog144/image-build/actions/runs/43224658240): PASS.

No native Host, filesystem, quota, gateway service, AWS credentials, IAM, SQS, SSM or compiler state was modified. No original GitHub issue or compiler job was created.

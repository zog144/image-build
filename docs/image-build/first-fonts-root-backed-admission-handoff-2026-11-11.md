# First Fonts exact source and ordinary root-backed admission handoff — 2026-11-11

**Result: SOURCE PREPARATION PASS; NATIVE INSTALLATION AND DISPATCH NOT AUTHORIZED.**

## Frozen producer, consumer and first task

- Original selected image-build producer: `1f07e83dbd80dacb9bed0d6494c697375f0e26cd` and immutable October source pin `sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`.
- Image-build compiler-purpose native reader PR #20: `1616f192ef9d8964a8f37f32a86c69c0242a213c`; genuinely independently observed isolation and preserved original base `kind=image` or `kind=toolchain`, not fabricated stage-two provenance.
- Independent host-deploy PR #29 compiler-base consumer: `b3ac93cd92df1b280f087fbb748263d3371750aa`; `graphics_base_acceptance.py` must match this source byte-for-byte.
- Host-deploy PR #7 exact first-Fonts candidate: `ee4a3d58077fac8a578e1c4f96540e1999a9d1ba`; independent exact Git blob owner pin `b2148a30bc1a7b074468e463cb9fab1e9abe4ce1`, with native resource module and root-only catalogue installation.
- Trusted-Host Task C PR #30 selected source: `0fd2db17698423d4cd30b296fc9f78e83cee145c`, using original issue → FIFO SQS → trusted Host IAM → fixed SSM document and local durable no-retry intent. No signed Task C owner/installation approval, independent S3 checkpoint, broker, new role, extra EBS or automatic retry required.

The catalogue has **one** `graphics-fonts-image-v1` operation: libpng → FreeType → Fontconfig; original source archives/hashes, rights declarations and predecessor contracts unchanged. The complete accepted compiler-base receipt identity is frozen into the catalogue's `retained_acceptance_sha256`; the catalogue and gateway preparation remain separate from actual job authorization.

## Native resource admission

Host-deploy now stages the one-shot root-owned catalogue and receipt in `/var/lib/zog/fonts` (0600, O_EXCL, fsync), rather than an image-backed state volume. Work must select the actual Host/installation/managed lane, installed reader and accepted input generation before populating the ordinary root-owned local approval file and installing the exact catalogue.

The new `zog-fonts-root-backed-resource-admission-v1` requires **two distinct kernel-enforced directory project quotas** under the existing root filesystem: `/var/lib/zog/fonts/work` capped at 30 GiB and `/var/lib/zog/fonts/external` capped at 2 GiB. Native `inspect_native()` reads actual XFS quota hard limits and project inheritance, same root device, root directory ownership and current capacity; it requires genuine worker writable path observations and an enforced **21,600-second** runtime deadline. The source supports **XFS with active enforced project quotas only**, and requires at least 32 GiB currently available. If the selected Host filesystem is ext4, XFS project quotas are unavailable, the directories are not yet configured, or writable worker mounts escape those roots, admission must remain HOLD. Do not create EBS disks, loopback files, new partitions, S3 or signing systems as a workaround.

A quota is a hard upper bound, **not an exclusive physical reservation against unrelated Host writes**. Free-space inspection is point-in-time evidence; Work must evaluate actual shared-root headroom and worker occupancy before claiming operational readiness. Neither the source verifier nor a JSON `native_quota_observed=true` field authorizes anything.

## Exact source evidence and remaining Work

- PR #7: [source workflow #43114073762](https://github.com/zog144/host-deploy/actions/runs/43114073762) — 119 PASS plus 2 disposable root tests on each Python 3.12/3.13 lane.
- PR #17: [offline preparation #43115012446](https://github.com/zog144/image-build/actions/runs/43115012446) — 69 PASS; no original issue, SQS SendMessage, SSM SendCommand or compilation.

Before native catalogue installation, Work must authenticate the original compiler generation/issuer/probe and Host/installation/STATE, actual root filesystem and project quotas, fully observed worker writable roots, root-owned approval and exact catalogue digest, source and notice retention, GitHub actor/allowlist, existing shared-Host IAM/SSM target, and durable single-attempt/reboot handling. Work should install and validate these selected bytes with the existing ordinary host-install path, **without activating the one-task compilation until separately authorized**. The PR #17 JSON retains `PREPARED_NOT_SUBMITTABLE`, all native gate entries `null`, and no issue/request/queue/result identities.

**No AWS, IAM, STATE, filesystem quota, catalogue installation, SQS/SSM or compiler job was changed or started in this source review.**

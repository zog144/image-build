# First Fonts GitHub preparation — 2026-11-06 historical review, superseded 2026-11-11

**Current status: PREPARED_NOT_SUBMITTABLE.** The former protected-owner/S3/dual-SSM-path installation requirements described in the earlier November 6 review have been superseded by the trusted-Host Task C decision on November 11.

The authoritative current **source-only** handoff is [First Fonts trusted-Host Task C reconciliation — 2026-11-11](first-fonts-trusted-host-task-c-reconciliation-2026-11-11.md). Follow its exact current immutable selections and gate list, not the historical v3 owner/broker or S3 design.

Original image-build compiler producer: `1f07e83dbd80dacb9bed0d6494c697375f0e26cd`. October pin: `sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`. Both unchanged.

Selected compiler-purpose reader PR20: `1616f192ef9d8964a8f37f32a86c69c0242a213c`. Shared consumer PR29: `b3ac93cd92df1b280f087fbb748263d3371750aa`. Reviewed first-Fonts-only catalogue PR7: `84cc8812ff027a40e849099023263075a2565bc4`. Trusted-Host Task C source PR30: `0fd2db17698423d4cd30b296fc9f78e83cee145c`.

The retained compiler `kind=image` and historical-provenance gaps remain unchanged; a separately accepted `kind=toolchain` is also valid. The new catalogue passes the exact independently checked compiler-purpose receipt SHA as `arguments.compiler_base`. The original recipe/notice rights declarations remain unapproved for public redistribution. The 30+2 GiB / six-hour bound remains a **Fonts worker** constraint, implementable through the reviewed root-backed quota approach, not an extra disk, S3 authority or installation signature for Task C.

**Native Work still must independently establish** current image and signed compiler evidence, installed reader and catalogue, managed Host/lane, native quota/time enforcement and actual trusted-Host SSM/IAM/FIFO admission. No issue, SQS request, SSM command, compiler job or output image is authorized by the source-only review.

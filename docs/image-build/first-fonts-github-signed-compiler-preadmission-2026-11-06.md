# First Fonts GitHub-trigger preparation — signed compiler and protected-owner reconciliation, 2026-11-06

**Status: PREPARED_NOT_SUBMITTABLE. Source-only contract reviewed, never an executable issue or accepted catalogue.**

## Exact selected source and separate roles

- Producer compiler/original Fonts sources: `zog144/image-build@1f07e83dbd80dacb9bed0d6494c697375f0e26cd`, `project/bootstrap/graphics-fonts.py`, original October source pin `sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`.
- Reviewed host-deploy PR #7 one-task definition: `745cb7e887fabcea06caf1d7db732b33f9dadca0`, source-only, root-installed catalogue not yet present.
- Reviewed protected Task C gateway PR #26 source: `02db124609b92396ff89fa628d8ddc9383e05f4b`, source-only, native owner not accepted.
- Independently reviewed image-build PR #18 signed dual-kind compiler reader: **`bf0b37fea1767bf7ab02ca2d1c5d1a0d5487d4b6` (40 hexadecimal characters)**. This is separate from the original producer commit; it is not installed solely because source CI checked it out.

The updated `first-fonts-github-preparation-v1.json` retains `status=PREPARED_NOT_SUBMITTABLE`, no original issue/workspace/request/queue acknowledgement or generation ID, zero installed catalogue/receipt and all native gate values `null`. It names the current reviewer commits and the signed reader, rather than the earlier PR7 `78a772a...` / Task C `c46c6b...` and superseded stage-two-only assumption. The old preparation audit remains historical evidence, not a current installed source pin.

## Task, dependencies and rights

One-task schema-2 Fonts only; fixed sorted entries `fontconfig-final`, `freetype-final`, `libpng-final`, execution targets **libpng → FreeType → Fontconfig**. Verified against original plan and individual original archive/recipe dependencies and test/install declarations.

Original source archives:
- libpng 1.6.58, `28eb403f51f0f7405249132cecfe82ea5c0ef97f1b32c5a65828814ae0d34775`.
- FreeType 2.14.3, `36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f`.
- Fontconfig 2.18.3, `4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3`.

Only selected packages are in the first task; zlib/bzip2/Expat/gperf, compiler, make, pkgconf, Meson/Ninja and other inherited capability inputs must be independently authenticated from the selected Host generation. FreeType intentionally excludes HarfBuzz and Brotli; full configured Fontconfig `make check`, FreeType smoke test, original notices and bounded DESTDIR install remain part of the recipe contract. The three exact `license.py` records are `declared` with unresolved per-component reviews; archive/notice hashes are frozen, but this does **not** establish public redistribution clearance. Releasing artifacts requires separate corresponding-source/notice and ownership evidence.

The accepted first input may retain its original **`kind=image` or `kind=toolchain`**, but only after independently pinned Ed25519 acceptance, exact compiler/linker/header/libc/inventory/manifests, real native isolation/probe, Host/installation/STATE and documented historical gaps; no inferred stage-two history or synthetic acceptance. Subsequent image outputs use their separate graphical predecessor acceptance.

## Dispatch and IAM review

The source contract is an original authorized `issues.opened` event on `zog144/host-deploy`, configured reviewed checkout/actor/operation, first run attempt only, GitHub OIDC role only on the submit job, a single SDK attempt to FIFO SQS with `MessageGroupId=workspace_id` and `MessageDeduplicationId=request_id`. The issue provides typed intent, **not** server-owned GitHub `origin`, SSM target or command. No retry is authorized after unknown acknowledgement. Existing protected Task C executes each preflight and stage exclusively through separate root-owner claims, with read-only `observe-original`; source tests are not native IAM-denial proof.

**Actual AWS permission check is NOT established by GitHub source.** Work must independently inspect the effective OIDC role trust condition, role and queue account/region, FIFO queue policy, `sqs:SendMessage` scope, dispatcher receive/delete/visibility/attributes, the protected owner-exclusive SSM sender, separate read-only S3 checkpoint role and true gateway principal's denied direct SSM/STS/PassRole/IMDS/secret paths. A shared-Host instance profile with SSM permissions must not be mistaken for process-isolated gateway denial.

## Execution and resource hold

Bounded dedicated reservation remains exactly 30 GiB work image + 2 GiB external accounting = 32 GiB; execution limit 21,600 seconds. Dedicated bounds do not imply all shared-host PID1/journal/SSM/cron/external writes are accounted; independent native overall budget checks remain required. No actual accepted compiler image, one-task protected catalogue SHA, Host/STATE/managed lane, operator approval, installed protected owner, non-rollbackable S3 checkpoint or IAM proof is supplied by this record.

**Next owner:** host-deploy/root-control/host-install Work independently accept original authority, protected issuer and current history, installed source, actual IAM and environment and independently sign/install the exact one-task catalogue. Only then may a separately authorized original GitHub issue be opened for one FIFO/owner-triggered Fonts compilation. No manual direct-SSM workaround, retry after uncertain ACK, or candidate promotion.

**No native operations, EC2/STATE modifications, AWS/SQS/SSM requests, GitHub issue creation, actual compilation or source promotion occurred here.**

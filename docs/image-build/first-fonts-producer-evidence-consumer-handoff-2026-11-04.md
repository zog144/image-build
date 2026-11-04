# First Fonts producer evidence and host-deploy consumer contract — 2026-11-04

**Status: source-only candidate; native compiler and generation acceptance NO-GO.**

## Exact ownership boundary

The original selected compiler *producer* source remains image-build `1f07e83dbd80dacb9bed0d6494c697375f0e26cd`, with original October pin `sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`. The reviewed first task is `graphics-fonts-image-v1`. Its exact canonical source plan `project/bootstrap/graphics-fonts.py` uses **libpng-final → freetype-final → fontconfig-final**, and those are the only targets. The alphabetically sorted root-owned schema-2 host-deploy task catalogue is a *consumer* and must be implemented by **host-deploy Regular** separately.

This *candidate source extension* is intentionally on top of the original `unstable` producer source, with no modified original recipe/pin, no selected source repin, and no installed command. It provides a read-only producer evidence adapter `src/zog/image_build/first_fonts_producer_contract.py`.

Before the first Fonts compilation, `source_plan(repository_root)` checks original pin file **bytes**, plan stage order, x86_64 and target selection. `observe_base(builder, repository_root, selected_generation_id)` requires a real, existing, non-symlink canonical image-build generation directory and reopens `manifest.json` and installed tree with the existing `engine.read_selection`. It rejects **kind=image**, stage 0/1, non-self-hosted or wrong-generation manifests. For stage-2 `kind=toolchain`, it requires the existing canonical `build_record` generation-root pointer and calls `generation_provenance.verify` to validate actual provenance records, package ancestry, installed verification and source/inventory bytes. It re-reads the manifest after verification and rejects changes. The pure adapter returns a *local observation*, never a claim of separately accepted Host/installation authority.

## Producer base evidence to be consumed after native protection

`image-build-first-fonts-base-observation-v1` fields:

| Field | Producer evidence source |
| --- | --- |
| `task`, `source_repository`, `source_revision`, `monthly_pin_identity` | Exact immutable producer plan and original October pin bytes; not issue-selected |
| `host_id`, `project_id` | Existing image-build canonical Provenance owner, **not independently an installation identity** |
| `base_generation_id`, `base_generation_kind`, `base_generation_stage` | Reopened canonical generation directory, `kind=toolchain`, stage 2, self-hosted |
| `base_manifest_sha256` | Digest of exact re-opened on-disk generation `manifest.json` bytes |
| `base_inventory_sha256` | `sha256:` + `metadata.identity(manifest.outputs)`; actual installed inventory checked by `read_selection` |
| `base_generation_record_sha256` | Existing canonical Build Record generation root pointer; checked by `generation_provenance.verify` |
| `status` | Exactly `canonical-base-observed-not-native-admission` |
| `catalogue_installed`, `native_compiler_authorized` | Both **false**; this producer cannot confer either authority |

**The consumer must never use a plausible 64-hex ID or these observations in isolation as an accepted generation.** Work must separately prove protected current Host/installation/boot, managed schema-4 lane, exact selected compiler software/source pin, original operator approval, true 30+2 GiB/21,600-second worker, independently nonrollbackable claim/checkpoint, root-control owned preflight and stage SSM, and actual gateway IAM denial. Only host-deploy's root-installed one-task catalogue/receipt and separate operator authorization can allow a new original GitHub issue-opened SQS submission. No manual direct SSM or retry on uncertain ACK.

## Successful output

After an authorized native one-shot compiler operation, `verify_fonts_output(...)` calls the **existing** `graphical_generation_acceptance.verify` (no second, weaker attester). It requires the independently observed canonical stage-two input again, identical source/pin/host and the original Fonts task. Existing producer verification must reopen original snapshot/submit/inspect records, request/pipeline identities, source/receipt/pin, completed on-disk pipeline and attempts, immutable output `kind=image`, original generation manifest/inventory, build-record generation root, installed verification and producer remote-result bytes. Only then can it return the existing `image-build-verified-graphical-predecessor-v1` success evidence. Its existing `acceptance_receipt_sha256` is the verified Build Record generation-root record ID, not a new invented receipt; `producer_receipt_sha256` is the raw completed original remote result SHA.

A real original operation that fails/has a lost acknowledgement must preserve its original gateway request, pipeline ID, durable pending state, SSM command/uncertainty, build-record and output artifacts; it is **not** a new request with a fabricated failed generation or permission to retry.

## Source review and native holds

The source-only CI tests canonical original pin/targets, stage-0/1 `kind=toolchain` and `kind=image` denial, missing/wrong source or provenance, changed on-disk manifest after checking, invented generation/receipt and nonroot refusal. It also reruns existing canonical graphical output producer tests on synthetic local records; synthetic fixtures are **not accepted native toolchains**. This branch adds no AWS/SSM/issue/SQS/daemon call. The native wrapper requires EUID root, but root EUID alone is insufficient authentication; the installed native reader/Host/STATE/pins must be attested independently.

**Source selection caveat:** this new module is not present in the already selected image-build commit `1f07e83d...`. A future protected reader using this code needs an independently reviewed exact *reader source* installation and authorization. Do not silently repin the existing protected compiler task catalogue or claim a native GO because source CI passes.

**Next:** host-deploy Regular implements the fixed catalogue consumer for `image-build-first-fonts-base-observation-v1` and binds it only to its separately protected Host/installation/native acceptance; Work performs independently authenticated installed-host acceptance **before** any first Fonts issue/SQS/SSM submission.

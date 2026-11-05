# Compiler-base acceptance for Fonts and subsequent graphical batches — 2026-11-05

**Source implementation in image-build PR #18, not a native admission, compiler job or historical reconstruction.**

## Decision: preserve both generation kinds

The compiler base is **not synonymous with `kind=toolchain`**. Two immutable kinds can be used:

1. An originally accepted **stage-two self-hosted `kind=toolchain`**, with the complete original canonical generation-root Build Record and installed verification.
2. An independently accepted **`kind=image` containing a working compiler**, with independently witnessed current compilation/linkage and an explicit historical-provenance gap. It remains `kind=image`; no stage-two build or missing predecessor is fabricated or relabelled.

Both paths require one authenticated native `image-build-compiler-base-acceptance-v1` Ed25519 receipt and exact protected issuer selection. The source-only read of a `kind=image` manifest, a 64-hex generation ID, an archive SHA-256, a locally forged signing key or a completed one-off test is never sufficient. Original toolchain Build Record closure is verified when genuinely present. For compiler-bearing images, the signed historical record requires `status=historical-gap-declared`, nonempty specific missing facts and a separately retained review-evidence digest. No native capability probe repairs that history.

## Selected protected receipt

The root-controlled installation owner, **not a remote pipeline request**, installs a root:root mode-0600 policy and a protected root-owned receipt directory. The trusted policy binds `host_id`, `installation_id`, `state_volume_id`, `project_id`, Ed25519 issuer `key_id` and public key, and SHA-256 of the exact box-control execution configuration. Work must independently verify this policy's original Host/STATE authority, issuer revocation, installation provenance, mount identity and ownership; root ownership of a file alone is not the full authorization.

The signed receipt is addressed by the *original selected generation ID* and its exact bytes' SHA-256 is the only `compiler_base` value permitted in the remote request. It contains the exact original generation kind, manifest digest, installed inventory digest, optional genuine Build Record generation-root digest, selected compiler target ABI, original external Host/STATE and execution environment, installed-byte paths + SHA-256 for `usr/bin/gcc`, `usr/bin/ld`, `usr/bin/as`, `usr/include/stdio.h`, the selected ABI header, CRT/startup object and libc/linker inputs, and a bounded native capability witness. Actual bytes are reopened from the immutable selected image root and hashed; traversal/symlink escape and changing manifests are rejected. Linker and header traces must name those same selected installed paths rather than foreign Host paths. This consumer does not authorize a job.

**Protected native probe:** `compiler_base_probe.execute_native_probe` has no `subprocess` or direct SSM fallback. It selects an explicit one-off box-control job with a **120-second** cap, read-only pivot-root sandbox and no network. The source is a fixed `stdio.h` C program compiled, linked and executed, with object/ELF checks, compiler `-dumpmachine` target check, header include-search and `-Wl,-t` library linker traces. The inspector refuses empty/oversized, Host-root/`/usr/local` paths or wrong ABI, but returns only **`observed-not-accepted`**. An independent native owner must establish actual box-control credential provenance, signed controller completion, a real elapsed monotonic clock, genuine mount isolation, original log bytes and policy before issuing the final accepted receipt. A signed or synthetic `status=passed` witness in tests is **not real native evidence**.

## Actual production path — not an observation-only extension

The new `compiler_base` field is wired into each of the executable paths below:

| Path | Contract enforcement |
| --- | --- |
| `RemoteOperations._pipeline_arguments` | Requires exact original protected receipt SHA for selected Fonts/XCB/X11 requests at the original producer revision and for every `kind=image` compiler base. Reopens signed original selected generation and rejects wrong mode, stale signer, unrecognized task, or unaccepted image. |
| `PipelineMixin._prepare_pipeline` | Validates the selected receipt **before durable pipeline allocation**, freezes its SHA in original pipeline arguments and pins current protected issuer identity in the execution policy. |
| `PipelineMixin._continue_pipeline` | Carries the exact frozen receipt into `ImageBuild._ensure` during resume/recovery; the previous command attempt and pipeline are retained. |
| `ImageBuild._ensure` / `_build_set` | Verifies native acceptance again before building and after package execution; binds exact verified compiler metadata to **every package input** and immutable generation input. The selected original image tree provides the disposable build root, without relabelling. Missing receipt or changed generation refuses compilation. |
| `graphical_composition.validate` | Treats the compiler base and package predecessor as **different inputs**. A separately accepted image compiler may build XCB/X11 only with separately verified immutable Fonts/XCB image ancestors. It never turns those package images or the compiler image into a toolchain. |
| `graphical_generation_acceptance.verify` / `first_fonts_producer_contract.verify_fonts_output` | Version-two trusted context requires the original `compiler_base` SHA and independently reopens that signed receipt. The retained `recipes.snapshot`, original `pipeline.submit` request, pipeline arguments, generation inputs, build-record root, installed verification, completed attempts and completed producer remote-result bytes must agree before existing `image-build-verified-graphical-predecessor-v1` output evidence may be returned. |
| Native CLI | `remote_operations` and graphical attester accept an *opt-in* `--compiler-base-authority` pointing to the installed root-protected issuer, alongside their existing selected controller configuration and original provenance owner. A source-only fixture or issue JSON cannot supply this policy. |

The existing legacy stage-two path for unrelated image builds is not implicitly repinned; **first graphical tasks from the exact original producer and all compiler-bearing image selections are gated**. An older graphical attestation context (v1) can still inspect historical outputs; a new completed Fonts result must use the protected v2 context. Host-deploy Regular must consume the **signed source-binding and actual compiler certificate**, not extrapolate permission from the earlier stage-two-only observation. It must independently pin the new reader source revision and root-owned catalogue; the selected old producer `1f07e83d...` does **not** contain these new changes.

## Downstream inheritance remains independent

Compiler-base acceptance is a distinct durable input from the Fonts/XCB/X11 package ancestry. For each graphical batch, source graph checks and native package receipts still independently prove selected generation, installed output manifest, original source/notice rights and the inherited base images. The actual original `toolchain`/compiler-image kind is preserved forever; an accepted compiler image does not need to be rebuilt as `kind=toolchain`, nor does its historical Build Record become magically complete.

## Separate security hold: host-welcome observer

The prior read-only host-welcome progress observer pins the **original** 14 security-critical module blob identities, including `engine.py` and `graphical_composition.py`. This compiler branch changes both files. It deliberately **does not modify the old `MODULE_BLOBS` allowlist or source revision**, and `reviewed_source_inventory` therefore continues to **deny using the changed candidate as the old observer source**. The source CI regression explicitly asserts this denial; observer owners must separately review and select an exact successor source before native deployment. This CI behavior is not an observer authorization.

## Native Work requirements

Native acceptance must independently prove the exact compiler Host/installation, source and selected reader executable, installed Ed25519 issuer and original grant, STATE identity, immutable generation bytes and real toolchain provenance or explicit historical gaps, bounded isolated compiler probe and linker/header origins, selected native ABI, one-task Fonts catalogue, signed operator authority, 30+2 GiB and six-hour bounds, installed protected Task C SSM owner with external nonrollbackable checkpoint, gateway IAM denial, one original GitHub issue-opened FIFO request and no retry after uncertain acknowledgement. Source tests cannot establish any of these native facts.

**Disposition:** the dual-kind compiler-base producer/selection/execution/output source candidate is reviewable; **no native compiler base, Fonts compilation or generation is newly accepted by this PR.**

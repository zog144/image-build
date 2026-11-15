# Resident B — original compiler receipt and corrected Boot A native inputs

The existing 29-stage source DAG and compatible 3.12 controller pins in PR #24
remain unchanged. The source-selected Boot A `273de2a0…` predecessor is
**historical**: the next Resident B must not silently inherit it after PR #25
publishes its corrected getty/account-aware Boot A successor.

## Source-side native evidence selection

`project/host/resident-b-consolidated-source-selection-v1.json` includes the
separate `native_admission` contract. This pins the *reported* retained
compiler-base generation `3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc`
and original protected receipt digest
`sha256:a205c07bde4e6cf61e48061affd9a0b40c3a101e18dff67a9871995a3a2afafc`.
Those strings are **expected identities**, not authenticated native evidence.
The original compiler Project and lane, installed authority and execution
configuration must be independently reopened.

The selected compiler acceptance reader is the existing
`compiler_base_acceptance.resolve` source reviewed at image-build PR #20
`1616f192ef9d8964a8f37f32a86c69c0242a213c`, exact source blob
`3eb562bbf2460fb95af0780a079cb2b058650f80`. It validates the original
canonical signed Ed25519 compiler-purpose receipt, protected issuer authority,
Host/Project/installation identity, original compiler generation, pinned ABI,
installed GCC/linker/library bytes, isolated probe and real runner configuration.
It must be installed/combined in the native source environment; PR #24's
source branch does not independently duplicate the protected reader. A
missing or different reader is a refusal, never a fallback to a request claim.

The `corrected_predecessor` fields stay `null` until a **different** Boot A
generation from PR #25 is actually published and independently verified by
image-build Work. Its exact generation, producer revision, canonical
`manifest.json` digest, Build Record rootfs archive SHA-256 and canonical
installed package-receipts digest must be updated *together* in a reviewed
source-selection revision. The old `native_input` record is preserved as
historical, not relabeled. Source CI rejects fake native permission or
invented predecessor bytes.

## Read-only Work admission

Once the corrected generation and original compiler reader have been installed,
the source implementation `tools/plan_resident_b_native_admission.py` accepts
explicit local paths for the retained compiler Project, corrected-predecessor
Project, protected compiler issuer policy, original controller configuration,
and exact reviewed materialized 29-stage recipe directory. It has no
default Project path, no user override and no Host mutation operation.

The operation first calls the existing protected compiler-base reader's
`resolve()` with the pinned signed receipt and actual selected generation.
It then reopens the new Boot A `kind=image` generation with
`read_selection` and `generation_provenance.verify`, independently hashing
the actual canonical archive, manifest and package receipt set. Both input
generations remain distinct and no prior receipt hash is reused.

For every source stage, a package is considered **present** only if its
selected source-recipe fingerprint, integration metadata, retained package
provenance, required outputs, and exact installed inventory records match an
independently verified predecessor or accepted compiler root. A matching
filename alone never counts. Missing, ambiguous, legacy or mismatched outputs
remain **missing or needing recompilation**. This read-only plan does not
compile stages or grant compilation. Any new binaries, Python 3.12/3.15
ABI closure, installed ELF and wheel RECORD, rights, privilege, STATE and
controller acceptance remain separate native operations.

The source selection declares `native_build_permitted=false`,
`package_binary_closure_verified=false` and
`service_activation_permitted=false`. These flags are never promoted by the
source checker or the read-only plan. The corrected rootfs must be verified
without changing prior Boot A generations, source receipts or historical
compiler records.

## Required native handoff

1. Publish the corrected PR #25 successor only after its account-materialized
   rootfs and canonical archive pass publisher verification and disposable
   boot acceptance.
2. Independently reauthenticate the original compiler receipt with the
   exact protected installed policy, source reader and original Project.
3. Update and review all corrected predecessor source pins together. Record
   actual archive, manifest and package receipts, never null-to-guessed data.
4. Materialize exactly the reviewed 29-stage recipe selection, run the
   read-only native admission, then build **only missing** packages via
   separately authorized native execution. Verify complete installed
   ELF/wheel/ABI and controller-runtime closure before any Resident B release.

No certificate issuance, S3 approval, spare compiler users, native build or
rootfs mutation is part of this source change.

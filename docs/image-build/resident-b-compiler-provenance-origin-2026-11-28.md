# Resident B original compiler provenance — reviewed reader and operation HOLD

## Scope and immutable historical evidence

This stacked source change does not rewrite Resident B PR #24's original selection:
project_id remains null, authenticated remains false, and no operation ID is
invented. The original signed compiler capability receipt, Build Record and
Oct 11 rootfs are immutable. This source supplies the exact reviewed PR #20
reader from source revision 1616f192ef9d8964a8f37f32a86c69c0242a213c.

Reviewed source-file Git blobs:

| Module | Original Git blob |
| --- | --- |
| compiler_base_acceptance.py | 3eb562bbf2460fb95af0780a079cb2b058650f80 |
| compiler_base_isolation.py | 210a3f81b5796db66a8798ce9d172669e1cf8814 |
| compiler_base_probe.py | 32c36d01d36453df20867945d7535ea117cad774 |

Original generation: 3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc (kind=image).
Original signed receipt: sha256:a205c07bde4e6cf61e48061affd9a0b40c3a101e18dff67a9871995a3a2afafc.

The PR #20 reader authenticates the protected Ed25519 issuer policy,
Host/installation/STATE/Project identity, original generation manifest,
inventory, Build Record pointer, seven installed compiler role hashes,
controller configuration, and constrained native probe. The source bundle
does NOT enroll an issuer, sign, publish, reissue or promote a receipt.

The original Build Record reportedly identifies logical Project
zog-compiler-view and assembly attempt
attempt:application-image-facilities-oct11-assembly. The local selected
Project directory, logical Build Record Project, and an operation ID are
separate concepts. Neither logical Project nor attempt identifies an
authoritative remote submission. Work's historical receipt verification
did not establish the old operation; do not derive it from a filename.

## Read-only native Work procedure

Install and attest the exact three reviewed modules and dependencies,
select the existing original Project and its protected compiler authority,
and run the auditor in the authorized native environment (paths below
are parameters, NOT new Projects or accounts):

~~~
/usr/bin/python3.12 -I tools/trace_resident_b_compiler_provenance.py \
  --compiler-project ORIGINAL_SELECTED_PROJECT \
  --compiler-state ORIGINAL_SELECTED_PROJECT_STATE \
  --authority PROTECTED_COMPILER_PURPOSE_POLICY \
  --controller-config ORIGINAL_AUTHENTICATED_CONTROLLER_CONFIG
~~~

The audit opens the canonical generation and immutable Build Record
read-only, binds the Project ID against the signed reader's authority and
the canonical source provenance, then traces any original operation only
through all of these retained links:

1. exact assembly attempt and its immutable generation pointer;
2. uniquely linked completed pipeline with the same generation and attempt;
3. matching pipeline owner and frozen original remote request;
4. matching durable pipeline binding and successful terminal remote result.

Expected source paths under selected original STATE:
- image-build/attempts/ORIGINAL_ATTEMPT/assembly/generation.json
- image-build/pipelines/ORIGINAL_PIPELINE/pipeline.json
- image-build/remote-operations/ORIGINAL_OPERATION/request.json
- image-build/remote-operations/ORIGINAL_OPERATION/binding.json
- image-build/remote-operations/ORIGINAL_OPERATION/result.json

Every path, ID and revision must be read from original source records.
If the original operation/pipeline chain is not retained, the result is
HISTORICAL_OPERATION_UNRESOLVED with a null operation ID. Tampering,
duplicate claims, foreign Project or contradictory terminal state are
refused. The auditor performs no job submission, filesystem repair,
receipt issuance, authority modification, rootfs publication or service
activation. Source tests are synthetic; native installed reader and
protected policy still require independent Work attestation.

## Successor selection if historical operation is unavailable

The separately documented
project/host/resident-b-compiler-provenance-successor-v1.json is
HISTORICAL_OPERATION_UNRESOLVED_NATIVE_HOLD. If no authoritative
historical operation record exists, obtain a distinct, expressly
authorized compiler producer operation/generation with its own
source/Project/record/receipt binding, then review its selection. Never
retrofit the original generation with an invented operation, sign a new
receipt as if it were the original, or replay the old attempt.

Resident B's unchanged PR #24 original source selection is still held
until a real Project and operation are proven. Boot A's corrected
generation and canonical installed package receipts remain an independent
prerequisite to the 29-stage package present/missing comparison.

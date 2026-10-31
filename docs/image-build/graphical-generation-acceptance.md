# Graphical generation acceptance attester

The graphical predecessor attester is a read-only producer capability for the
finite fonts → XCB → X11 source contract. It does not submit, resume, retry,
publish, activate, repair or select a caller-supplied output generation.

The protected owner supplies a trusted local context containing the original
gateway request, exact pipeline, Host/installation/lane/Project binding, frozen
source/pin, previous catalogue digest and selected input generation. The output
generation is derived only from the retained completed image-build pipeline.

The reader independently reopens and cross-checks:

- the deterministic gateway snapshot and submit operation identities;
- retained image-build request/binding/result files for those operations;
- the content-addressed recipe snapshot and exact reviewed bootstrap plan;
- the original monthly pin bytes, captured provenance pin and materialized
  snapshot monthly identity;
- the durable pipeline recipe inventory, source-pin identity, owner/source
  binding, selected input generation and completed attempt ledger;
- the immutable output generation manifest/inventory;
- the canonical generation build-record closure and package provenance;
- the single successful installed-verification report and its
  verification_execution binding; and
- the latest retained completed producer result for the submit/inspect sequence.

The normalized result is
`image-build-verified-graphical-predecessor-v1`, matching the bounded
host-deploy generation-chain consumer. Two digest fields are deliberately backed
by objects that already exist in image-build rather than newly invented
"acceptance" files:

- `acceptance_receipt_sha256` is the canonical build-record **generation root
  record ID** from the immutable generation manifest.
- `producer_receipt_sha256` is the SHA-256 of the exact retained completed
  image-build remote result bytes that bind the pipeline and generation.

The pure `verify(...)` function exists for deterministic source tests. Native
use must call the root-only `attest_native(...)` capability from an independently
reviewed protected owner. The trusted context is not a GitHub request or a new
remote_operations method.

## Current chaining boundary

This attester verifies predecessor acceptance only. It does not make an image
generation a valid compiler selection.

At source `b0f53dbd...`, image-build's ordinary `mode=image` execution still
requires its selected generation to be a promoted second-stage `kind=toolchain`.
The host-deploy bounded-chain draft currently proposes selecting the accepted
fonts image as the XCB pipeline selection, and the accepted XCB image as the X11
selection. That execution relationship is not yet supported by image-build and
must be corrected by a separate bounded predecessor-composition contract before
native automatic chaining is enabled. Do not weaken the toolchain-kind guard or
treat this attester as execution authorization.

Native compiler Stage A admission, the real accepted base, protected chain
policy, and genuine fonts/XCB/X11 outputs remain separate Work acceptance gates.

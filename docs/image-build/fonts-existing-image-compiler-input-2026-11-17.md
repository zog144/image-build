# First Fonts: use the retained accepted kind=image compiler input

Source-only change, November 17, 2026. No AWS, compiler run, gateway request,
new Fonts generation or state mutation was performed in this implementation.

## Existing accepted compiler identity

The already retained compiler environment is immutable generation
3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc
in the existing certbot-seed Project. Its canonical manifest has kind=image.
Installed tooling includes GCC, G++, assembler, linker, Make, CMake and Python.
The independently accepted compiler-purpose receipt and generation remain
exactly as issued and published. Neither must be relabelled to kind=toolchain.

Prior code in image-build.engine._ensure rejected every ordinary compiler input
other than a self-hosted second-stage kind=toolchain, regardless of the already
authenticated source inventory. The Project-default resolver in
remote_operations._configured_toolchain also rejected a canonical kind=image
selection after reopening the Project-local link. These were type-label
restrictions, not evidence that the actual compiler was missing.

## Changed source acceptance

For ordinary image builds:
- Existing kind=image is an eligible compiler input without invented stage,
  self_hosted or toolchain-active metadata.
- Existing kind=toolchain still needs the actual stage=2 and self_hosted=true
  proofs; this remains a separate meaningful assertion when a generation
  really is a toolchain.
- host-bootstrap and temporary/other noncompiler kinds are not promoted by
  this compatibility change.
- read_selection still reopens the exact immutable generation ID, manifest
  inputs and full root inventory. The build system copies the compiler root
  into an attempt-local environment and publishes a new kind=image generation
  under its own digest; it does not rewrite the source generation or receipt.
- Remote explicit selection supplies the exact generation ID and separately
  reviewed recipe_snapshot in the selected Project. No "toolchain-active"
  symlink or new kind=toolchain pointer is required for that explicit path.
- Project-default submission can continue using the historical existing
  toolchain-active link or an existing active link, but neither is written or
  synthesized by remote selection. The name "toolchain-active" conveys no
  manifest kind; the reader still verifies the canonical selected generation.

## Independently authenticated compiler receipt remains a separate gate

This source branch is based on the Fonts Project defaults implementation and
changes the obsolete kind-label checks only. **It is not a replacement for
the independently reviewed compiler-purpose acceptance reader** from
image-build PR #20, source 1616f192ef9d8964a8f37f32a86c69c0242a213c.
That reader's compiler_base_acceptance.resolve() already explicitly accepts
a real kind=image generation when the original separately installed
Ed25519 purpose-scoped signer and original SHA-256 receipt, Host, installation,
Project, ABI, executable files and original manifest/outputs match. It
records the original historical provenance gap rather than fabricating
stage-two promotion.

Before any native Fonts build, **retain and compose the PR #20 compiler
receipt validation path with this label-compatibility source**. This small
compatibility patch must not be mistaken for new compiler acceptance or a
shortcut around existing issuer/runner authorization. Never alter, regenerate,
re-sign or relabel the accepted receipt to make a check pass.

## Focused source acceptance tests

The source-only test suite creates an actual immutable kind=image generation
from a staged compiler, retains its exact original root inventory and raw
manifest bytes, writes an immutable external acceptance-receipt fixture, then:
1. Uses that image directly for an ordinary build and proves the output has
   a **different** generation digest, contains the new installed package, and
   binds the original compiler digest as its input.
2. Verifies source manifest, full input root inventory and external receipt
   bytes/mode unchanged after output publication.
3. Sends a new explicit remote image pipeline with its exact generation and
   reviewed recipe snapshot **without either local selection pointer**,
   verifying the prepared pipeline selects the same image.
4. Confirms default remote mode can reopen a pre-existing active image link
   after the historical toolchain-active link is absent, without creating one.
5. Rejects selecting a host-bootstrap generation as an ordinary compiler.

These are local source/durable-output tests, NOT live GCC execution, actual
signed-receipt verification or a Fonts compilation. PR #20's separate signed
image acceptance tests remain required in the composed production selection.

## Project-local limitation, deliberately left separate

The remote _generation() implementation searches *only the selected
builder.control_state Project* at image-build/generations/<generation-id>.
Similarly, remote Project defaults select only existing links inside that
Project, and the recipe snapshot is looked up in the same Project. This is a
Project-local selection rule, not a kind=toolchain gate.

If the selected execution Project is certbot-seed, and it already contains
generation 3805294f..., explicit selection of that exact generation and its
reviewed recipe snapshot requires no other Project, new toolchain, pointer or
compiler build. The first Fonts pipeline then publishes a different image
generation under that same Project. No prior Fonts output/history exists.

If the selected execution Project differs from the retained certbot-seed
Project, the existing remote code cannot look up a compiler generation in
the other Project merely by ID. This source change does not silently add
cross-Project reading or copy/migrate an accepted generation; any such
Project-routing decision requires its own separately reviewed source
contract. It must not be "fixed" by manufacturing a kind=toolchain generation
or new Project just to satisfy a kind check.

## Native Work handoff

- Keep original certbot-seed Project and generation 3805294f... unchanged.
- Install a reviewed source selection combining this kind-compatibility
  correction and PR #20's original accepted compiler receipt reader.
- Explicitly select the original exact generation with its original verified
  signed acceptance receipt and reviewed Fonts recipe snapshot in the
  existing Project. Verify original manifest kind=image and tool file bytes.
- Start a *new* Fonts output operation; never overwrite an input generation.
  Retain the compiler acceptance receipt, old generation, output generation
  and actual Build Record as distinct provenance.
- Verify the original compiler manifest SHA-256, root inventory and receipt
  SHA-256 before and after successful first Fonts publication; verify the
  new output generation ID differs from 3805294f...
- Do not claim a Fonts run/history from these source-only tests.

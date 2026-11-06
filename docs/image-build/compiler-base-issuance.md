# Compiler-base observed isolation and issuance

A compiler-bearing image retains its original kind and history. This acceptance
certifies present compiler capability in one enrolled execution environment. It
is not stage-two reconstruction, a recipe grant, or authorization to submit.

## Observed isolation profile

`image-build-compiler-isolation-v2` replaces the old unconditional booleans inside
the signed probe. The output parser returns `isolation: null`. A native owner
must authenticate a separate kernel witness, original controller completion,
selected generation and trace bytes, then provide the observation.

`selected-root-kernel-mounts-v1` requires nonroot UID/GID, zero effective
capabilities, NoNewPrivs, distinct mount/network namespaces and only loopback
interfaces in the observed job. Bind runtime/invocation IDs to completion,
compiler/linker/header hashes to installed paths, and the witness SHA256 to the
retained root-owned original evidence. Record the exact imported root, source
and output roots and complete mount inventory without dropping unknown entries.

The imported root must be read-only. Explicit pseudo filesystems under /dev,
/proc, /sys, /run, private temporary mounts and source/output workspaces are
permitted by name and filesystem type. /root must refer to the imported root's
own /root. Extra /usr, /lib, /lib64 or nested compiler/header/library mounts are
denied. Source and output mount roots must match the signed workspace identities.
The profile does not assert a specific root-changing syscall, hide the existence
of kernel interfaces, or prove that every possible escape is impossible. A rw
mount flag alone does not establish writable permissions for the worker. The
native owner reviews these actual semantics before selecting this profile.

Signatures authenticate reviewed observations; JSON fields or file ownership do
not establish that the observation happened. Preserve complete native evidence,
including any rejected or incomplete witness, outside the implementation repo.

## Compiler-purpose enrollment and operator review

The installed `zog-protected-compiler-base-issuer-v1` policy remains a separately
authenticated selection of Host, installation, STATE, Project, execution-config
SHA256, public key/key ID and protected receipt directory. Task C operator/event
pins do not automatically authorize this purpose. The protected installation
owner must explicitly enroll a compiler-purpose signer (or explicitly authorize
an already enrolled operator key for this additional domain), attest its custody,
reader/issuer source and dependency bytes, and install the policy. Never create
placeholder installation or STATE identities. No key generation or enrollment
is performed by this module.

Before installing a signing approval, present the exact canonical claim and its
SHA256 to the operator using the selected approval procedure. Review the original
generation/manifest/inventory/record, precise historical gaps, actual ABI, native
completion and witness, installed-path hashes, execution scope and mount profile.
Do not sign an observation merely because synthetic tests passed.

Install one root:root 0600 canonical JSON approval in a protected directory:

- schema: `image-build-compiler-signing-approval-v1`
- purpose: `compiler-base-capability`
- claim_sha256: SHA256 of the exact canonical claim, prefixed `sha256:`
- authority_sha256: SHA256 of the canonical installed authority policy
- key_id: the enrolled compiler-purpose key ID
- reader_revision: the exact reviewed 40-character source commit

The authority, approval and claim must be canonical sorted compact ASCII JSON
without duplicate fields; the private key is an enrolled raw 32-byte Ed25519 seed.
All inputs and their parent directories must be root-controlled. Keep keys out of
argv, environment, journals, repositories and handoffs. Invoke on the protected
signing owner, using its attested Python/cryptography environment:

```
python -m zog.image_build.compiler_base_issuance \
  --authority /protected/compiler/authority.json \
  --approval /protected/compiler/approval.json \
  --claim /protected/compiler/claim.json \
  --private-key /protected/compiler/private.key \
  --reader-revision EXACT_REVIEWED_COMMIT
```

These paths are schematic, not installation identities. The revision argument
is checked against approval; it is not a replacement for installed-byte
attestation. Approval selection is administrative authority, never gateway input.

The signer compares the actual public key with enrollment, checks compiler
purpose and both approved digests, validates the observed probe, and signs
`ZOG_IMAGE_BUILD_COMPILER_BASE_ACCEPTANCE_V1` + NUL + canonical claim. Output is
canonical Ed25519 envelope bytes. Publication is fsynced and atomic create-only
at the policy receipt directory's generation JSON filename. An identical rerun
reopens identical bytes; a conflicting existing receipt is preserved and denied.
A crash may leave a temporary file, never a truncated final receipt. Inspect
uncertain outcomes before rerunning; do not replace historical accepted evidence.

Then independently reopen the receipt with the actual producer `resolve()` and
host-deploy `checked_base()` using enrolled policy and approved lane identities.
Neither signing nor successful reopen grants a Fonts task. Revocation must remove
or replace the protected consumer's trusted compiler policy/selection through
its reviewed installation procedure; deleting an issuance approval alone does
not revoke a receipt already trusted by a consumer. No revocation-history or
key-rotation service is implied by this bounded issuer.

## Reader and observer separation

Install this reader separately from the original immutable producer and the
host-welcome observer. Keep the observer's existing source/module allowlist when
it still serves its original application. If an observer upgrade is needed,
review and attest that exact source separately; never widen the allowlist merely
to admit an unrelated compiler reader.

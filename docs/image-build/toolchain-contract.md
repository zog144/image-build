# Toolchain specification and immutable artifact contract

The canonical producer contract is `image-build-toolchain-specification-v1`.

This contract separates four things that were previously spread across worker
implementation details:

1. the ordered bootstrap graph;
2. durable recovery ownership for each transition;
3. the verification needed before a compiler is called self-hosted;
4. the immutable generation contract consumed by ordinary image-build jobs.

The specification is available to transport consumers through
`toolchain.specification.inspect`. It is source-bound by the normal
`image-build-remote-operation-v1` request and does not execute a build.

## Bootstrap pipeline

The production bootstrap graph is not the same thing as the generic two-stage
`ImageBuild._bootstrap()` primitive. The production graph is:

`cross-bootstrap -> native-bootstrap -> final-libc -> final-math -> final-compiler`

The native-bootstrap phase is deliberately repeatable and may use the producer-owned
`native`, `native_tools` and `native_stage` transitions under reviewed plans.
The final-libc phase permits the normal `glibc_final` path or the separately
evidence-preserving `glibc_publish` recovery path. No phase authorizes an implicit
fallback between producers.

Every phase retains its own intent/operation record, pipeline records where used,
controller request/job identities and cleanup state. Automatic retry and implicit
generation promotion are forbidden.

The specification exposes the typed
`image-build-toolchain-remote-execution-v1` interface through
`toolchain.submit`, `toolchain.inspect`, and `toolchain.resume`.

After the initial `cross-bootstrap` seed generation, callers provide only the next
reviewed phase and the predecessor toolchain operation ID. Image-build derives the
project, catalogue, fixed bootstrap plan, controller configuration, work directory,
retained pipeline attempts and package-ownership records from its own authorized
state. Request JSON never supplies host filesystem paths, worker argv, package target
lists or arbitrary commands.

The concrete unattended chain is:

`cross-bootstrap -> temporary-userspace -> native-transition ->
native-environment -> final-libc-build -> final-libc-publish -> final-math ->
final-compiler`

A failed `final-libc-publish` may be followed only by the explicit
`final-libc-recover` phase, which consumes its retained failed publication
evidence. There is no automatic retry operation. Other terminal failures require
inspection and a separately reviewed correction/new source operation.

The caller must never translate these phases into arbitrary commands or generic
`pipeline.submit` aliases.

## Verification

A final toolchain opts into `image-build-toolchain-verification-v1`.

The required acceptance covers:

- compiler and linker versions;
- glibc version;
- C compile and execution;
- C++ threads, exceptions and LTO;
- the dynamic loader;
- absence of RPATH/RUNPATH;
- host search paths rather than bootstrap paths;
- the installed M4 probe.

Both compiler and M4 checks require typed controller completion with exit status zero
and completed process cleanup. The verification record is content-addressed and its
identity is part of the immutable generation inputs.

## Immutable artifact

A final compiler generation opts into
`image-build-toolchain-artifact-v1`. The generation must be:

- `kind=toolchain`;
- stage 2;
- self-hosted;
- source-built;
- a complete build environment;
- produced by `gcc-three-stage-comparison`;
- bound to the exact toolchain specification identity;
- bound to the exact verification identity.

The generation's normal image-build identity remains the hash of its publication
inputs. The specification and verification bindings are inputs, so changing either
produces a different generation identity.

Intermediate and historical `toolchain` generations that predate this contract are
still readable. They do not become final-toolchain artifacts merely because they use
`kind=toolchain`; consumers that require the final compiler contract must call the
final artifact validator or inspect the contract fields.

The only activation name defined for a final artifact is `toolchain-active`.
Activation happens after immutable publication and successful validation. The
contract never authorizes implicit promotion of a candidate or native temporary
environment.

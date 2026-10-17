# Bootstrap pipeline

## The staged route from host tools to a self-hosted generation

Image-build's initial bootstrap uses a deliberately recorded **host-bootstrap** seed, a cross-compiler stage graph, a temporary native build environment, and acceptance checks before selecting a source-built toolchain. This is not the same as declaring a completed, bootable Zog operating system. Each stage has a distinct output identity and provenance; a compiler that merely runs during a bootstrap is not proof that the final toolchain can rebuild itself.

The [cross-bootstrap plan](../BOOTSTRAP-STAGES.md) describes the x86_64 LFS-target stage graph and explicitly names its source/target/build tuples. A plan's stage identifiers are stable dependency nodes; they are not necessarily package display names. Recipes declare source versions and checks, and the owner materializes a bounded, durable pipeline rather than executing a one-off shell transcript.

## Frozen execution inputs and outputs

Before a build command, the owner binds the selected base generation, exact recipe snapshot, execution policy, expected outputs and controller identity. Package build commands run through box-control and retain invocation-specific journald evidence. The image-build operation owns the package/generation outputs; box-control is an execution mechanism, not a compiler or rootfs producer.

An interrupted wait resumes inspection of the **same** recorded job. Exit 75 is used in historical bootstrap entry points for pending work, not evidence of failure or permission to dispatch a replacement. Input drift, missing snapshots, unknown start outcomes, and failed verification must remain explicit. Do not rerun a failed stage with changed source under its former operation identity.

## Temporary native environment and compiler promotion

The next [native environment stage](../NATIVE-BUILD-ENVIRONMENT.md) uses a reviewed dependency graph with source-built target tools. Its declared dependencies are resolved from the accepted base and pinned archives, not silently satisfied by host RPMs or internet package installation. Installed files are staged under DESTDIR, checked against manifests, and composed into another immutable result. A new stage does not silently overwrite the active generation.

A separate [retained compiler acceptance procedure](../retained-compiler.md) covers an explicitly preserved GCC installation after an independently passing full-suite report. It verifies the original registration/ownership records, exact installed bytes, compile/link behavior, shared-loader paths, and a follow-on native-tool rebuild before selecting the resulting stage-2 toolchain. This is a narrowly scoped recovery continuation, **not** permission to bypass ordinary pipeline checks or a declaration of public/boot readiness.

## When is a stage accepted?

Distinguish these evidence levels:

| State | What can be concluded |
|---|---|
| Recipe prepared | Source, dependency and build metadata exist |
| Graph / source CI validated | Static constraints and source metadata tests passed |
| Build job completed | A concrete execution returned an observed result |
| Installed output verified | Output inventory and intended runtime probes passed |
| Toolchain accepted | The owner performed its explicit promotion checks |
| Boot or distribution accepted | Separate host-install, systemd, trust and live acceptance must pass |

The evidence record must name the selected generation, toolchain, recipe revision and test coverage. A passing smoke test never represents an unrun upstream suite; accepted outputs do not imply that downstream GUI, services or hardware are ready.

## Operator reading order

1. Read [bootstrap stage graph and pending-operation semantics](../BOOTSTRAP-STAGES.md).
2. Review [native environment composition and package reuse](../NATIVE-BUILD-ENVIRONMENT.md).
3. For retained compiler recovery only, follow [retained compiler acceptance](../retained-compiler.md).
4. Inspect [source pins](sources-and-monthly-pins.md), [immutable publication](immutable-artifacts-and-generations.md), and [recovery rules](../publication-recovery.md) before any resumed operation.

Historical commands in the original documents were written for particular source revisions. Verify their import namespace and CLI options against the exact installed revision before running them; this chapter deliberately does not copy an older command line as current executable guidance.

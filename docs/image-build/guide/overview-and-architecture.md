# Overview and architecture

## Purpose and boundaries

Image-build is Zog's **immutable software producer**. It resolves reviewed sources and explicit package recipes, constructs dependency and build plans, executes finite build commands through box-control/root-control, verifies installed outputs, and publishes immutable root-filesystem generations or application software objects. It is neither an alternative process supervisor nor a host provisioner. The [component manual](../README.md) and [reference/schemas chapter](reference-and-schemas.md) identify component boundaries and source-backed interfaces. Consult the matching source revision for exact command-line entry points; the aggregate root README is not an image-build-specific setup guide.

| Responsibility | Owner | Boundary |
|---|---|---|
| Pin selection and source download | image-build, assisted by archive-mirror | Canonical source identity stays pinned regardless of transport |
| Package recipe, output and dependency graph | image-build | Explicit build/runtime edges, no implicit host RPMs for target packages |
| Transient commands, cgroups and journald | box-control using privileged root-control | Finite build services; no Docker/Podman execution fallback |
| Durable immutable software objects | image-build | Exact input/output identities and verified publication |
| Build provenance and observations | image-build producer → build-record → build-trace | Canonical records and separately selected observation snapshots |
| EC2/SSM host and dispatch ownership | host-deploy | Exact authorized workspace, source revision and request |
| Runtime application launch | box-control | Consumes selected immutable generations/views without building |
| Boot installation, disks and selected HOST slots | host-install | Separate disk/host acceptance, not image-build success |

## Repository, project, and state are different things

The repository contains `src/zog/image_build/`, `project/package/`, `project/bootstrap/`, tests and developer aids. A **deployment project** and its `state/` reside separately from that source checkout. A package is build/install metadata; an application is runtime composition belonging to box-control. Recipes contain literal source, dependency, build, manifest, license and integration descriptions, not Python scripts imported as an unrestricted build backend. A package may have build-only inputs whose binaries must **not** enter a published rootfs.

Pipeline preparation binds the selected immutable recipe snapshot, original monthly pin digest, explicit base/toolchain, resource limits and controller identities. Package attempts produce retained outputs and verification evidence. Composition selects runtime dependencies, validates ownership/collisions and publishes a new immutable generation. The `active` or `toolchain-active` selection is explicit and distinct from the existence of a built generation. A reference to a generation is not proof that it was booted or that a release was approved.

## Build lifecycle

1. **Select** an exact reviewed source set, recipes and accepted base/toolchain; unresolved source/version or licensing exceptions remain recorded.
2. **Prepare** a durable pipeline with frozen inputs and provenance identity before dispatching side effects.
3. **Acquire and verify** source bytes (local content cache, authorized archive-mirror, upstream fallback) against pinned digests.
4. **Build and test** finite, identity-bound commands using box-control, retaining execution, logs, outputs, skips and failure evidence.
5. **Compose and verify** the immutable rootfs or application artifact/view, including ownership, installation paths, notices and runtime compatibility.
6. **Publish** an exact content-addressed object with atomic receipt/pointer handling; interruption resumes the same frozen publication.
7. **Observe and inspect** canonical records, selected verification snapshots, and read-only references. Release, application launch and host installation remain separate decisions.

A successful package compilation or even a selected rootfs generation does **not** imply a boot-ready host or a currently deployed workstation. Evidence levels are explained in [recovery and verification](recovery-and-verification.md).

## Software product classes

The rootfs generation contains read-only system files and declared empty runtime scaffolds. The application software store publishes installed runtime application artifacts (including optional Django/React output), while symlink-composed views map selected artifacts into stable application paths without OverlayFS. Mutable databases, private keys, host leases, journals and other STATE must never be baked into software. Publication identities, consumer contracts and recovery are detailed in [immutable artifacts and generations](immutable-artifacts-and-generations.md).

The bootstrap route starts from an explicitly recorded foreign host seed and builds toward a source-built toolchain. Independent toolchain tests and target-root acceptance precede ordinary package builds. Graphics and host boot packages have further acceptance gates, as described in [bootstrap](bootstrap-pipeline.md), [language runtimes](toolchains-and-language-runtimes.md) and [graphics](recipes-graphics-and-runtime-facilities.md).

## Execution ownership and uncertainty

Only the exact selected controller project may submit and observe its finite commands. If a root registration, service start or SSM submission result is uncertain, image-build and its caller must inspect the **same** bound request/resource before trying another action. An unavailable input, incomplete artifact candidate or changed recipe must not be silently replaced during resume. Provenance output is not permission to reclaim retained artifacts: external runtime/cleanup references may still protect them.

The [remote execution contract](remote-execution-and-gateway.md) provides capability discovery, recipe snapshots, pipeline preparation and inspection for the exact deployed source revision. Host-deploy independently authorizes the gateway and compiler lanes; station-access is an administrative reader/consumer rather than an additional compiler owner.

## Which chapter to read

- [Sources and monthly pins](sources-and-monthly-pins.md): exact upstream selection, mirrored transport, exceptions.
- [Bootstrap](bootstrap-pipeline.md) and [toolchains](toolchains-and-language-runtimes.md): source-built execution foundation.
- [Immutable publication](immutable-artifacts-and-generations.md): rootfs, application artifacts/views and protection.
- [Remote operations](remote-execution-and-gateway.md): producer API, caller admission and recovery.
- [Provenance](provenance-and-observation-publication.md): record creation, observation selection and comparability.
- [Verification](recovery-and-verification.md) and [schemas](reference-and-schemas.md): acceptance evidence and machine contracts.

### Source-of-truth notes

The [early architecture checkpoint](../catalogue/IMAGE-BUILD-ARCHITECTURE.md), [implementation report](../catalogue/IMPLEMENTATION-REPORT.md) and [dated status history](../CURRENT-STATUS.md) are retained for traceability. Several describe the build-job API as not yet available or report older partial compiler states; they are **historical snapshots**, not canonical current capability decisions. The repository README and exact deployed `capabilities.inspect` response determine the supported interface; a live production host needs separate acceptance. No source revision in this manual authorizes rootfs promotion or release publication on its own.

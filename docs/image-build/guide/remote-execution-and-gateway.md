# Remote execution and gateway

## The exact deployed producer is the execution authority

The `image-build-remote-operation-v1` interface is a **transport-neutral producer contract**. A caller such as host-deploy, a command-center service or a future external automation does not gain arbitrary shell access by knowing the interface. Every request identifies the exact authorized source repository, immutable deployed commit, operation ID, operation kind and closed arguments. A mismatched checkout/commit or repeated operation ID with changed intent fails closed. Image-build owns recipe snapshots, pipeline construction, result persistence and the exact output identities.

The remote caller must distinguish the request for an operation from its actual completion. An accepted request with incomplete controller evidence is not a proven build success, and lost responses must not create a second independent command or change its bound source.

## Read-only capability discovery and preparation

The producer exposes `capabilities.inspect` to report its **implemented** generic pipeline modes and operations for that deployed revision. `worker.inspect` describes maintained-worker routing separately. The published remote contract includes `recipe.validate`, `recipes.snapshot`, `pipeline.submit`, and explicit inspect/continue/cancel/retry forms; no generic pipeline target list can be silently invented from a historical worker name.

A `recipes.snapshot` request binds an immutable, dependency-complete selected recipe set to the exact catalogue revision and reviewed monthly pin. New submit/retry operations use the accepted immutable snapshot binding. The original source provenance pin and materialized snapshot pin are **distinct** identities. See [remote operation contract](../remote-operations.md) and [monthly source pins](sources-and-monthly-pins.md).

## Runtime dependency preflight is read-only

The maintained `zog.image_build.runtime_preflight` inspects the deployed environment against `image-build-runtime-preflight-v1`, including required compatible dependencies and source-binding evidence. It makes **no** image-build mutation. Host-deploy should run that preflight while remote dispatch remains prepared and only submit once the exact producer/runtime requirements hold.

An unsuccessful or unavailable preflight does not authorize a guessed dependency set or a new SSM command. Passing preflight is also not authorization or proof of successful execution: gateway ownership, caller scope, source identity, remote status and result receipts remain independently checked.

## Controller and host-deploy boundaries

Image-build submits finite build commands through the configured box-control project and retains the associated job/request identities. Root-control validates privileged execution. Host-deploy owns EC2/SSM transport and host-wide lane admission. Workspaces and independent build lanes have separate mutable project state and `image-build.lock`; they may share host hardware and source-byte mirror resources, not one mutable attempt/generation directory.

A lost build-root registration reply can be reconciled through the exact resource identity and read-only status, according to the [registration recovery](../registration-recovery.md) and [continuation](../registration-continuation.md) contracts. Status `importing` or `absent` does not mean safe resubmission. Box-control itself verifies intent and clears its own guard before any job identity is issued. Similarly, SSM submission uncertainty belongs to the owner gateway; the compiler producer must not bypass it.

## Results, observation and retry

Pipeline inspection returns durable pipeline/request identity and status. Unknown or uncertain outcomes retain the recorded evidence and block automatic substitution; the original request's exact operation identity remains the resume target. Explicit retry is a **new authorized operation** under documented predecessor/retry rules, not rewriting a terminal failed result or reusing an abandoned request ID.

The producer must not expose host-level package installation, arbitrary privileged shell operations, EC2 lifecycle, or network diagnostics through this contract. Those are separately authorized host-deploy/controller capabilities.

## Canonical references

- [Versioned remote operations and capabilities](../remote-operations.md)
- [Source pins and immutable snapshot selection](sources-and-monthly-pins.md)
- [Read-only registration recovery](../registration-recovery.md)
- [Long-running registration continuation](../registration-continuation.md)
- [Controller launch/builder integration](../CONTROLLER-INTEGRATION.md)
- [Host-deploy owner gateway](https://github.com/zog144/host-deploy/blob/unstable/docs/host-deploy/guide/compiler-gateway-and-dispatch.md)

Historical gateway pass notes that rejected `build.submit` before snapshot support remain historical. Determine **current** availability from the exact pinned producer capability response and accepted live gateway path; this chapter does not authorize production dispatch.

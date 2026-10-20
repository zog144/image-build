# Post-install application progress projection

Contract: `image-build-post-install-progress-v2`  
Wire: `image-build-post-install-progress-rpc-v2`

This is a bounded read-only projection of **image-build-owned durable evidence**.
It complements, and does not replace, box-control's
`zog-application-progress-v1` controller/runtime observations.

It never submits, resumes, cancels, publishes, mounts or launches work.

## Authoritative intent owner

`host-install` is the sole selection/intent owner.

The owner records one complete selection using:

`zog.image_build.post_install_progress.record_selection(...)`

The record has:

- monotonically increasing integer `sequence`;
- immutable `selection_revision` derived from the complete selected/not-selected
  set;
- one row for every reviewed post-install application;
- `requested: true` plus an immutable SHA-256 `operation_revision` for selected
  applications;
- `requested: false` and no operation revision for explicit non-selection.

Absence, damage, ambiguity or rollback of this receipt is **unknown**, never
`not-requested`.

A requested application's pipeline must be prepared with the exact owner object
returned by:

`pipeline_owner(selection_receipt, application)`

The owner object freezes:

- host-install intent owner;
- selection revision and sequence;
- application;
- immutable operation revision.

The progress reader searches only exact matching pipeline-owner objects. Multiple
matching pipelines are a conflict and return `uncertain`.

## Command execution join

New command `.view.json` records freeze two additional safe identifiers at command
creation:

- `recipe_identity`: the exact package recipe fingerprint;
- `source_pin_identity`: the pipeline's exact source-pin identity.

The projection joins these to existing immutable fields:

- pipeline ID;
- attempt ID;
- stage ID;
- package;
- build phase;
- command index;
- controller request ID;
- deterministic build job ID;
- a SHA-256 identity of the sanitized immutable build trace;
- build-record identities for prepared inputs/result/output when present;
- the retained controller observation timestamp and controller boot identity.

The authenticated snapshot additionally binds the deployed producer source with
`image-build-post-install-source-v1`: exact repository plus immutable 40-hex
image-build commit. This is the source revision of the projection implementation,
not a substitute for the package's separate recipe/source-pin identity.

Only phases `prepare`, `configure`, `build`, `test`, and `install` are
accepted.

Raw argv, environment, log text, host paths and source URLs are never returned.

A saved controller request without a terminal observation is `uncertain`, not
running. A command succeeds only when its saved observation has the exact request
and deterministic job identities, a valid observation timestamp/boot ID, says
`state=completed`, `outcome=success`, and
`process_cleanup_complete=true`, and has the required retained trace/build-record
association. Missing receipts or conflicting evidence return `unknown`.

Terminal failure and cancellation are projected distinctly even when the pipeline
remains `pending` for explicit recovery. A caller interruption is not permission
to fabricate a new attempt. Durable terminal command evidence may survive reboot;
the current snapshot's own boot/timestamp are separate freshness evidence.

No percentages are synthesized: `progress` is always null.

## Publication receipt

Application build success is **not** software publication.

The image-build publication owner records a verified receipt with:

`record_publication(...)`

The receipt reopens the immutable `applications-v1` artifact and binds:

- exact artifact SHA-256 ID;
- artifact revision;
- digest of artifact source/provenance identity;
- host-install selection revision;
- owner operation revision;
- optional `application-software-view-v1` SHA-256 ID;
- whether selected-rootfs compatibility was independently checked;
- the exact immutable selected rootfs **generation ID** when compatibility is checked;
- optional `application-software-consumer-v1` binding digest.

Publication can advance monotonically:

1. artifact only;
2. artifact + view, compatibility unchecked;
3. same artifact/view + verified selected-rootfs compatibility.

Each superseded receipt is retained under publication history. Artifact, source,
view, selection or operation identity may never change during that progression.

Every read re-resolves the immutable artifact/view. A compatibility-checked receipt
also reopens the exact retained `kind=image` rootfs generation, verifies that its
frozen `application_software_compatibility` descriptor still equals the receipt,
and recomputes the consumer binding. A copied descriptor from another generation,
missing generation, tampered artifact/view, or conflicting publication returns
`unknown`.

Publication does not imply box-control runtime admission, a mounted application,
an active GUI, or physical-seat readiness. The projection reports
`runtime_admission="unobserved"`; host-welcome must join box-control evidence
separately.

## Local broker

Source entry point:

`python -m zog.image_build.post_install_progress_broker`

Deployment parameters are fixed by host-install/systemd, not the UI:

- canonical image-build state directory;
- numeric host-welcome observer UID;
- reviewed application allowlist;
- exact deployed image-build repository name and immutable source commit;
- exactly one systemd-activated AF_UNIX socket.

The service must run as the distinct non-root image-build progress producer UID.
It refuses root execution and refuses using the consumer UID as the producer UID.

Authentication uses Linux `SO_PEERCRED` **before request parsing**. Only the
configured observer UID receives a reply.

Request framing is a 4-byte network-order length followed by JSON, maximum 4096
bytes. Reply maximum is 65536 bytes. The only operation is:

```json
{"schema":"image-build-post-install-progress-rpc-v2",
 "operation":"snapshot","after":null,"limit":4}
```

The UI cannot provide a project/state path, application selector, command, job ID,
credential, mutation action or arbitrary evidence reference.

The application allowlist is fixed at broker startup. Pages are ordered by
application name, maximum 16 applications, with at most 16 command observations per
application in the broker's default producer call.

Every response has a fresh random 128-bit `snapshot_id`, timezone-aware
`observed_at`, the producer's current Linux boot ID, and exact deployed source
binding. A consumer must reject a stale/future response or an unexpected producer
source/boot according to its own reviewed freshness policy. Durable
intent/build/publication identities survive reboot, so a retained terminal command
may truthfully name the older controller boot while the current snapshot names the
new producer boot. Replaying an old response never changes producer state.

## Sanitized state/message vocabulary

Application states are restricted to:

- `not-requested`
- `waiting`
- `running`
- `succeeded`
- `blocked`
- `failed`
- `cancelled`
- `uncertain`
- `unknown`

Examples:

- no authoritative selection: `selection-unobserved` / unknown;
- explicit owner non-selection: `application-not-requested`;
- selected but no pipeline: `intent-awaiting-pipeline`;
- saved request but missing terminal observation:
  `command-observation-missing` / uncertain;
- terminal cleaned-up command: `command-succeeded`;
- pipeline complete without publication:
  `pipeline-complete-publication-unobserved`;
- artifact receipt only: `artifact-published`;
- view exists but compatibility is not checked:
  `view-published-compatibility-unchecked`;
- verified selected-rootfs binding: `view-published-compatible`;
- tampered/conflicting publication: `publication-evidence-conflict` / unknown.

Synthetic source fixtures are test evidence only. host-welcome must continue to
display publication as unobserved until a live authenticated producer is deployed.


## Host-welcome fixtures and adoption boundary

Sanitized source fixtures live under
`examples/host-welcome/post-install-progress-v2/`:

- `successful.json`: build completed; publication still unobserved;
- `in-progress.json`: requested pipeline executing;
- `failed.json`: retained terminal build failure;
- `interrupted.json`: request/job identity retained but terminal observation missing;
- `unknown.json`: no authoritative selection/evidence;
- `published.json`: artifact + view + exact selected rootfs generation compatible.

These are schema examples, not live host evidence. The authenticated host-welcome
consumer must use the fixed broker, verify the expected image-build source commit,
peer UID, current response freshness/boot, and then separately join current
box-control runtime evidence. It must not treat `published` as mounted, launched,
display-ready, authenticated-login-ready, or physical-seat-ready.

The broker service runs as a distinct non-root producer account and authorizes only
the exact numeric host-welcome UID supplied by protected host-install/systemd
configuration. It refuses root execution and refuses producer UID == consumer UID.
Neither the UI nor the RPC request can choose the state directory, repository,
source revision, application allowlist, controller job, or publication identity.

# Remote image-build operation contract

Contract: `image-build-remote-operation-v1`.

This interface is the transport-neutral boundary between image-build and callers such
as host-deploy, station-access, or a future GitHub/SQS dispatcher. Image-build does
not know which transport requested an operation.

Every request binds:

- a client operation ID;
- an operation type;
- the exact authorized source repository identity;
- the exact immutable deployed commit revision;
- operation arguments;
- an optional predecessor operation ID.

The adapter is invoked from that exact deployed checkout. A request whose repository
or revision differs from the deployment is rejected before execution. Reusing an
operation ID with different input is rejected.

## Operations

Initial operations are:

- `capabilities.inspect`: return the versioned machine-readable producer capability
  contract for this exact deployed source revision. It is derived from the same
  operation and generic-pipeline mode constants used by request validation, and
  explicitly distinguishes generic pipeline execution from maintained workers.
- `recipe.validate`: parse reviewed recipes and verify the currently supplied recipe set.
- `recipes.snapshot`: materialize a content-addressed, dependency-complete selected
  recipe set from exact repository catalogue entries plus the reviewed monthly pin.
- `worker.inspect`: return the machine-readable maintained-worker routing contract;
  it does not execute a worker.
- `package.inspect`: report source identities, dependencies, outputs, licensing and
  source provenance for one package.
- `dependencies.resolve`: return deterministic dependency order for arbitrary
  reviewed targets.
- `pipeline.submit`: prepare and continue an `image`, `bootstrap`, `seed-check`
  or `native-check` pipeline using an explicitly selected immutable
  `recipe_snapshot`.
- `pipeline.inspect`: bounded read-only summary of an existing pipeline.
- `pipeline.resume`: continue an adapter-owned pending pipeline only with its
  originally bound repository/revision.
- `pipeline.cancel`: durably bind an explicit cancellation request, cancel any
  retained controller jobs by their existing identities, wait for process cleanup,
  then release pipeline resources without deleting retained evidence.
- `pipeline.retry`: create a new pipeline after a predecessor has authoritative
  terminal failure evidence and no unresolved outcome. The predecessor is explicitly
  released; its recipes, attempts and failure evidence remain retained.
- `generation.inspect`: verify and report a published generation inventory and
  provenance locators.
- `diagnostic.submit` / `diagnostic.inspect`: execute or inspect a reviewed,
  repository-pinned diagnostic definition.

Pipeline preparation and execution are separate internally. The pipeline ID and its
owner/source binding are durable before the first command submission. If a caller
loses the reply, repeating the same operation discovers that exact pipeline rather
than creating another one. Calls carrying the same remote operation ID are serialized
by a per-operation file lock before request or binding creation, so concurrent
duplicate dispatchers cannot allocate competing durable state.

## Capability discovery

Consumers should not infer producer readiness from documentation text or branch age.
Submit a source-bound `capabilities.inspect` request with an empty `arguments`
object. The response artifact is:

`image-build-remote-capabilities-v1`.

The contract advertises:

- the exact request/result schemas and deployed source repository/revision;
- the exact remote operation names accepted by that producer revision;
- whether generic pipelines are remotely supported;
- `image-build-recipe-snapshot-v1` as the required immutable selection boundary
  for new `pipeline.submit` and `pipeline.retry`;
- the generic modes accepted by the same validation constant used by submission;
- explicit inspect/resume/cancel/retry recovery operation names and the fact that
  retry is never automatic;
- the maintained-worker contract and worker names, with
  `remote_execution_operation: null` and
  `generic_pipeline_submit_equivalent: false` until a future producer revision
  implements worker-specific remote execution;
- the deliberately narrow external-observed-state capability
  (`pipeline.inspect` only).

A gateway may therefore enable generic `build.submit` only when the exact deployed
producer advertises `generic_pipeline.supported: true`, names
`recipes.snapshot` and `pipeline.submit`, and accepts the task's generic mode.
It must not turn a maintained worker into a generic target list merely because that
worker name appears in the capability document.

## Runtime dependency preflight

The normal remote-operations CLI may need companion Zog components before it can
execute the requested operation. In particular, provenance initialization calls
build-record **before** an operation such as `pipeline.inspect` reaches the adapter.
A module-only import of `zog.image_build.remote_operations` is therefore not a
sufficient gateway readiness check.

Image-build now owns the pre-provenance entrypoint:

```sh
python -B -m zog.image_build.runtime_preflight \
  --repository-root /absolute/image-build-checkout \
  --python-executable /usr/bin/python3.12 \
  --operation pipeline.inspect \
  --provenance \
  --external-observed-state \
  --component-root build-record=/absolute/build-record-checkout
```

The output contract is `image-build-runtime-preflight-v1`. It is bounded JSON and
the process exits 0 only when `ready: true`; a missing or incompatible companion
returns exit 3 with `ready: false`. The advertised invocation requires Python
`-B` (and the module also sets `sys.dont_write_bytecode`) so importing staged
source cannot create `__pycache__` content. The preflight creates no image-build
state, captures no provenance artifact, opens no controller, and never submits a
command.

For the pass-4 external-observed-state `pipeline.inspect` path with provenance, the
operation-specific companion closure is:

- image-build exact deployed source;
- build-record 0.8.2, validated compatibility checkpoint
  `a866c9c4b0dd385045f00ce2de7d809f5b67c104`;
- no build-record component dependencies;
- no build-record external Python dependencies.

The maintained source layout is:

```text
<image-build>/src
<build-record>/src
```

and the selected interpreter receives both as explicit source roots, for example:

```text
PYTHONPATH=<image-build>/src:<build-record>/src
```

The preflight requires the imported `zog.build_record` module to resolve below the
supplied build-record root, requires version 0.8.2, and executes the same core
build-record schema APIs used by provenance startup without writing storage.

Controller-backed operations have a larger profile. They additionally require
box-control 0.1.0 at validated public compatibility checkpoint
`644170fc441863307092f329bf7e23cb64eb33e2`, rooted at
`<box-control>/box-control/src`, plus `dbus-next==0.2.3`. The required API is
`BoxControl`, `Project`, `runtime.root_control.RootControlSystemdTransport`,
and `build_jobs.BuildJobs`. This profile is advertised by
`capabilities.inspect`; it is not imposed on the read-only historical
`pipeline.inspect` path.

The aggregate `zog-component.json` dependency list remains broader
(`box-control`, `build-record`, `host-identify`) because it describes the full
component/release closure, not the imports required for every individual remote
operation.

A gateway must run this producer-owned preflight while its dispatch is still
prepared. A failed preflight is not an SSM request execution and must not advance the
dispatch to submitting.

For exact-companion acceptance, after the read-only preflight succeeds, run the
producer-owned disposable smoke helper:

```sh
python -B -m zog.image_build.runtime_companion_smoke \
  --repository-root /absolute/image-build-checkout \
  --python-executable /usr/bin/python3.12 \
  --source-repository zog144/image-build \
  --source-revision IMAGE_BUILD_COMMIT \
  --build-record-root /absolute/build-record-checkout \
  --provenance-pin /absolute/image-build-checkout/INACTIVE-REVIEW-PIN.py \
  --expected-pin-digest sha256:EXACT_REVIEW_PIN_DIGEST
```

The smoke contract is `image-build-runtime-companion-smoke-v1`. For source-only
compatibility testing, the pin may be a deterministic inactive review pin below
the disposable checkout; it is hash-bound and discarded with that checkout and is
not an activated or historical monthly source pin. Production provenance still
requires the separately approved reviewed monthly pin.

The helper first runs the read-only preflight, then invokes the **real**
`zog.image_build.remote_operations` CLI with the same exact source roots and a
temporary control-state directory. Its request is only `capabilities.inspect`, so
real `Provenance.capture_pin` and `Provenance` initialization are exercised but no
build pipeline is created. The temporary state is discarded on completion and is
distinct from the production gateway ledger and historical observed state.

## Request

Example:

```json
{
  "schema": "image-build-remote-operation-v1",
  "operation_id": "oct1-gcc-pass1",
  "operation": "pipeline.submit",
  "source": {
    "repository": "zog144/image-build",
    "revision": "0123456789abcdef0123456789abcdef01234567"
  },
  "arguments": {
    "mode": "image",
    "selection": "<64-hex toolchain generation>",
    "targets": ["gcc"],
    "recipe_snapshot": "sha256:<selected recipe snapshot>"
  }
}
```

The CLI is:

```sh
python3 -m zog.image_build.remote_operations \
  --repository-root /absolute/deployed/source \
  --source-repository zog144/image-build \
  --source-revision COMMIT \
  --package-dir /absolute/deployed/source/project/package \
  --state-dir /absolute/lane/project/state \
  [--observed-state-dir /absolute/read-only/historical/project/state] \
  [--controller-config /absolute/lane/project/controller.json] \
  --provenance-host-id HOST-ID \
  --provenance-project-id zog-compiler-view \
  --provenance-pin /absolute/deployed/source/project/pins/YYYY-MM-01/commit-pin.py \
  --expected-pin-digest sha256:EXACT-MONTHLY-PIN-DIGEST \
  request.json
```

Host-deploy is responsible for obtaining and authorizing the source checkout,
transporting the request, AWS/SQS/IAM concerns and selecting the lane. For a production lane, provenance configuration requires both
`--provenance-pin` and `--expected-pin-digest`. The provenance pin is the **original
reviewed monthly source pin** inside the exact deployed repository, not a pin inferred
from `--package-dir`. Image-build requires an absolute regular non-symlink path below
`--repository-root`, validates the monthly pin structure, rejects materialized
recipe-snapshot pins, captures the exact bytes through `Provenance.capture_pin()`,
and verifies the SHA-256 before and after capture. The resulting provenance descriptor
retains the repository-relative path and the exact supplied deployed source revision.

`--package-dir` now means only the recipe set used by the `ImageBuild` instance.
It does not locate provenance evidence. Read-only operations such as
`pipeline.inspect` may therefore use `<checkout>/project/package` while provenance
is independently bound to `<checkout>/project/pins/<month>/commit-pin.py`.

Image-build owns request meaning, monthly-pin meaning, recipe/pipeline identity and
recovery. Host-deploy may freeze and verify the image-build-supplied repository path
and digest, but must not derive that path from a date convention or from
`package_dir`.

## External read-only observed state

`--observed-state-dir` is an optional server-owned CLI binding for one narrow use
case: read-only `pipeline.inspect` against a historical image-build state universe
that is different from the current gateway/control lane.

The two state roots have separate ownership:

```text
--state-dir
  mutable control/evidence state for this remote operation
  image-build/remote-operations/<operation-id>/...
  provenance capture and any other new gateway-owned evidence

--observed-state-dir
  read-only historical state
  image-build/pipelines/<pipeline-id>/pipeline.json
  image-build/attempts/...
  image-build/generations/...
```

Supplying external observed state changes **only** the source of retained pipeline
inspection evidence. It never replaces `ImageBuild.state`, does not weaken the
configured runner's state/project invariant, and is not accepted from request JSON.

The observed path must be absolute, already exist as a directory, not itself be a
symlink, canonicalize successfully, and differ from the control state. The canonical
path and pipeline ID are frozen in the remote-operation binding under the control
state so replaying one operation ID against a different historical tree is rejected.

With `--observed-state-dir` configured, request validation permits exactly:

```text
pipeline.inspect
```

Every other remote operation is rejected before observed-state resolution, including
submit/resume/cancel/retry, generation inspection, diagnostics, package/recipe
inspection and dependency resolution. This deliberately makes the mode
observation-only rather than a general alternate state root.

External inspection resolves the pipeline record, attempts, command/execution/
observation records, and selected generation entirely from the observed state. It
does not fall back to control state if evidence is missing, even when a same-ID
pipeline exists there. Existing missing-evidence and uncertainty behavior is retained.

No controller is required for external `pipeline.inspect`. Even if the control lane
has a configured controller, live log lookup is disabled for externally observed
pipelines; retained journal references and bounded evidence locators are still
returned. A future live-log feature would require a separately explicit controller/
project binding.

The bounded result does not reveal the observed absolute host path. Instead, when a
pipeline record is available it includes:

```json
{
  "artifacts": {
    "observation_source": {
      "kind": "external-state",
      "pipeline_record_sha256": "sha256:..."
    }
  }
}
```

When the observed pipeline record is missing, `kind: external-state` is retained
without fabricating a digest. The full canonical observed path remains only in the
control-state operation binding.

This design performs no write, chmod, rename, unlink, directory creation or other
mutation below the observed tree. All remote request/binding/result and provenance
writes continue to use `--state-dir`.

## Result

Every response uses `image-build-remote-result-v1` and is bounded. Core fields include:

- operation ID/type and exact source repository/revision;
- recipe, pipeline and attempt identities;
- selected generation;
- package/stage/phase where known;
- status and terminal outcome;
- bounded failure reason;
- controller job IDs and observed exit/outcome fields;
- journal/evidence locators and bounded sanitized log excerpts when the configured controller is available;
- generation/artifact and provenance locators; generation inspection includes a bounded inventory prefix, total count, truncation flag, full inventory digest, and the durable manifest locator;
- uncertainty and explicitly missing evidence;
- allowed next operations;
- predecessor operation.

The response is an observation of image-build/controller state, not recovery
authority. Full logs remain in journald/controller storage and full artifacts remain
in durable image-build stores.

Status meanings:

- `completed`: authoritative operation completion was verified.
- `failed`: terminal failure evidence exists.
- `pending`: the same identity requires inspection/continuation.
- `released`: the pipeline was explicitly abandoned/released.

A controller failure whose process cleanup is explicitly unresolved also remains pending and is never offered for retry. An unknown controller outcome remains pending with `uncertainty=true`; retry is not
offered. Pending pipelines may be explicitly cancelled. Cancellation never creates a
replacement command identity: it reconciles/cancels the retained controller jobs,
requires process cleanup, and only then marks the pipeline released.

## Monthly provenance pin versus recipe-snapshot pin

Two immutable pin objects have different meanings and are never substituted.

The original reviewed monthly pin is repository source evidence, for example:

```text
project/pins/YYYY-MM-01/commit-pin.py
```

It identifies the reviewed monthly source set and is captured by
`Provenance.capture_pin()`.

Separately, `pins.snapshot()` materializes a `commit-pin.py` in a durable recipe
snapshot. That record binds selected recipe IDs/sources and carries
`monthly_identity`. It is intentionally not byte-identical to the original monthly
pin. The remote provenance CLI rejects a pin carrying `monthly_identity`.

The first host-deploy pass-4 read-only acceptance does not need a recipe snapshot:
`pipeline.inspect` can use the repository catalogue as `--package-dir` and the
explicit original monthly pin as `--provenance-pin`.

Remote recipe selection is now explicit.

A caller first submits `recipes.snapshot` with an exact list of:

```json
{
  "entries": [
    {
      "id": "gcc-final",
      "project": "gcc",
      "recipe": "gcc/stages/final"
    }
  ],
  "pin_date": "YYYY-MM-01"
}
```

When provenance is configured, `pin_date` may be omitted; image-build uses the
already captured monthly provenance pin and refuses a conflicting date. The monthly
pin bytes/path must still match the captured provenance descriptor.

The operation copies only the selected reviewed recipe directories into
`state/image-build/recipe-snapshots`, retains the required license and source
provenance declarations, writes the distinct materialized `pins.snapshot()`
`commit-pin.py`, verifies that every selected package's build/runtime/test
dependencies are present, and publishes the result under the content-derived
`image-build-recipe-snapshot-v1` identity.

The snapshot manifest binds:

- exact deployed repository/revision;
- normalized selected recipe IDs/project/recipe paths;
- reviewed monthly-pin identity;
- package fingerprints;
- complete materialized recipe inventory.

A published snapshot is immutable and tamper-checked before use. The generated
snapshot pin retains `monthly_identity` and remains distinct from the original
reviewed monthly provenance pin.

Every **new** `pipeline.submit` and `pipeline.retry` must provide
`recipe_snapshot: sha256:...`. Image-build verifies that the snapshot belongs to the
same deployed source revision and that requested targets/stages are present, then
constructs the pipeline with that snapshot as its package directory. The pipeline
still retains its own exact recipe copy, preserving the existing per-pipeline recovery
contract.

Historical already-owned submissions remain inspectable/resumable by their retained
pipeline identity; this requirement does not rewrite old pipeline records.

### Maintained worker routing

The public gateway names:

```text
stages
native-stage
glibc-final
glibc-publish
final-math
final-compiler
```

are **not** generic `pipeline.submit` aliases.

`worker.inspect` publishes
`image-build-maintained-worker-v1` with the exact maintained module/entrypoint,
required/optional CLI options, high-level owned semantics, and:

```text
dispatch_interface = maintained-worker
generic_pipeline_submit_equivalent = false
```

The dispatcher `zog.image_build.worker` derives its module table from that same
contract so the executable routing and advertised routing cannot drift independently.

The classifications are deliberate:

- `stages` owns reviewed stage-plan materialization, seed verification, cross-bootstrap
  assembly, linking probes and runtime-generation publication.
- `native-stage` owns its staged native durable operation and plan.
- `glibc-final` and `glibc-publish` own specialized retained-attempt normalization,
  probes and final-libc publication.
- `final-math` owns the accepted final-libc arithmetic prerequisite flow.
- `final-compiler` owns multiple reviewed plans, replacement of temporary compiler
  components, upstream three-stage comparison, acceptance probes and final self-hosted
  toolchain publication.

Host-deploy must therefore dispatch these identities through the maintained worker
entrypoint until image-build introduces a future explicit worker-specific remote
operation. It must not synthesize target lists and call generic `pipeline.submit`.

## Explicit retry

A failed recipe is never modified in place. A corrected commit uses a new remote
operation ID and `pipeline.retry` with `predecessor` referencing the failed remote
operation. The old pipeline must still classify as a resolved terminal failure.

A new source revision is allowed for the retry. That creates a new snapshotted
pipeline while retaining the old source revision, recipes, command evidence and
failure.

## Diagnostics

Diagnostics are repository source, not issue-body shell.

A diagnostic is stored at:

```text
project/diagnostic/<name>/
    diagnostic.json
    <script>.py
```

The declaration fixes the Python script, guest interpreter, timeout, memory maximum,
thread maximum, CPU weight, output-byte limit and result paths. Requests may only add
a bounded argv vector and select a retained target generation.

Diagnostics:

- use an immutable selected generation as a read-only build root;
- copy only the reviewed pinned Python diagnostic source into the source workspace;
- run through the existing box-control/root-control finite-build mechanism;
- have no host privileges;
- have network disabled by the current build protocol;
- receive their own controller request/job identity;
- retain output hashes and controller/journal locators;
- remain linked to the exact remote operation/source revision.

Networked diagnostics require a future separately reviewed protocol change; this
contract does not weaken root-control's current `PrivateNetwork` policy.

## Concurrency / build lanes

Image-build remains intentionally serialized **within one state directory**. Concurrent
independent builds use different box-control Project roots/state directories on the
same host. This preserves each lane's:

- `image-build.lock`;
- pipelines, attempts and generations;
- box-control mutation guard/build records;
- root-control build resources.

Root-control already scopes privileged resources by the full project root. Build
requests additionally support optional systemd `CPUWeight` alongside the existing
per-job MemoryMax/TasksMax. Host-deploy owns host-wide lane admission.

Do not share mutable attempts/generations between lanes. A lane deliberately rejects
a second unfinished pipeline while another lane, backed by a different state
directory, may prepare and execute independently. Archive-mirror is the intended
cross-lane source-byte cache.

## Remaining interactive/administrative work

The remote contract deliberately does not provide:

- host-level package installation or privileged shell access;
- root-control/systemd service administration outside finite build jobs;
- EC2 provisioning, stopping, rebooting or filesystem repair;
- replacement of uncertain controller submissions;
- automatic retries;
- network-enabled diagnostics.

Those remain host-deploy administrative operations and, until their gateway contracts
are implemented and accepted, may still require Work/live-host execution.

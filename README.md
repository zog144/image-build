# image-build

**Documentation:** [Technical manual](docs/image-build/README.md) · [Source traceability](docs/image-build/TRACEABILITY.md). The manual organizes current concepts; linked detailed sources preserve exact contracts and historical evidence.

Image-build constructs immutable root filesystem generations for Zog from reviewed
source recipes. It downloads and verifies inputs, orders package dependencies,
executes builds through box-control/root-control, validates outputs, and publishes
generations that box-control can launch. Host-deploy supplies AWS development
hosts; station-access can show the controller's build jobs and journal logs.

The implementation includes durable pipelines, resumable command identities,
reusable verified artifacts, and LFS-derived cross/native bootstrap stages from
an explicitly recorded Amazon Linux seed. **A complete self-hosted release image
is not yet accepted.** [CURRENT-STATUS.md](docs/image-build/CURRENT-STATUS.md) records the latest
checked-in compiler checkpoint; it is not a live job-status query. The accepted
temporary build environment and final Glibc work are different milestones. The
current tree also includes an explicit retained-build Glibc finalizer for staged
installation, merged-/usr composition, loader-cache generation and runtime checks;
it does not mark the complete compiler toolchain self-hosted.

## Install and inspect

Use Linux and Python 3.11+. Install from this repository:

```sh
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest
python -m zog.image_build --help
```

The package exposes Python modules, not an `image-build` console script. Source
inspection, metadata work and seed import do not require a running controller.
Build execution requires a compatible separately installed box-control,
root-control running independently on a systemd host, and a dedicated nonzero
build UID/GID. The caller needs access to the project and build-group files.
There is no direct shell, Docker or Podman execution fallback in the builder.

Box-control records an exact image-build dependency in its version-share handoff.
Use a reviewed compatible pair rather than assuming the latest revisions of both
repositories work together. Install a matching controller with
`python -m pip install -e /path/to/box-control/box-control`; this project does not
bundle that daemon. Host-specific backend patches under `handoffs/` are historical
integration inputs, not automatically installed dependencies.

## Project and package layout

| Path | Purpose |
| --- | --- |
| `src/zog/image_build/` | Engine, pipeline recovery, generation reader and controller adapter |
| `src/zog/image_build/developer/` | Host prerequisite planning, seed assembly and optional RPM research tools |
| `project/package/` | Package catalogue and reviewed source recipes |
| `project/bootstrap/` | Cross, temporary, native and final-stage plans |
| `examples/create_packages.py` | Generates a small library/executable recipe example |
| `tests/` | Local recipe, pipeline, artifact, cleanup and adapter tests |
| `jobs/` | Host-deploy development-job examples |

Package directories contain literal data in `sources.py`, `dependencies.py`,
`build.py`, `produce-manifest.py`, and optional `integration.py`. They are parsed,
not imported. Sources carry URL/checksum identity; build and runtime dependencies
are separate. Commands use explicit argument lists. Installation writes to the
output staging directory through `DESTDIR`.

Output manifests specify exact paths or allowed trees with required outputs.
Completed results retain exact inventories and hashes. Composition rejects
ownership conflicts and includes the requested packages plus runtime dependencies,
not every build dependency. Catalogue/research entries without reviewed recipes
are deliberately blocked from execution.

## Running a build

Use a deployment project beneath the controller user's home directory.
`--state-dir` is **PROJECT/state**, not PROJECT/state/image-build. Create an
explicit controller JSON file following
[controller integration](docs/image-build/CONTROLLER-INTEGRATION.md): project and socket paths,
execution UID/GID, resource limits, and startup/execution/caller timeouts are
required. The integration document's old source-directory names describe an
earlier bundle; the installable source now lives at this repository root.

```sh
# Import an explicitly prepared seed tree with a JSON provenance record.
python -m zog.image_build --package-dir PROJECT/package --state-dir PROJECT/state import-bootstrap SEED_ROOT provenance.json
# Compile and verify selected packages against that seed (no toolchain promotion).
python -m zog.image_build --package-dir PROJECT/package --state-dir PROJECT/state --controller-config controller.json verify-seed HOST_GENERATION package-name
# Ordinary image construction requires an accepted second-stage toolchain.
python -m zog.image_build --package-dir PROJECT/package --state-dir PROJECT/state --controller-config controller.json build TOOLCHAIN_GENERATION package-name
```

Upper-case paths and package names are deployment inputs, not supplied artifacts.
A generation argument names its manifest directory, not its `root/` subdirectory.
Importing a host seed does not make it a self-hosted source toolchain.

The staged LFS workflow starts with:

```sh
python -m zog.image_build.stages --project /absolute/bootstrap-project --package-dir /absolute/image-build/project/package --plan /absolute/image-build/project/bootstrap/lfs-cross.py --controller-config /absolute/controller.json --seed /absolute/seed-generation
```

Exit 75 means pending: repeat the same command to continue the recorded operation.
See [bootstrap stages](docs/image-build/BOOTSTRAP-STAGES.md) and
[native build environment](docs/image-build/NATIVE-BUILD-ENVIRONMENT.md) for subsequent stages,
verification and explicit failed-stage restart. These recipes currently target
x86_64; they are not a one-command generic distribution installer.

## State and recovery

Under PROJECT/state, `image-build/generations/` holds published roots and
manifests; `image-build/active` selects an application image.
`image-build/pipelines/` holds durable recipe/configuration snapshots;
`image-build/attempts/` retains work, controller checkpoints and failure evidence.
For provenance-enabled generations,
`image-build/build-record/observation-snapshots/` holds owner publication receipts
and the explicit selected canonical snapshot ID; the build-record content store is
never scanned to infer a newest/preferred snapshot. See
[canonical observation snapshot publication](docs/image-build/observation-snapshot-publication.md).
Stage-specific operation records bind their seed and plan. Keep these records
with their required inputs across caller restarts.

```sh
python -m zog.image_build --package-dir PROJECT/package --state-dir PROJECT/state inspect PIPELINE_ID
python -m zog.image_build --package-dir PROJECT/package --state-dir PROJECT/state --controller-config controller.json resume PIPELINE_ID
```

Resume uses recorded recipes and request identities. It validates retained
outputs before reuse; editing the original recipe does not retarget an existing
pipeline. A caller wait timeout does not cancel a build. Failed commands are not
automatically rerun. `release PIPELINE_ID` abandons continuation and releases
controller resources only after cleanup; it does not cancel a running command.
Inspect the failed attempt before release or an explicit stage restart.

The Python entry point is `ImageBuild(package_dir=..., state_dir=..., runner=...)`.
Its public operations include `import_bootstrap`, `bootstrap`, `ensure`,
`verify_seed`, `inspect_pipeline`, `resume`, `release_pipeline`,
`publish_observation_snapshot`, `selected_observation_snapshot`, and
`observation_snapshots`. Normal canonical generation publication creates an
initial owner-selected observation snapshot; explicit refresh can create a later
immutable snapshot without rewriting the generation or an earlier snapshot.
`read_selection(path)` verifies a published generation.
`zog.image_build.build_views.read_build_commands(attempt, after=None, limit=50)` maps
stages to controller job IDs for authorized log viewers. `ImageBuild(..., source_mirror=...)`
can inject archive-mirror transport explicitly; maintained workers may also use
`IMAGE_BUILD_SOURCE_MIRROR_CONFIG`.

## Application-software artifacts

Image-build now has the producer-side `applications-v1` contract for immutable
application software that will later be mounted read-only by box-control below
`/applications`. This lifecycle is separate from both rootfs generations and
persistent application data. See
[immutable application-software artifacts](docs/image-build/application-software-artifacts.md).

The Python API is `zog.image_build.application_software.ApplicationSoftwareStore`.
Callers build only into an unpublished operation root; finalization freezes the
complete installed-file inventory, source/provenance identities, notices and
compatibility requirements, then atomically publishes a content-addressed
`sha256:...` artifact. Controller consumers resolve an artifact ID through the
trusted local store rather than accepting a host path from an application.

## Remote/disconnected build operations

Image-build exposes a transport-neutral, versioned remote-operation adapter for
host-deploy and other trusted local callers. It binds every client operation to an
exact deployed repository revision before allocating controller work, persists a
pipeline identity before first execution, distinguishes pending/uncertain work from
terminal failure, supports explicit predecessor-linked retries, and returns bounded
machine-readable inspection summaries.

See [the remote operation contract](docs/image-build/remote-operations.md). Independent concurrent
builds use separate box-control Project/state directories on the same host; image-build
remains intentionally serialized within each lane.

## Tests and limits

With a compatible box-control importable, run:

```sh
python -m pytest -q
```

For source checkouts, set `PYTHONPATH=/path/to/box-control/box-control` if that
package is not installed. Tests use local fixtures and injected runners; one
small compilation test also needs host C/static-link tools. This suite does not
perform the full LFS bootstrap or prove upstream Glibc/GCC acceptance.

Source acquisition uses the verified local cache first. When configured, authenticated
archive-mirror providers are preferred for ordinary HTTPS sources before falling back
to the canonical recipe URL; see [archive-mirror source acquisition](docs/image-build/archive-mirror-sources.md).
Mirror transport never changes the canonical URL/SHA-256 source identity. Real builds need
substantial host disk, RAM and finite execution budgets. RPM/DNF assistance is
for developer-side seed/research work, not the runtime package manager.
New-format generation reclamation still needs a shared controller retention
contract; reaching the generation limit is not permission to delete referenced
inputs. Source signatures, reproducibility across independent full builds, and
a complete clean deployment remain release work.

## Maintained worker entry points

Use `python -m zog.image_build.worker --help` and the [worker guide](jobs/README.md)
for cross stages, fresh native stages, final Glibc, arithmetic and compiler operations. Runtime worker code
lives in `zog.image_build`; handoffs are historical evidence, not installed dependencies.
The maintained `native_tools`, `host_trust`, and `python_enrollment` workers
require explicit `--host-id` and `--project-id` provenance ownership inputs;
deployment identities are not defaults embedded in reusable source. Those values are
frozen into each worker intent, so recovery cannot silently substitute a different
owner. No box-control source is installed from this repository. The controller consumer
records the tested image-build revision in its version-share handoff.

Normal builds require the [monthly source pins](docs/image-build/MONTHLY-PINS.md). The active dated set is selected explicitly; new pipelines reject missing pins and recipe/source drift.

Build-trace consumers: [optional inspection contract](docs/image-build/build-trace-contract.md)
provides stable descriptions, redacted request summaries, retained controller
observations and explicit diagnostic/retry relationships. It does not change build
acceptance or authorize automatic recovery.


Collaboration handoffs and verification evidence are maintained in
private maintainer evidence archive (private maintainer evidence; not publicly linked).
See the 2026-10-02 artifact migration (private maintainer evidence; not publicly linked) for relocated reports and their original source revisions.

For required canonical package provenance, see the opt-in
[build-record integration](docs/image-build/build-record-integration.md). It freezes original
monthly pin/source/recipe materials before dispatch and binds successful or failed
results durably. This is separate from optional inspection capture.

### Catalogue host seed scope

Catalogue upstream archives use `release_url` (including pinned development snapshots).
Distribution mapping review is independent of a source build recipe. Profiles may
explicitly set `seed_required: False` with an empty `seed_packages` list when the
project is built from source after bootstrap. Host planning excludes those profiles;
it does not treat their RPM names as verified. All requested seed mappings still
require `repository-names-verified`. Catalogue `recipe-plan.py` remains inert
research; executable stage recipes and live acceptance are separate.

Integration consumers can use the versioned [observation export](docs/image-build/integration-observations.md)
for named installed verification, ELF/shebang interfaces, frozen package dependencies
and source-development identities. It is separate from regression analysis and
preserves explicit gaps in legacy evidence.

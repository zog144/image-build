# Maintained build workers

Install image-build and matching box-control/root-control from the exact pins in
reviewed public source pins and compatible component revisions and the consumer handoff. The controller daemon uses
the same pair. This source tree contains no runtime copy of box-control.

Run `python -m zog.image_build.worker --help` to list maintained workers. Each worker
accepts explicit paths and exposes its exact inputs through `--help`:

| Worker | Purpose |
| --- | --- |
| stages | Cross-stage plan execution from an explicit seed |
| native-stage | Fresh native-stage plan execution, including the final-start Glibc plan |
| glibc-final | Finalize an existing tested Glibc attempt; requires its recorded base/output |
| glibc-publish | Recover/publish a recorded prior Glibc finalization; not a generic fresh build |
| final-math | Build final arithmetic libraries from the selected base |
| final-compiler | Test tools, final Binutils/GCC, compiler checks and M4 acceptance |

For example, inspect `python -m zog.image_build.worker final-compiler --help`, then
supply --project, --catalogue, --controller, --selection, --arithmetic, --ownership
and --work. These are the actual existing worker arguments; no hidden compiler
host paths or generation IDs are substituted. Run the worker in a durable
host-deploy job or a supervised service with this installed Python environment.
The worker's operation directory is its identity: inspect its operation.json or
progress.json/result.json and controller checkpoints before retrying. No new retry or
cancellation behavior is introduced by this dispatcher.

The native-stage worker promotes the still-needed final-stage orchestration from
private maintainer archive / glibc-device-correction-pass2/final-stage-worker.py. It accepts explicit
--project, --catalogue, --plan, --controller, --selection and --work paths. For the
final-start stage, select project/bootstrap/lfs-final-start.py as --plan. It records
its input identity, locks the operation, returns exit 75 for a durable pending job,
and resumes on the same command; failed operations require review and completed
ones do not submit new work. A completed stage is not full self-hosting acceptance.

Earlier temporary/native/environment orchestration is maintained in
zog.image_build.temporary.run, zog.image_build.native.run and
zog.image_build.build_environment.run; those Python interfaces retain their existing
explicit path arguments. Seed tooling lives in zog.image_build.developer.

The remaining implementation already lives in image_build modules. private maintainer archive /  retains
historical drivers, copied test fixtures and patch evidence only. Do not import
or apply those as dependencies. Current root-control/build.py owns the private
null-device feature and ownership correction; do not apply the historical patches
over it. The older installed-host ownership-reclamation extension mentioned in
handoffs is not proven by local tests; deployment must still verify workspace
cleanup against the selected daemon.

This pass adds maintained entry points and native-stage resume/input-binding checks;
it does not claim fresh Glibc or compiler acceptance, change running jobs, or
replace their installed source. Existing job paths remain valid. See the current
source checkpoint separately from this reusable interface.


`gcc_pin_build.py` runs inside a controller-owned build job with its explicit
`--version`, `--sha256`, and `--jobs` arguments. Stage the matching archive under
`/image-build/source/gcc-VERSION.tar.xz` first. It creates fresh `pin-VERSION`
source/build and output directories, runs a checking-enabled C/C++ bootstrap,
then the two PR121298 regression cases before the full suite. Progress is retained
in the output directory; stdout/stderr flow to the controller journal. The
compiler retains default PIE/SSP; focused byte-swap commands use a neutral board; the full suite uses its normal board so explicit hardening tests can enable their required options.
Unexpected results fail the job even when make reports success. It never installs
or promotes a generation. Existing directories require inspection; do not replay
the worker as a recovery mechanism. Register/dispatch through box-control and
retain the exact source binding and request/job receipts.

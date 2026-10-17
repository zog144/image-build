# Completing the temporary native build environment

`zog.image_build.build_environment.run(project, catalogue, controller, selection)` expands an accepted `native-temporary-toolchain` selection. The supplied base must explicitly be source-built. It does not change the normal-build promotion boundary or the active generation.

The reviewed LFS 13.1-systemd plan is `project/bootstrap/lfs-native-environment.py`. Recipes live in each project's `stages/native-environment` directory. The graph resolves Python's Zlib/mpdecimal inputs and Texinfo's Perl input. Other basic build tools are provided by the accepted base generation. This is a staged bootstrap graph, not a distribution dependency solver.

Each source archive is pinned to SHA-256. The catalogue preserves distribution mappings and records verified secondary GitHub repositories separately from authoritative release archives. Package outputs are staged under DESTDIR and checked against output manifests. Perl manual-page paths and extensions are explicitly configured, because a minimal root may have no existing man-directory defaults. The shared Info index is omitted so independent packages do not collide on it.

The operation snapshots all recipes and binds the base, execution policy, acceptance commands and plan to its durable record. Individual commands use the existing box-control checkpoint adapter. On an interrupted wait, resume the same operation: it inspects the existing job identity before proceeding. A changed recipe or policy fails rather than silently reusing previous work.

After all packages succeed, their outputs are merged with the base into a recorded assembly root. A separate nonroot, network-disabled box-control job performs the checks in `project/bootstrap/native-environment-checks.py`. Publication records `build_environment_complete=True`, `source_built=True`, `self_hosted=False`. Completed resume validates the published selection and performs any pending assembly cleanup without compiling again.

Package source and private root workspaces are cleaned after successful output recording and controller release. A failed workspace is retained for diagnosis. Source archives, recorded installed outputs, immutable generations and journal references remain. Generation retention is explicitly capped at 16 for this bootstrap operation; that is a safety limit, not an automatic deletion policy.

The focused acceptance tests exercise generated Bison C code, Perl, Python AST parsing, decimal arithmetic, Zlib compression, subprocess execution, Gettext catalogue generation, Texinfo and Util-linux. Python intentionally lacks optional SSL and other modules at this temporary LFS stage. A final self-hosting rebuild and comprehensive upstream test suites remain separate work.

## Verified package reuse after a recipe correction

`zog.image_build.artifacts.import_completed(builder, pipeline_id)` imports only packages with validated completion records from an explicitly released pipeline. It checks the original recipe snapshot, execution policy, package identity, recorded outputs and resource release receipts. Rejected or incomplete packages are skipped. Imports are copied into a content-addressed artifact store; originals remain intact.

The engine may restore a package only when its full inputs match: recipe fingerprint, toolchain generation, dependency output identities, architecture and execution policy. It rechecks all cached file hashes. Changed recipes or policies cause a build; corrupted cached bytes are rejected. Restoration commits atomically and records the original pipeline/package in `artifact-reuse.json`, preserving the original job/log lineage.

This pass uses that path for seven accepted packages after correcting Util-linux's isolated staging directories. Util-linux is compiled again; its rejected output is never reused. The final combined acceptance runs against all eight installed packages.

### Native runtime refresh and application compatibility

`native_tools` assembles all retained package names plus the requested runtime
closure. A rebuilt package replaces the whole same-name output. It never overlays
new files onto an old generation, and build-only fixtures are excluded. Existing
roots and canonical per-package output/result bindings remain unchanged.

New native runtime generations freeze `application_software_compatibility` in both
the identity inputs and manifest. `rootfs_compatibility` derives CPython's exact
version/SOABI from selected installed headers/sysconfig metadata, verifies the
ELF architecture, and advertises reachable SONAMEs in `/usr/lib` and `/lib`.
It does not execute the inspected Python, import its sysconfig, search host
libraries, or infer ABI values from the controller's interpreter. Private plugin
SONAMEs are excluded. Unsupported or ambiguous Python metadata and incomplete
ELF inspection fail publication. Other producers must explicitly adopt this
contract before their roots can host application software; historical manifests
are not retrofitted. This conservative descriptor is an interface prerequisite,
not proof of live application acceptance or complete symbol-version compatibility.

Build dependency refresh also uses whole-package replacement. When a dependency
has the same package name as an output in the selected toolchain, its old identity
and `replace-inherited-package-dependencies-v1` policy are frozen in the consuming
package inputs and generation inputs. After copying the toolchain to a disposable
build root, all old files in the replacement set are checked against both the
selected generation inventory and actual staging bytes before anything is removed.
Unrelated files and shared directories remain. Shared non-directory ownership,
composed-file mismatches, changed files, unsafe parents and attempts to operate
on the retained root fail closed. The normal strict merger installs the new outputs.
This does not weaken the separate bootstrap sysroot replacement contract.
A changed composition policy requires a fresh attempt; completed dependencies with
unchanged package inputs/policy can be imported through the released-pipeline cache.


## Publish an accepted runtime as an application image

Native runtime/toolchain acceptance does not make a generation eligible for
box-control application launch. Use the explicit, inactive publication operation:

```sh
python -m zog.image_build.runtime_image --project /path/to/project \
  --selection /path/to/accepted/generation --work /path/to/runtime-image-operation \
  --base-components /path/to/exact-component-paths.json \
  --source-revision <exact-image-build-commit>
```

The component map must cover exactly the accepted runtime manifest's package
membership, including inherited components that are not standalone package attempts.
The operation verifies the canonical base graph, each package output and its
provenance, and the derived compatibility descriptor. It composes new bytes from
those outputs; only the declared empty application mountpoint directories may
be added. No package compilation or active-selection change occurs.

Both frozen inputs and the new manifest use `kind: image`. The descriptor is
bound into that identity and independently re-derived during publication. The
complete base canonical graph, including original installed verification, is
retained as the assembly material `accepted-runtime-provenance.json`;
`verification_inherited_from` identifies the accepted base. This does not claim
a fresh installed test or application launch. New assembly provenance and canonical
export are produced, and existing roots/manifests remain unchanged. Operation
inputs are frozen for replay. Consumers must check `published_selection` and
software-view compatibility before their separate live launch acceptance.

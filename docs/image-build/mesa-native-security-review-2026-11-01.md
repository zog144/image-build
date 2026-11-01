# Independent-style Mesa native evidence security re-review — source NO-GO for native authority

**Scope:** image-build PR #8, November 1, 2026. Review of the candidate
`tools/verify_mesa_native_evidence.py` and its synthetic test suite.
This source security review is a separate pass over the implementation, but
was conducted within the implementation channel; it is **not** an independent
human approval or a protected native attestation.

## Findings and corrections

| Finding | Original risk | Source correction and regression |
|---|---|---|
| NVE-1: forged but mutually consistent inputs | The entire captured source, binary and JSON envelope can be rewritten and rehashed by the submitter | Explicit positive-forgery regression proves the returned status remains `evidence-consistent-not-native-accepted`; three authorization flags are always false |
| NVE-2: incomplete compilation graph | A one-to-one relation between submitted compile commands and submitted maps did not detect omitted object files | Enumerate physical `.o`/`.obj` under the build root, require all to map, require `-MD -MF` depfile evidence for every compile and check hashed source/header inputs including system headers |
| NVE-3: unsupported linker inputs | Compile commands do not describe the separate link step; hidden archives/response files/scripts could escape mapping | Mandatory `link_commands` sidecar, checked linker bytes, exact object inputs and build-to-install ELF hashes; reject unsupported scripts, `.a`, response files, extra linker options and nonshared executable links |
| NVE-4: implicit loader dependencies | A reported DT_NEEDED library might load other libraries or carry an unreviewed PT_INTERP/filter directive | Reject path-containing DT_NEEDED, PT_INTERP, audit/filter tags, and unexpanded software-library provider DT_NEEDED/RPATH/RUNPATH; require modeled search reachability |
| NVE-5: path and symlink ambiguity | Roots could overlap; symlinks or library paths could resolve into a Host tree | Reject nested roots, hostile object/provider symlinks and missing/unreachable providers; validate installed leaves separately |
| NVE-6: original notice provenance | Copied notices may match a digest without binding that license record to the selected upstream archive | Require each `license.py` original member's source SHA-256 to equal the draft upstream pin; compare delivered bytes and all planned notice paths, preserving unresolved rights |
| NVE-7: blind trust in native capture | Hashing a mutable observation cannot establish capture provenance, execution completeness, actual ld.so resolution or archive rights | Remains blocked for protected root-control/host-install witness, independently validated original sources, complete linker/loader model and separate rights approval |

## Explicit unsupported inputs and future native witness requirements

The source verifier deliberately handles only narrowly described ELF64/LE
PT_DYNAMIC objects and shared links with individually hashed `.o`/ `.obj`
inputs. It rejects `PT_INTERP` (therefore actual glxgears/glxinfo executables),
ordinary static `.a` bundles without member-level evidence, linker scripts,
opaque response files, and unresolved transitive dynamic dependencies.
Native collector work must extend the evidence format with independently
authenticated toolchain root, build invocation, linker graph, generated-code
commands, source-to-object and archive-member membership, ELF interpreter,
actual runtime loader/cache/default-path resolution, and any legitimately
required command flags. Avoid changing this to a permissive passthrough.

The source tests intentionally create valid synthetic ELF bytes and a forged
source with updated hashes; passing those tests establishes **adversarial source
verification behavior**, not native compiler execution or rights clearance.
The collector's roots and sidecars are untrusted JSON, and independently
validated immutable installed bytes are still absent.

**Decision:** source hardening prepared, native authentication NO-GO, rights
NO-GO, canonical graphics recipe admission NO-GO. All six draft rights
records remain unresolved, no AWS jobs or protected Host changes were made,
and frozen Boot A source selection is unchanged.

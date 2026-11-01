# Mesa native build-evidence consistency verifier (source-prepared)

**Scope:** image-build PR #8; source review only. No native compilation, witness authentication, rights grant, canonical recipe admission or artifact publication is performed here.

`tools/verify_mesa_native_evidence.py` consumes an evidence bundle and the current noncanonical `project/graphics-drafts` contracts. Its only successful result is `evidence-consistent-not-native-accepted`; the JSON explicitly sets `native_accepted=false`, `source_archives_independently_accepted=false` and `redistribution_authorized=false`.

## Invocation

```bash
python3 tools/verify_mesa_native_evidence.py \
  --bundle /path/to/native-capture-bundle \
  --drafts project/graphics-drafts
```

The bundle contains `evidence.json` and eight separately SHA-256-referenced JSON sidecars named `compile_commands.json`, `source_objects.json`, `installed_inventory.json`, `elf_dependencies.json`, `library_provenance.json`, `delivered_notices.json`, `implicit_inputs.json`, and `link_commands.json`. The `evidence` object maps those keys to `{"file":"...","sha256":"..."}`. The envelope must have:

- `schema="zog-mesa-native-evidence-v1"`, `component` one of the six graphics drafts, `capture_status="untrusted-observation"`, and `source_archive_sha256` equal to that draft's immutable upstream pin;
- absolute existing `roots` for `source`, `build`, `destdir`, `software`; each is deliberately treated as supplied evidence rather than installation authority;
- an exact-path SHA-256 list `compilers` for the compiler programs used by `compile_commands.json`.

The verifier does **not** execute compiler or linker commands, fetch archives, invoke `readelf`, execute ELF, or use any privilege. The collector must supply an honest, complete immutable snapshot of actual native bytes: compiler executable(s), source and object files, installed DESTDIR, and every needed library under the approved immutable software root. The bundle's absolute roots are necessary references to captured bytes, not a reason to trust them.

## Sidecar contracts

| Sidecar | Required content and cross-check |
|---|---|
| `compile_commands` | Standard compilation database rows with `directory`, `file`, and exactly one of `arguments`/`command`, plus optional `output`; match normalized `-c` source and `-o` object to source-object map, with compiler byte hash and include/library path containment |
| `source_objects` | Full compilation unit map: `source_root` (`source` or `build`), source relative path/SHA, object relative path/SHA, generated input provenance; one-to-one with compilation commands and all physical `.o`/`.obj` files found in the captured build tree |
| `implicit_inputs` | One original or generated source dependency graph per compilation unit, checked against the actual full `-MD -MF` depfile bytes (not `-MMD`); source/header SHA-256 and approved root, with no Host implicit includes |
| `link_commands` | One captured shared-ELF link output per installed ELF, with exact linker, compiled object inputs, build-output and installed-byte digests; response files, static archives, linker scripts and opaque flags are held |
| `installed_inventory` | Complete DESTDIR leaf enumeration; exact installed-file digests and contained relative symlink targets; all expected binary/header/notice paths from draft manifest |
| `elf_dependencies` | Every physical installed ELF64 little-endian dynamic file; `DT_NEEDED`, SONAME, RPATH and RUNPATH cross-checked against the ELF program headers and dynamic strings in actual installed bytes, not merely a self-reported `readelf` result |
| `library_provenance` | One exact resolved byte digest per reported `DT_NEEDED` edge, rooted in captured `software` or `destdir`, with matching actual library SONAME; no Host library fallback in the conservative modeled lookup; a software-library provider with unexpanded transitive dependencies or search paths is rejected |
| `delivered_notices` | Exact planned notice-member path and installed-byte digest; compare against original archive-member SHA-256 in the draft's `license.py` evidence, requiring every planned notice and binding its license evidence to the same original source-archive SHA-256 |

A missing compilation unit, unreported ELF, extra installed output, wrong notice bytes, Host include paths, library-soname mismatch, symlink escape, tampered sidecar hash, and bundle-supplied approval are negative cases. The test fixture generates tiny synthetic ELF64 PT_DYNAMIC bytes and deliberately *recalculates* sidecar SHA-256 after many tampering changes so the verifier must detect semantic inconsistencies.

## Production capture/acceptance boundary

1. **Native source:** independently verify exact upstream archive SHA-256, original notices, and any selected patches; the bundle's assertion of a pin is not proof.
2. **Native installation and execution:** a protected host-install/root-control witness must bind a genuine installation ID/generation and protected compiler/software root, immutable build source, namespace and execution identity, capture time, and a complete immutable manifest of the observed files. An attacker-provided bundle, even if internally consistent, cannot establish this.
3. **Compiler and linker provenance:** collect the complete build graph, command expansions and response files, generated-source transformations, static archives, scripts, compiler startup/system headers, implicit link dependencies and actual ELF loader resolution. The current verifier deliberately rejects opaque linker paths and unsupported ELF formats rather than claiming broad coverage.
4. **Complete dynamic and distribution inspection:** reconcile real installed outputs against the entire dependency closure and per-file rights, including bundled LLVM BLAKE3, Mesa's generated GLAPI, disabled sources, and all delivered notices. The limited current notice delivery plan is not a legal clearance.
5. **Separate authorization:** actual native acceptance, original-source/patch verification and independent redistribution rights require their own independently signed evidence and explicit authorization. Do not promote any of the six graphics drafts to `project/package` or modify frozen Boot A pins on this source-only result.

The synthetic evidence fixtures intentionally prove nothing about an EC2 compiler, native installed artifacts, or graphics operation. They test the verifier and its fail-closed behavior only. Eventually, a low-cost Xvnc/noVNC `glxgears` smoke can validate graphical operation after the independent native and rights gates pass; no FPS threshold.

## Additional fail-closed review restrictions

The source verifier now rejects overlapping capture roots, unexpected build objects,
unrecorded implicit compiler inputs, `-MMD` depfiles that exclude system headers,
unexpanded linker archives/response files/scripts, extra linker input objects,
path-bearing `DT_NEEDED` entries, ELF audit/filter tags, and unverified `PT_INTERP`.
It models only a bounded subset of compiler/linker invocations and ELF64 little-endian
shared objects; actual glxgears/glxinfo executable loader selection and real LLVM/Mesa
static-archive links remain **native collection/provenance work**, not a source PASS.

A self-consistent forged source tree, depfile, compiler output, linker output,
DESTDIR inventory and sidecar digest set can still satisfy these checks.
The regression `test_forged_self_consistent_source_is_not_authenticated`
deliberately demonstrates that limitation. The caller must never infer a native
authority, verified source code provenance or redistribution rights from a
successful consistency result. The native witness must establish the selected
installed-generation root, immutable capture, actual compiler execution, and
reproducible link/loader closure independently.

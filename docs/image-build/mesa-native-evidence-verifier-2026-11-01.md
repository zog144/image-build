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
| `link_commands` | Captured shared-ELF link output, approved linker bytes, independently compiled `.o` inputs, complete optional bounded classic ar archive-member inventory and selected-member assertions, plus byte-matched one-level response-file expansions; linker scripts, unknown flags and nonshared links remain held |
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


## Bounded static archives and linker response files (2026-11-02)

`link_commands` retains the original `installed_path`, `output`,
`output_sha256`, `arguments` and `inputs` fields. The extended form
adds **both** `archives` and `response_files` (empty arrays are permitted).
The response-file record has exact keys `path` (relative to captured build root),
`sha256` (of the actual file bytes) and `arguments` (tokens that must match
`shlex.split` of those exact bytes). Only a single layer of `@path` is
supported; references must be unique, every declared response file must be
used, and nested files, shell interpolation, byte escapes, unreadable files
or Host paths are rejected. This source parser models a deliberately bounded
POSIX-style token grammar, not every GCC/Clang response dialect.

The archive record has `path` (relative `.a`), `sha256` (whole ar file)
and `members` (the **complete** file-ordered member inventory).
Each member requires `name`, `sha256`, `object` (source-derived
captured `.o`/ `.obj` file), `object_sha256` and a boolean
`selected`. The original ar member bytes must equal that exact compiler
object's bytes. A claim that a member was selected is **not** a proof of what
the linker actually loaded. In this revision classic **non-thin** ar with
short regular object member names is supported; the optional GNU symbol
index is covered by the whole archive digest. GNU extended-name tables,
BSD names, thin archives, nested archives, scripts, inferred link search and
non-object members are held for separate native extension. Every referenced
archive must be recorded, and every record must correspond to an actual
link input.

The synthetic tests exercise legal bounded captures and hostile modified
member bytes, missing or duplicated members, missing/unused response files,
nested response files and apparent selected-member claims. They also
intentionally forge a complete depfile and its digest while omitting an actual
header: consistency **can** still pass and must not become acceptance.

**Authentication boundary:** all response-file and archive hashes originate
from the submitted capture. The verifier checks their relationships; it does
not authenticate their origin, that they were actually supplied to a genuine
linker, or that the reported selected members are complete. Before native
admission, root-control/host-install must independently witness the
installation/generation, exact command and working directory, captured bytes,
actual ar-member selection, linker-driver toolchain (including defaults),
full source/header closure, loader resolution and immutable capture identity.
Selected-source licensing and redistribution authorization remain separate
NO-GO gates.

# Mesa evidence verifier separate source re-review and bounded link extension

**Date:** 2026-11-02. **PR:** [image-build #8](https://github.com/zog144/image-build/pull/8).
**Baseline:** `e7de6687b9f7a576ef65b788e203f66f8d8c10c1`.
**Authority:** source verification only; NOT an external human approval, native
attestation, or redistribution rights grant.

## Re-review of the hardened verifier

The original eight-sidecar consistency design correctly **does not** grant native
acceptance. Its submitted archive pin, compiler paths, source maps, hashes, root
paths and notices are self-reported bytes. A malicious author can forge all of
them consistently; this is intentionally demonstrated in tests.

Findings and improvements:

1. **Archive selection completeness:** a normal `.a` is not a single object.
   Earlier source checks rejected it entirely. The bounded extension reads
   the real captured ar bytes and compares every regular member, in order,
   to an explicitly hashed source-derived object. Missing/extra members,
   changed member bytes and duplicate member identifiers are rejected.
   The claimed selected subset remains untrusted without an actual linker
   trace, symbol resolution and independent native witness.
2. **Link response expansion:** earlier opaque `@file` inputs were denied.
   The extension checks the captured file's exact SHA-256, constrained parser
   output and declared tokens, with no nested references, response paths
   outside the build root or unused files. A valid source-hash relationship
   cannot authenticate who supplied or executed those contents.
3. **Compiler inputs:** `-MD` depfile and source-object map checks catch
   reported mismatches and extra physical objects, but cannot detect a
   successfully forged depfile that suppresses a real header. Native
   environment/command attestation and exact immutable source/headers remain
   required.
4. **ELF/loader:** existing limited ELF64/PT_DYNAMIC checks deny unexpanded
   interpreters, filter/audit tags, Host search paths and unresolved external
   transitive dependencies. No real `ld.so` selection, executable acceptance,
   static link driver default flags, plugin inputs or split-debug dependencies
   have been established.
5. **Filesystem paths:** realpath containment and hashed bytes reject many
   symlink and Host escapes, but live mutable-file TOCTOU is not excluded by
   source tests. Authenticated immutable capture (or descriptor-based native
   reader) remains essential.
6. **Notices:** delivered original-archive member hashes and selected
   `license.py` source SHA binding check only listed notices. Generated code,
   bundled third-party notices and actual per-output attribution still require
   independent rights work.

## Tested boundaries and remaining hold

The new bounded positive fixtures have classic ar byte headers and a one-level
byte-verified response file, with strict source-derived object provenance.
Tampered cases cover missing or altered members, thin archives, false
selected-member lists, omitted/changed response files, nested references,
and a forged internally consistent depfile.

**Native acceptance NO-GO:** authentic linker invocation, ar selection,
GNU/BSD extended archive formats, legitimate unmodeled GCC/Clang options,
linker scripts, full ELF executable/loader/recursive closure, system-default
search paths, complete native output byte provenance and original release
sources are not independently witnessed. Separate human security and
component-rights approval remain outstanding. All six graphics drafts stay
unresolved and outside canonical package admission; frozen Boot A inputs,
AWS execution and publication are unchanged.

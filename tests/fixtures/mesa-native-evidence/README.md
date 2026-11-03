# Synthetic Mesa native evidence fixtures

The pytest fixture builder in `tests/test_mesa_native_evidence.py` constructs
small, real ELF64 little-endian PT_DYNAMIC binaries, a synthetic compiler
byte file, source/object maps, a DESTDIR tree, signed-by-nobody JSON manifests,
and a matching source-only draft rights contract.

`tamper-cases.json` enumerates independent corruptions; for many tests the
JSON sidecar SHA-256 values are recalculated after corruption to prove that
internal SHA consistency cannot substitute for evidence agreement. There are
**no genuine native build receipts, upstream release archives, or redistribution
approvals in this directory**. Fixture validation must always emit
`evidence-consistent-not-native-accepted` on the positive case.

The security review fixture `tests/test_mesa_native_security_review.py` adds
forged-but-internally-consistent captures, extra physical objects, full compiler
depfile coverage, unapproved implicit headers, unsupported linker flags and
archives, hidden transitive ELF dependencies, `PT_INTERP`/filter directives,
unreachable library providers and object/library symlink escape tests.

The source verifier's expanded eight-sidecar protocol is deliberately narrower
than production Mesa/LLVM: it refuses link archives, runtime executables and
opaque compiler options until the native witness supplies separate supported
evidence. The positive synthetic case is not a native installation receipt.

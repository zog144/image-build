# Synthetic Mesa native evidence fixtures

The pytest fixture builder in \`tests/test_mesa_native_evidence.py\` constructs
small, real ELF64 little-endian PT_DYNAMIC binaries, a synthetic compiler
byte file, source/object maps, a DESTDIR tree, signed-by-nobody JSON manifests,
and a matching source-only draft rights contract.

\`tamper-cases.json\` enumerates independent corruptions; for many tests the
JSON sidecar SHA-256 values are recalculated after corruption to prove that
internal SHA consistency cannot substitute for evidence agreement. There are
**no genuine native build receipts, upstream release archives, or redistribution
approvals in this directory**. Fixture validation must always emit
\`evidence-consistent-not-native-accepted\` on the positive case.

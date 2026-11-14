# Data only; parsed with ast.literal_eval.
{
  "project": "libdrm",
  "stage_id": "final",
  "base_contract": "Source-built Zog userspace libdrm; do not grant /dev/dri or import distribution libraries.",
  "native_admission": "HOLD exact archive and notice closure, build/install output proof",
  "unresolved": [
    "Original COPYING/notice hashes",
    "Exact libdrm.so and pkg-config ABI path",
    "Check Mesa requires only core libdrm, no hardware APIs"
  ]
}

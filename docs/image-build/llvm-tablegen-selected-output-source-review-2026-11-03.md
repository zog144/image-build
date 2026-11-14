# LLVM 21.1.6 TableGen installed-output source correction — 2026-11-03

**Scope:** image-build PR #8 draft graphics catalogue; no change to the selected LLVM 21.1.6 original source SHA-256 `908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad`, Mesa 25.3.0 source, or inherited source/runtime generations. No native compilation, accepted executable, distribution authorization or active task catalogue change.

## Original LLVM target review

The upstream `llvmorg-21.1.6` source `llvm/utils/TableGen/CMakeLists.txt` (Git blob `67291214c14e605eaade5eea3a4b3aa215772968`) explicitly defines `add_tablegen(llvm-tblgen LLVM ... DESTINATION "${LLVM_TOOLS_INSTALL_DIR}" ... DEPENDS intrinsics_gen)`. [View upstream TableGen CMake source](https://github.com/llvm/llvm-project/blob/llvmorg-21.1.6/llvm/utils/TableGen/CMakeLists.txt). This corroborates that the upstream selected-version project supports the `llvm-tblgen` target. This tagged Git blob is corroborating source context, not an independently attested hash of the compiled native executable or of that exact member inside the separately SHA-pinned release archive.

The existing LLVM X86/RTTI/shared-library CMake flags and original notice-member hashes are unchanged. Its source recipe now explicitly:

1. Builds `llvm-tblgen` with `cmake --build build-llvm --target llvm-tblgen --parallel 2` before the existing all-target build.
2. Requires `build-llvm/bin/llvm-tblgen` in the test stage, alongside the existing LLVM 21.1.6 X86, shared-library, RTTI and `llvm-config` checks.
3. Stages that exact selected build-tree executable under `$DESTDIR/usr/bin/llvm-tblgen` with `install -Dm755`, then requires its executable output and the existing `llvm-config`, `libLLVM.so`, LLVM LICENSE.TXT and BLAKE3 LICENSE outputs.
4. Expands the LLVM original rights/output matrix consistently, without claiming real installed object bytes or new rights approval.
5. Requires `/usr/bin/llvm-tblgen` in Mesa's selected source configure step **in addition to** the already-authored protected graphics toolchain verifier, `llvm-config` X86/RTTI/shared-mode and required `llvm-final` predecessor.

The actual native worker must independently prove that this TableGen binary came from the selected authenticated LLVM stage, verify its ELF/loader provenance and all generated-header input/output digests, and reconcile the compiled LLVM/Mesa source and original rights notices. A `test -x` assertion in a draft source recipe does **not** establish tool provenance; only a protected native installed-generation witness can.

## Source CI and deliberate NO-GO

`tools/verify_llvm_tblgen_source.py` and `tests/test_llvm_tblgen_source.py` reject a missing TableGen target build, absent test/install command, missing required output/notice, substituted Mesa tool or unselected LLVM dependency, and premature rights/native claims. This source gate remains separate from native build submission. The PR #8 LLVM source stage is still `catalogue-only`; the independent current host-deploy PR #19 continues to pin the **earlier** immutable PR #8 input `9cbd652226b863a7b4bb2d6d9539722e1a262508`. Its existing `llvm-tblgen` production HOLD must remain until a future separately reviewed exact source repin; do not silently change protected selection.

**Disposition:** selected LLVM TableGen output obligation resolved in source, installed bytes and native admission **NO-GO**.

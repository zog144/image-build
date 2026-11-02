# First Workspace source-to-native and original rights handoff — 2026-11-02

**Boundary:** source-prepared, *not submittable*. No native generation, compiler invocation, signed authority, redistribution approval, or installed byte evidence is created. Source PR #9 is held independently from Mesa PR #8.

## Source-to-native contract

Machine-readable exact-source checklist: `project/graphics-first-workspace/source-to-native-handoff.json`. It identifies Workspace PR #9 reviewed source snapshot `db13d73a45f8a3be579226656442c331a9f701ea` and Mesa PR #8 source revision `9cbd652226b863a7b4bb2d6d9539722e1a262508`. These are **reviewed input revisions**, not published package generations. PR #9 changes after this review require a new exact-source reconciliation before native scheduling. Its frozen generation slots are null, intentionally.

The planned order is fonts → XCB → X11, plus LLVM → Mesa software GLX → Xvnc/i3/xterm → mesa-demos Workspace smoke. Fonts and XKB data are also prerequisites of Xvnc; LLVM and Mesa may be compiled after X11 in dependency order, but Mesa must precede any Xvnc software GLX acceptance. Acquire protected accepted-generation receipts for the fonts, XCB and X11 producers, separately for inherited `zlib-native-environment` and `ncurses-temporary`, and separately for Mesa. Preserve distinct *source pin*, *package stage*, *compiler output*, and *accepted generation ID*. Do not insert a plausible generation ID into source CI.

Verify source-built tools, generator inputs/outputs, selected package-config roots, libX11/libxcb and XKB data, xkbcomp and 6x13 font output, xterm terminfo and app-defaults, CMake/Meson configuration, headers, ELF dynamic dependencies and immutable notices with the trusted native worker. Signed stage grants, independently accepted authority/checkpoint state and exact provenance remain required before submission. The current GitHub Actions job rejects fabricated receipts and missing source obligations. `tools/verify_workspace_native_handoff.py` deliberately refuses native readiness even when someone inserts superficially plausible SHA-256 receipt strings: source CI is not a protected trust verifier. The exact reviewed PR #9 snapshot predates these handoff-only commits; the eventual compiler grant must freeze a new exact PR #9 candidate head and externally authenticate it.

## Original-source component rights matrix

| Scope | Original source/notice evidence already in review | Remaining required evidence and admission decision |
| --- | --- | --- |
| TurboVNC 3.3.1 main | Original pinned tarball and `LICENSE.txt`; primary CMake member hashes | Actual CMake configure, copy/installed paths, compiled objects, NOTICE mapping; **HOLD** |
| Bundled Xserver | `unix/Xvnc/programs/Xserver/COPYING`, original Xserver CMake/GLX feature guards | Enumerate all selected Xorg subdirectories and inherited notices, generated Xserver files, and object-to-source map; GLX `glxdriswrast.c` remains selected; **HOLD** |
| Bundled libsha1 | Original `unix/Xvnc/lib/libsha1/COPYING` hash, selected CMake `add_subdirectory(libsha1)` | Independently inspect per-file notices, actual linked objects and installed notice bytes; **HOLD** |
| Bundled zlib-ng | Original `unix/Xvnc/lib/zlib-ng/LICENSE.md` hash; `TVNC_ZLIBNG=OFF` | Prove zero compiled/link inputs from bundled zlib-ng and source-backed inherited Zog zlib; archive presence alone is not inclusion; **HOLD** |
| DRI3 / PAM / device features | Source conditionals and explicit `TVNC_DRI3=OFF`, `TVNC_USEPAM=OFF` | Actual compile/link exclusion and absence of unauthorized device access; software GLX and `glxdriswrast.c` cannot be called absent; **HOLD** |
| LLVM 21.1.6 | `LICENSE.TXT`, Support notice, `lib/Support/BLAKE3/LICENSE`; BLAKE3 and TableGen sources | Determine BLAKE3 object inclusion and generated tables/templates, selected RTTI/shared ABI and notice delivery; **HOLD** |
| Mesa 25.3.0 GLAPI | `docs/license.rst`, original `src/mesa/glapi/glapi/gen/license.py` hash | Track generator scripts/templates and *generated* GLAPI file provenance into compile/link manifests, deliver applicable notices; **HOLD** |
| Mesa llvmpipe / GLX | Original `lp_screen.c`, GLX Meson graph and source hashes | Confirm llvmpipe/LLVM swrast objects, runtime `swrast_dri.so`, linked `libGL.so`, actual loader resolution and copied notices; **HOLD** |
| Mesa excluded Vulkan / imgui | Original excluded subtrees present; source selection policy excludes Vulkan | Prove absence from compiled/linked bytes; do not treat archive presence as feature activation; **HOLD** |
| libdrm common and KMS | Original `xf86drm.c`, `xf86drmMode.c` and headers pinned | Prove enabled common code and excluded vendor/device/udev paths through actual object and device access evidence; **HOLD** |
| mesa-demos `glxgears` / `glxinfo` | Original two C files SHA-256 checked | Independently classify per-file copyright/public domain declarations, compile/link only selected programs, deliver notice bytes; **HOLD** |

The machine-readable source-byte inventory `project/graphics-first-workspace/selected-component-rights-handoff.json` additionally pins nine individual original archive members (including LLVM BLAKE3, Mesa GLAPI/llvmpipe, libdrm and two demos). Its offline CI checks compare TurboVNC member evidence against the actual PR #9 license records and bind Mesa rows to frozen PR #8 original-source checks; it does not impersonate Mesa's existing eight-sidecar verifier.

This table is **a review questions inventory, not a legal clearance or a claim about native inclusion/exclusion**. Authoritative detailed originals remain `docs/image-build/turbovnc-bundled-selected-feature-review-2026-11-02.md` in PR #9 and `docs/image-build/mesa-original-rights-questions-2026-11-02.md`, `project/graphics-drafts/rights-admission-evidence.json` and the eight-sidecar native verifier in PR #8. The eventual independent reviewer must make component-level rights decisions against exact installed-generation evidence.

## Acquisition repair

GitHub Actions run 41536678728 failed **before** SHA-256/notice inspection: author URL `https://invisible-island.net/archives/xterm/xterm-412.tgz` returned HTTP 403. The independently documented upstream mirror URL `https://invisible-mirror.net/archives/xterm/xterm-412.tgz` is a transport fallback only. Keep pinned SHA-256 `b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6` and `inspect()` original metadata and notice checks. A mismatch, oversize input or malformed tarball **fails**, never triggers source substitution. CI must rerun after this commit before a PASS is claimed.

## Negative native admission decision

All required graphical generation receipts (fonts, XCB, X11, LLVM, Mesa, inherited zlib and inherited ncurses) remain `null`. They must be replaced only by genuine source/manifest-bound, independently verified protected receipt references when scheduling is separately authorized, **never** by a guessed UUID, plain SHA string or a GitHub source check. The source CI contains no external native approval mechanism and intentionally returns `native-readiness DENIED`.

The selected CMake Xvnc profile disables DRI3/PAM/zlib-ng but retains software GLX. Actual compile/link commands, source-generated headers, installed ELF dependencies, and runtime VNC loader paths are required before calling any component selected or excluded in native bytes. No approval for external source redistribution is inferred from copied original notices.

# Remaining original-source and distribution-rights evidence — 2026-11-03

**Scope:** supplementary source-only review for image-build PR #9, pinned input `6b64a7e1b6f9842554bd3b9eee5599e24ca2402c`, and Mesa PR #8 `9cbd652226b863a7b4bb2d6d9539722e1a262508`. This review does **not** repeat original archive acquisition or SHA-256 inspection, accept compiler objects, certify installed notices or authorize redistribution.

The exact reviewed archive-member hashes and planned notice destinations remain those in `project/graphics-first-workspace/selected-component-rights-handoff.json`. The supplementary per-component obligations are in `project/graphics-first-workspace/remaining-distribution-evidence-2026-11-03.json`, checked by `tools/verify_remaining_graphics_rights.py` and targeted omission tests.

| Component | Specific next generated-code and native-selection evidence | Distribution obligation not yet discharged |
| --- | --- | --- |
| TurboVNC bundled Xserver | Actual Xorg/Xserver generated protocol header inputs/output hashes, selected GLX `glxdriswrast.c` objects; prove DRI3 and hardware-facing code exclusion from native link, not just CMake flags | Trace every selected subdirectory/file attribution to original COPYING and installed Xserver-COPYING bytes |
| TurboVNC libsha1 | CMake-selected libsha1 originals, selected object/archive-member evidence; determine if generated files were used | Map per-file copyrights to original bundled COPYING, then installed copy bytes |
| TurboVNC bundled zlib-ng | Show zero bundled objects and headers used; show inherited Zog zlib provenance in real linking/loader | Upstream bundled LICENSE.md was observed, but declared OFF is not proof of compiled exclusion; no installed zlib-ng notice is planned |
| LLVM BLAKE3 and TableGen | X86 TableGen `.td` source, llvm-tblgen executable, any actual `X86Gen*.inc` outputs and selected link objects; independently prove whether BLAKE3 is linked | LLVM LICENSE.TXT plus BLAKE3 original LICENSE native delivery and per-file scope |
| Mesa GLAPI generator | GLAPI Python generator, original scripts/templates including `src/mesa/glapi/glapi/gen/license.py`, emitted C/header hashes, compile commands, actual `libGL` source closure | An original copied `license.py` source file is **not itself** a blanket right to generated outputs; reconcile full notices |
| Mesa llvmpipe/GLX | Linked `lp_screen.c` and Gallium output to `swrast_dri.so` and LLVM ABI; verify Vulkan/EGL/GBM/imgui exclusions from actual native objects | Original Mesa license, generated Gallium attribution, installed linked dependencies and notice copies |
| libdrm | `xf86drm.c`, `xf86drmMode.c` actual object mapping and generated config; vendor/udev/device-access boundaries | Per-file header/source rights and declared installed source notice files |
| mesa-demos `glxgears` | Exact `glxgears.c` native compile/link and no unrelated demos, or selected generated input mapping | Independent per-file public-domain/copyright determination; copying source into a notice directory is only evidence delivery |
| mesa-demos `glxinfo` | Exact `glxinfo.c` native compile/link and no unselected demos | Independent per-file rights decision and installed source/notice bytes |

The source gate rejects missing generated-code attribution, missing link/inclusion decisions, unexamined device exclusions, omitted demo copyright questions, source-hash/notice-path substitution, and attempts to claim a native generation, installed notice bytes or rights approval. All original hashes are inherited from the previously reviewed immutable original-source matrix, not freshly asserted by this review.

**Native handoff required:** a protected compiler witness must deliver actual compile/link, generator/input/output, selected archive-member and installed manifest evidence. Independent rights-holder permission and third-party notice delivery approval remain a separate, explicit authorization step. `rights_approved=false`; graphics generation release **NO-GO**.

# Independent first-Workspace source and rights audit — 2026-11-03

Scope: PR #9 source-only handoff and exact immutable PR #8 candidate `9cbd652226b863a7b4bb2d6d9539722e1a262508`. **Not** native admission, a signed predecessor grant, a compiler submission, source distribution approval, or evidence that installed objects exist.

## Review outcomes

**Source DAG:** The handoff's coarse producer stages require fonts and XKB resources before Xvnc, XCB before X11, LLVM and X11 before Mesa, Mesa before Xvnc software GLX, and a later mesa-demos smoke. The independent `review_local_stage_closure` gate now reads actual source stage `build` and `runtime` dependencies for i3, xterm and Xvnc. It refuses removed `mesa-final`, `xkbcomp-final`, `libxkbcommon-final`, `zlib-native-environment`, `ncurses-temporary` or `basic-font-final` references. This is not evidence of accepted producer generations.

**Inherited provenance:** zlib is referenced by its real `zlib-native-environment` stage and ncurses by `ncurses-temporary`, never fictional `*-final` stages. All inherited generation slots remain `null`; compiler selection requires separately authenticated, immutable accepted receipts for fonts/XCB/X11/LLVM/Mesa plus their actual inherited sources. An XKB package may be included in a later authorized generation, but the tool and XKB data path must be source/manifest-bound to the generation that supplies them; neither a workstation `/usr/bin/xkbcomp` nor a Host fallback may be inferred.

**Tool and resource provenance:** C/C++/linker/Binutils, CMake/Meson/Ninja/pkgconf, selected Python generators/templates, llvm-tblgen and XKB/font tools need protected exact input origins, not a mere tool name. Expected outputs now include every declared output of the local i3, xterm, Xvnc, xkbcomp, xkeyboard-config and basic-font stages, including `usr/share/X11/xkb`, `6x13.pcf.gz`, `fonts.dir`, XTerm app defaults, terminfo and selected original notices. Generated headers, linker/ELF closure and packaged dynamic lookup remain native obligations.

**Authority:** The source handoff rejects unknown success or approval fields (e.g. `native_ready` and `accepted_generation_id`), non-null and forged-looking generation receipts, omitted predecessor resources and premature package statuses. Even syntactically correct signed-looking receipt objects never confer trust through source CI. The separate protected compiler/authority/checkpoint verifier must read genuine receipts and freeze the exact *later* PR #9 source revision before job admission.

## Independent selected-source rights audit (task 5)

Original archive inspection and SHA-256 observation were **not** rerun. The existing rights matrix was reconciled with the actual TurboVNC local license record, and the selected LLVM/Mesa/libdrm/mesa-demos license and `produce-manifest` blobs at frozen PR #8 revision. `verify_first_workspace_source_branches.py` binds those extra immutable Git blob identities and requires **complete** source-member SHA-256 equality (not digest prefixes). Mesa `lp_screen.c` is bound to the original scoped-source candidate record, separate from license.py's notice entries.

| Component boundary | Evidence role | Planned output and remaining HOLD |
| --- | --- | --- |
| TurboVNC bundled Xserver | Original Xserver `COPYING` | `turbovnc/Xserver-COPYING`; selected Xorg subdirectories, generated sources, `glxdriswrast.c`, actual link list unobserved |
| Bundled libsha1 | Original `COPYING` | `turbovnc/libsha1-COPYING`; source-to-object mapping unobserved |
| Bundled zlib-ng | Original `LICENSE.md`, proposed *excluded* feature | No selected installed zlib-ng notice output; prove bundled zlib-ng absent from linked objects and inherited Zog zlib used |
| LLVM/BLAKE3 | Original BLAKE3 LICENSE and LLVM notice | Planned `BLAKE3-LICENSE`/LLVM notices; TableGen generated code, actual BLAKE3 linkage, installed byte proof unobserved |
| Mesa GLAPI | Generator source `license.py` | Planned `glapi-generator-license.py`/Mesa license; original generator scripts/templates and emitted C/header/notice mapping unobserved |
| Mesa llvmpipe | Original C source `lp_screen.c`, **not** a standalone rights grant | Planned Mesa license; swrast/GLX object-to-source and software loader closure unobserved |
| libdrm | Original `xf86drm.c` source | Planned two original-file notice outputs; KMS/common object selection, vendor/udev exclusions and original attribution unobserved |
| mesa-demos | Original `glxgears.c` and `glxinfo.c` files | Planned file attribution delivery; independent public-domain/copyright determination and only-selected compile/link evidence unobserved |

The distinction between **an original C/generator source file**, **an original license/notice file**, **a source-declared installation path** and **a verified installed notice** is enforced in the matrix. A declared output path is *not* evidence that any output was built. Negative CI cases refuse altered original SHA-256s, swapped source roles, missing notice outputs, bogus installed notice claims and rights approval flags. The separate PR #8 eight-sidecar protected native verifier remains untouched.

**Decision:** source handoff and evidence consistency reviewable; native generations/selected compiled objects not accepted; redistribution and independent copyright-holder authorization still **HOLD**.

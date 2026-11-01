# Mesa llvmpipe source-contract checkpoint — November 2026

**Source drafts only; no native compilation or admitted monthly recipe snapshot.**
The canonical October Boot A source pin is unchanged. `project/pins/2026-11-01/graphics-source-pin.py`
is a standalone supplementary pin ledger, not an authorized producer monthly snapshot.

| source | exact archive SHA-256 | purpose |
| --- | --- | --- |
| LLVM 21.1.6 | `908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad` | X86 JIT, shared LLVM library |
| Mesa 25.3.0 | `0fd54fea7dbbddb154df05ac752b18621f26d97e27863db3be951417c6abe8ae` | Gallium swrast/llvmpipe, X11 GLX |
| mesa-demos 9.0.0 | `3046a3d26a7b051af7ebdd257a5f23bfeb160cad6ed952329cdff1e9f1ed496b` | standalone glxgears, glxinfo |

Pins are from the LLVM GitHub release digest, Mesa upstream release notes
and independent maintained Yocto mesa-demos source checksum, respectively.
The pinned archives and selected archive-internal license/notice members have
been SHA-256 checked by GitHub Actions. These hashes establish the identity of
selected evidence, **not** complete component rights or redistribution approval.
The six draft `license.py` records use canonical schema and remain
`status='unresolved'`.

The finite intended build contract is: LLVM X86 shared/RTTI, bounded two-job
CMake/Ninja; Mesa Gallium `swrast` with LLVM enabled and `glx=dri`, X11
platform, GLVND/EGL/GBM/Vulkan/Wayland/GPU drivers disabled; no
kernel DRM device or DRI3 hardware capability is granted. Mesa 25.3.0 no
longer exposes the obsolete `-Ddri3` Meson option. The demo profile builds
only `glxgears` and `glxinfo`. These typed source recipes are not
assertions that exact upstream 25.3.0 Meson options and build targets
were successfully executed. The GPU-free swrast DRI module does **not**
authorize any kernel DRM device.

**Native/source-admission blockers:** compile the now-pinned libdrm,
libxshmfence and libXxf86vm sources (userspace libraries do not authorize
/dev/dri), close the source-pinned Mako/PyYAML/MarkupSafe/PEP-517
build-only chain, and verify the LLVM 21.1.6/Mesa 25.3.0 native
shared-library ABI, installed file paths, complete source/component rights
and runtime ELF/driver/GLX loader closure,
and immutable `applications-v1` publication. Host GL and LLVM fallback
are forbidden. Do not expand Basic/console-first rootfs.

**Minimal native acceptance:** launch Zog-built `glxgears` from the
immutable software view inside a TurboVNC/Xvnc Workspace presented through
station-access/noVNC; briefly observe animated gears without client/X
server crash. Capture `glxinfo -B` optionally and confirm llvmpipe and
Zog-owned library paths. No FPS minimum, performance suite, soak,
high-core-count instance or hardware GPU test.

**Loader boundary:** these packages live in `project/graphics-drafts`, NOT in `project/package`. The canonical package loader and licensing admission suite cannot see them. Promotion requires complete source/notice evidence and a reviewed move into `project/package`, plus a canonical monthly pin; this revision makes no such move.

## Source-closure checkpoint (2026-11-01)

The core userspace libdrm 2.4.128 tarball is pinned to upstream release SHA-256 `3bb35db8700c2a0b569f2c6729a53f5495786856b310854c8de57782a22bddac`; the draft disables vendor KMS drivers, tests, udev integration and device access. This does **not** grant `/dev/dri`. Mako 1.4.3 and PyYAML 6.0.3 source sdists are pinned from PyPI and listed in the supplementary review ledger only. Their full build-only installation is still held pending MarkupSafe and PEP-517 backend provenance (Mako), PyYAML's pure-Python/Cython build policy, and exact import checks. All new packages remain outside `project/package/`.

Mesa draft now uses lowercase Meson booleans and disables fallback subproject acquisition. The GLX/driver install manifest and demonstrated LLVM 21.1.6 shared+RTTI ABI are required native evidence, not asserted source successes. `libdrm` runtime ELF dependencies must be observed from actual immutable Mesa output; it must not be included speculatively or omitted after observation.

## Exact archive inspection — source-only evidence

GitHub Actions [41310820294](https://github.com/zog144/image-build/actions/runs/41310820294) verified all six raw source archives against their frozen release SHA-256 values, then hashed selected archive-internal notices or primary source rights headers without compiling or installing software. The SPDX expressions remain subject to component-by-component review. The verified member paths and digests now appear in each graphics draft's `license.py` or supplementary `python-build-inputs.py` record. **Exact bytes hashed does not mean all file rights or distribution grants are approved.**

The supported first-Workspace profile still requires source-level Meson option and GLX dependency closure, exact built filename/ELF verification and a native installed smoke before canonical admission. No `/dev/dri`, large-core performance benchmark or hardware driver is needed.

**Exact upstream option correction:** Mesa 25.3.0 removed the `dri3` Meson option. Do not pass the earlier guessed `-Ddri3=disabled`. Restrict hardware exposure via software-only `swrast` selection, the approved immutable software view, no device grants, and GLX loader/runtime isolation; no DRI3 hardware acceptance is implied.

### Verified exact-source build profile

The [source archive/option inspection](https://github.com/zog144/image-build/actions/runs/41311239593) passed for the six pinned archives. It checked that the Mesa, demo and libdrm Meson options used in the draft configure commands are actually defined by the corresponding hashed upstream archives. Its next expanded inspection records the original Mesa GLX/DRI and demo Meson dependency references so the remaining X11 and XCB package edges can be reviewed without guessing. LLVM's real CMake/configured ABI must still confirm shared `libLLVM`, X86 backend and RTTI. Source checks are not native configure or installed runtime acceptance.

### GLX source dependency selection

The exact Mesa 25.3.0 `meson.build` inspection ([source evidence 41311622938](https://github.com/zog144/image-build/actions/runs/41311622938)) shows that with X11 + `glx=dri` the producer requires X11, Xext, X11-XCB, XCB-GLX and XCB-SHM. Its DRM DRI branch also requires XCB-DRI3/XCB-Present, XCB-Sync, XSHMFENCE, and direct GLX may require Xxf86vm. XCB extension pkg-config modules come from `libxcb`, X11-XCB comes from `libX11`; `libxshmfence` 1.3.3 and `libXxf86vm` 1.1.7 are now independently pinned **draft** packages, not accepted inherited binaries. Xrandr and libXpresent Xlib are conditional branches not automatically added. The run-time Xvnc GLX/DRI capability must still be checked; no device access is inferred from software DRI support.

## Canonical package admission handoff

The typed `project/graphics-drafts/admission-plan.json` records the six exact intended native stages, already-authored X11 predecessors, blocked Python build-input stages, mandatory rights/source/ELF checks and the limited `glxgears` criterion. This plan is a **hold**, not an executable build request. Its source tests refuse silently treating the drafts as packages in `project/package/`. Source-only build and archive inspection being green does **not** authorize package publication or imply a usable llvmpipe renderer.

## Canonical metadata boundary (2026-11-01)

All six native graphics drafts now pass the actual image-build package metadata and licensing parsers in source CI. The three original output manifests had an unsupported `publication` field, now removed. Rights records now use the precise canonical `schema=1` shape, retaining original archive SHA-256 member evidence while declaring `status='unresolved'`, `scope`, and unresolved scoped components. This is **metadata compatibility only**, not compiler, runtime or redistribution acceptance.

The supplementary November pin remains review-only and **no files were promoted to `project/package`**. Mako/MarkupSafe and PyYAML packaging backends, complete selected-component rights, real source-built LLVM/Mesa shared ABI, installed output/ELF inventory, immutable artifact/view and Xvnc `glxgears` smoke remain outstanding. Never use green source CI as native admission.

### Native GLX interface handoff

The Mesa draft now declares the required inherited `x11-xcb`, XCB GLX/SHM/DRI3/Present/Sync/XFixes/RandR, xshmfence, Xxf86vm and libdrm pkg-config modules. Its `configure` step explicitly requires them; the pre-existing libX11 output manifest already names `libX11-xcb.so`. The libxshmfence draft additionally requires its installed `xshmfence.pc`. The mesa-demos configure step requires both `gl` and `glx` pkg-config modules, then installs only Zog-built `glxgears` and `glxinfo`. These exact interfaces must be proved in the real compiler software view; merely declaring the modules in source metadata is not installed verification.

Public source CI [41313406115](https://github.com/zog144/image-build/actions/runs/41313406115) passed 242 local/source tests (one skipped) and 1,794-file public preflight with zero findings; independent pinned archive/option inspection [41313401603](https://github.com/zog144/image-build/actions/runs/41313401603) passed. Neither workflow is native-compilation or redistribution acceptance.

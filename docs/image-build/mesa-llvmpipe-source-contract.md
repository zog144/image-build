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
Archive-internal rights notices have not been extracted and SHA256 attested.
`license.py` entries explicitly hold notice coverage and redistribution.

The finite intended build contract is: LLVM X86 shared/RTTI, bounded two-job
CMake/Ninja; Mesa Gallium `swrast` with LLVM enabled and `glx=dri`, X11
platform, GLVND/DRI3/EGL/GBM/Vulkan/Wayland/GPU drivers disabled; demos
only `glxgears` and `glxinfo`. These typed source recipes are not
assertions that exact upstream 25.3.0 Meson options and build targets
were successfully executed. The GPU-free swrast DRI module does **not**
authorize any kernel DRM device.

**Native/source-admission blockers:** independently source-pin and build
`libdrm` (library != /dev/dri authority), Python Mako/PyYAML and any exact
additional Meson/CMake/pkgconf build edges; verify LLVM 21.1.6/Mesa 25.3.0
API/ABI compatibility, original source notices, Meson options from the actual
archive, target install paths, all runtime ELF/driver/GLX loader closure,
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

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

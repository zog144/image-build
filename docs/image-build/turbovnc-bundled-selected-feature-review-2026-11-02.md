# TurboVNC Xvnc 3.3.1 — selected bundled-source and feature-scope review

November 2, 2026 · PR #9 · exact original archive SHA-256 `9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da`.

This review checks the original top-level, unix, Xvnc and Xserver CMake member
hashes, the original TurboVNC, Xserver, libsha1 and bundled zlib-ng notices, and
additional Xvnc library, VNC server and GLX CMake source guards. Exact source
paths are checked *inside the pinned original tarball*, not a GitHub source
checkout or a synthesized post-install layout.

**Selected server-only profile:** `TVNC_BUILDVIEWER=OFF`,
`TVNC_BUILDSERVER=ON`, `TVNC_BUILDWEBSERVER=OFF`,
`TVNC_NVCONTROL=OFF`, `TVNC_BUILDSYSTEMD=OFF`,
`TVNC_DRI3=OFF`, `TVNC_USEPAM=OFF`, `TVNC_ZLIBNG=OFF`,
`TVNC_USETLS=OpenSSL`, `TVNC_DLOPENSSL=OFF`, and
`TVNC_STATIC_XORG_PATHS=ON`. The previous value `TVNC_USETLS=1`
was **not** an upstream-supported TLS selection: corrected to the actual
`OpenSSL` option. `TVNC_USEPAM` defaults ON upstream and is
explicitly disabled to avoid an unselected PAM dependency.

The checked Xserver CMake still builds `glx-server`, whose source includes
`glxdriswrast.c` and links `OpenGL::GL`; **GLX software rendering is
not equivalent to disabling all DRI-related code.** The DRI3 extension path,
libdrm/GBM device access and physical `/dev/dri` are not granted by source
staging. `TVNC_DRI3=OFF` removes the optional Xserver `dri3` target and
VNC `dri3.c` path, subject to native linked-object proof. The bundled zlib-ng
ExternalProject is guarded by `TVNC_ZLIBNG`; the draft instead requires the
separately pinned Zog zlib inherited source stage. Bundled libsha1 remains
**selected** and its COPYING notice must actually be delivered.

The original notice hashes and conditional CMake guards do not prove installed
binary ELF closure, compile flags, generated files or complete redistribution
rights. Require trusted native configured options, actual source/compile/link
commands, SHA-256 notice delivery, XKB `xkbcomp` origin and software GLX loader
resolution before any native acceptance. Rights and publication stay NO-GO.

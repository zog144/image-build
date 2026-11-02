# Remaining Mesa software-rendering component rights — original source questions

November 2, 2026 · PR #8 · source-only, separately from eight-sidecar native evidence verifier.

The read-only original-archive matrix now requires **exact existing** LLVM 21.1.6,
Mesa 25.3.0, libdrm 2.4.128, and mesa-demos 9.0.0 upstream SHA-256
pins, checks selected original member hashes and counts relevant selected/excluded
source trees. Those source-file presences are *not* evidence that a native build
selected or excluded any specific object. No parallel native evidence verifier is
created and no existing signed sidecar contract is weakened.

| Component | Original archive evidence to examine | Remaining independent question |
| --- | --- | --- |
| LLVM | `LICENSE.TXT`, `include/llvm/Support/LICENSE.TXT`, `lib/Support/BLAKE3/LICENSE`; BLAKE3 and TableGen source trees | Does libLLVM.so include BLAKE3 objects? Which generated tables or copied templates carry different notices? Require exact object-to-source mapping and installed BLAKE3 notice equality. |
| Mesa | `docs/license.rst`, GLAPI generator `license.py`, `lp_screen.c`, GLX Meson source; llvmpipe, Vulkan and imgui subtrees | Show generated GLAPI and llvmpipe code/inputs in real compile commands, absence of excluded Vulkan/imgui in linked closure, and software `swrast_dri.so` GLX runtime provenance. |
| libdrm | `xf86drm.c`, `xf86drm.h`, `xf86drmMode.c`; selected/excluded device-driver trees | Distinguish common library from KMS symbols and actual device access; prove disabled vendor, udev and tests are not compiled or linked, even though their sources remain in the archive. |
| mesa-demos | `src/xdemos/glxgears.c`, `glxinfo.c` and xdemos tree | Audit original per-file copyright/public-domain statements individually and link only the two selected programs, with independently delivered notices. |

The original source tree may include an excluded component; **its presence is not
feature expansion**. Conversely a Meson option spelling alone cannot prove it is
excluded from an ELF object. The eventual trusted native witness must bind
compile commands, generated source paths, intermediate archives, ELF dependencies,
license delivery and installed manifests to the actual selected generation.

**Hold:** rights review unsigned; no native installed bytes, no canonical promotion
or automatic submission. Consult the existing rights ledger and eight-sidecar verifier
rather than substituting a GitHub Actions archive inspection for either.

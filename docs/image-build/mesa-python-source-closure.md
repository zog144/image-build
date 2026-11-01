# Mesa first Workspace: source-only Python build closure and rights hold

Source candidate PR #8. No canonical package promotion or native compiler run authorized.

The repository already pins source recipes for `python-markupsafe` (3.1.0.dev0,
exact commit 4e111271b1494995708a9e878a10829b5e10c7ba),
`python-setuptools` 84.0.0, `python-wheel` 0.48.0,
`python-installer` 1.0.1, `python-packaging` 26.3,
`python-flit-core` 3.12.0, Python 3.15, CMake 4.4.4, Ninja,
Meson and pkgconf 3.0.5. Do not borrow OS/Runners' installed modules or
silently select a second MarkupSafe.

Noncanonical source-pinned stages were authored for Mako 1.4.3 and PyYAML 6.0.3.
Mako's upstream backend requires setuptools >=77 and its runtime imports MarkupSafe >=2.
PyYAML's original 6.0.3 backend declares Cython, even for use where only pure Python
is wanted. The draft pure-Python-only `prepare` step matches original
`pyproject.toml` metadata, records a pre/post modification hash and removes the
Cython requirement while retaining the original `_pyyaml_pep517` backend.
It explicitly disables the libyaml extension and requires a platform-neutral
wheel. This is a source transformation to review, **not an unmodified upstream build**.

`tools/verify_mesa_toolchain.py` is fail-closed against Host PATH,
Python module/search paths, `LD_LIBRARY_PATH`, pkgconf provider directories
and include/library flags. It verifies installed executable bytes and import origins
against a protected receipt. Crucially, it **does not issue or authenticate** that
receipt. The root-control/host-install native authority must bind the exact
software-root generation, signer and original source provenance before it can
constitute accepted evidence. Python `-I` checks are only as trustworthy as
that protected authority and its root mount identity.

All six graphics packages and both new build-only stages stay in
`project/graphics-drafts`. `rights-admission-evidence.json` records the
selected-feature notice inventory and unanswered attribution/installed-output
questions. Verified archive/member hashes are evidence of original bytes,
not permission to redistribute or a claim that disabled source cannot enter
native objects. Actual compiled-source manifests, immutable `DESTDIR` outputs,
ELF closure, wheel RECORD, and independent reviewer authorization are still
required. **Native and canonical admission: NO-GO.** Frozen October Boot A
inputs and the eventual low-cost glxgears-only Workspace smoke are unchanged.

## Review of six actual output contracts

The original archives and their selected notice-member SHA-256 values are verified.
The linked six draft output manifests identify **expected**, not observed, paths:
`llvm-config` and shared `libLLVM`; Mesa `libGL` and `swrast_dri`;
`glxgears`/`glxinfo`; `libdrm` with `xf86drm.h`/`libdrm.pc`;
`libxshmfence` plus its header/`.pc`; and `libXxf86vm` plus its `.pc`.
The precise paths are now cross-checked against
`rights-admission-evidence.json` by source CI.

**Review finding:** These expected files do not constitute an installed-byte
inventory, and their existing draft manifest does **not** demonstrate that all
required original component license and copyright notices have been delivered.
For LLVM specifically inspect bundled BLAKE3 obligations; for Mesa prove which
GLAPI, generated files and disabled Vulkan/imgui sources are actually linked;
for Mesa demos distinguish its copyrighted and public-domain source headers.
The independent reviewer must reconcile compile_commands, source/object hashes,
DESTDIR manifest and notice outputs. No status is upgraded to reviewed from
source-level checking, and no graphics artifact may be distributed yet.

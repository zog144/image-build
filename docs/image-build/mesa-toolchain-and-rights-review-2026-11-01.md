# First Workspace Mesa: isolated build tools and rights review (2026-11-01)

Review target: image-build PR #8, starting head `c2f04ec5b4c49390b3c6e962fa9a20aadb7f4cf2`.
This is an evidence review, **not an approval to build, redistribute, or promote**. The six graphics packages remain in `project/graphics-drafts/`, outside canonical package discovery.

## Task 3 — Python and native tool isolation

Existing verified source inputs: Mako 1.4.3 (`cd6537fe88d5fec315c55c2f8529bc4ce7a9a352ad7db3eeaa6a66e2dd4ec37a`) and PyYAML 6.0.3 (`d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f`). Their license-member hashes and original archive hashes have passed archive inspection, but they have **no admitted final build/install stages**. Never infer their isolated availability from Python imports on the GitHub runner.

Required source-closure sequence, before any native admission:

1. Independently pin exact original MarkupSafe source bytes, version, original license and selected notice-member hashes. Account for its optional compiled speedups or explicitly choose a verified pure-Python profile; Mako imports must resolve only to the selected immutable installation.
2. Independently pin and inspect `setuptools`, `wheel`, `packaging` where required, `flit_core`/`hatchling` or other backends **only as declared by the exact upstream pyproject.toml**, together with backend transitive requirements. Do not invent a fixed universal PEP 517 dependency list; derive the DAG from each selected sdist.
3. Pin `build`/PEP 517 frontend and its own dependency closure if used. Prefer offline wheelhouse creation with exact hashes; require `--no-index --no-deps` only after the complete dependency DAG has been explicitly checked. Disable build isolation only when the replacement environment is proved complete and isolated.
4. Choose an explicit PyYAML 6.0.3 backend (pure-Python recommended for this small build-only dependency, if confirmed compatible with its original build metadata); disallow opportunistic Cython extension generation. Do not assume that an environment variable alone replaces inspection of build metadata.
5. Validate accepted Zog-built Python 3.12 + ssl/sqlite interpreter and isolated `sys.path`; reject `PYTHONPATH`, user site packages, `~/.local`, distribution `site-packages`, and runner-provided modules. Run import-origin checks for `mako`, `markupsafe`, `yaml` and every selected backend; compare actual wheel `RECORD`/installed paths with the immutable staging manifest.
6. Pin and prove source origin/version for CMake, Ninja, Meson and pkgconf (or explicitly approved pkg-config implementation), plus compiler and Python invoked through those tools. A bare `command -v meson`, `command -v ninja`, `command -v llvm-config` or `pkg-config --exists` only proves that an executable/interface is present. It **does not** establish ownership.
7. Before configure, build an allowlisted `PATH`, `PKG_CONFIG_LIBDIR`, `PKG_CONFIG_SYSROOT_DIR`, `CMAKE_PREFIX_PATH`, interpreter path and Meson native/cross files exclusively from accepted Zog artifacts. Disable pkgconf default host search paths and Meson wrap/subproject downloads; inspect `meson-info`, compiler and linker commands for absolute references outside allowed roots. Require fail-closed tests with injected Host-only `.pc`, libraries and Python modules.
8. After real compilation, scan ELF `DT_NEEDED`, `SONAME`, `RPATH`, `RUNPATH`, loader resolution and exact `DESTDIR` installed files. Zero Host library resolution is an acceptance assertion, not a currently proven fact.

The currently authored Mesa draft references `mako-final` and `pyyaml-final` before those stages exist. Source checks and the existing `-Dallow-fallback-for=` option are necessary but **not sufficient** to resolve this closure. Task 3 therefore remains **BLOCKED**, rather than complete.

## Task 4 — Selected-feature component rights review

The verified archive/member hashes below come from the existing PR #8 archive-inspection workflow. Hash verification is evidence of identity, not a grant of distribution rights. Review only the selected first-Workspace software GLX feature graph; do not automatically include disabled GPU/Vulkan, Wayland, hardware DRM or tests in the distributed package.

| Draft / selected scope | Present original rights evidence | Outstanding attribution decision |
| --- | --- | --- |
| LLVM 21.1.6: shared X86 LLVM with RTTI | `LICENSE.TXT`, `include/llvm/Support/LICENSE.TXT`, `lib/Support/BLAKE3/LICENSE`, `test/YAMLParser/LICENSE.txt`, `utils/lit/LICENSE.TXT`; top-level expression `Apache-2.0 WITH LLVM-exception` | Determine precisely which bundled BLAKE3, generated tables, support modules and other third-party components enter selected library/tools. Preserve their separate notices and LLVM exception text where required; test-only components need an explicit excluded/output decision. |
| Mesa 25.3.0: swrast/llvmpipe, X11/GLX | `docs/license.rst`, `src/imgui/LICENSE.txt`, GLAPI generator `license.py`, Vulkan radix_sort and screenshot-layer licenses; top-level expression `MIT` | Enumerate actual Meson-selected and generated compilation units; resolve independent copyright/header terms and shader/compiler-generated code. Verify whether imgui and Vulkan subtrees are *excluded* rather than copying their notices into a claimed swrast-only grant. |
| libdrm 2.4.128: userspace libdrm without hardware drivers | Original `xf86drm.c` and `xf86drm.h` notices, expression `MIT` | Account for every selected common implementation/header and generated output. Verify disabled vendor KMS, udev and privileged-test sources do not enter artifacts. |
| libxshmfence 1.3.3 | Original `COPYING`, expression `MIT` | Map compiled source/header attribution and installed license/notice delivery for the selected library. |
| libXxf86vm 1.1.7 | Original `COPYING`, expression `MIT` | Map selected compiled source, installed library and `xxf86vm.pc`; distinguish the external xorgproto header's separately inherited notice. |
| mesa-demos 9.0.0: only glxgears/glxinfo | Original source-header hashes `src/xdemos/glxgears.c` and `src/xdemos/glxinfo.c`; expression `MIT AND LicenseRef-Public-Domain` | Review the two original header texts and other linked source independently; verify explicit public-domain attribution versus permissive copyrighted sections, and exclude broader demo assets from deliverables. |

Review criteria for each component: archive identity; selected source-file inventory based on the actual native build; exact copyright holder/license text; bundled/generated code provenance; upstream modifications; dependency and dynamically linked component attribution; source/binary redistribution obligations; notice delivery in the final immutable artifact. Preserve every distinct applicable license; do not flatten heterogeneous components to the package's top-level expression. Verify distribution rights *before* publication and distinguish internal source compilation from public distribution.

**Decision: NO-GO for canonical package admission or distribution.** The existing six canonical-shaped `license.py` records correctly set `status='unresolved'`; do not change to reviewed until an independent reviewer signs off on complete feature-scoped source/output attribution. October Boot A source inputs and compiler-host submission authority remain untouched.

Future native acceptance remains a single inexpensive Xvnc/noVNC `glxgears` smoke with optional `glxinfo -B`, not an FPS benchmark.

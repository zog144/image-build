# Separate source re-review: Mesa Python isolation and scoped rights

**Date:** 2026-11-01  
**PR:** [zog144/image-build #8](https://github.com/zog144/image-build/pull/8)  
**Source review baseline:** `4c0b485404a4453bed9bd8fc2f291e951a7e2a36`  
**Decision:** source hardening prepared; native isolation and redistribution **NO-GO**.

This is a separate read-through and adversarial test expansion after the original
implementation work, but it was performed by the same connected implementation
channel. It **does not** claim an independent human reviewer has signed off.

## Finding I-1: Python preflight versus actual build behavior

The verifier's `python -I` probe was not enough when the subsequent Mako/PyYAML
build and installer commands used plain `python3`: working-directory imports
could differ from verified imports. All Mako/PyYAML Python build/prepare and
installation invocations have been changed to isolated `python3 -I`.
New adversarial regressions reject Host module origins, hostile `sys.path`,
missing isolated-mode flags, and wrong interpreter identity.

The existing canonical `python-markupsafe` source pin, setuptools/wheel,
installer/packaging/flit-core producers and CMake/Ninja/Meson/pkgconf source
definitions remain the selected upstream sources; no duplicate binary or
Host-installed dependency is authorized. Mako's upstream backend/runtime
requirements and PyYAML's original conditional Cython requirement are checked
against SHA-256 verified original source archives. The PyYAML pure-Python-only
build transformation remains a separately recorded, unresolved downstream patch.

**Native blocker:** isolated-mode startup can still load authorized-site
`.pth` or `sitecustomize` code before a Python-level verifier runs.
A genuine protected installation must attest the selected interpreter's
startup paths, site hooks, libraries, and distribution RECORD/inventory;
source tests cannot prove such installed-state provenance.

## Finding I-2: pkgconf, tool selection, and Host fallback

The earlier source verifier inspected a `.pc` directory and only simple
`-I`/`-L` tokens. It now inspects `--static` private requirements,
checks attached and split include/library flags, rejects opaque linker/plugin
options, and denies untrusted Python/pip, compiler include/library, CMake,
Meson cache, and pkgconf environment overrides.

Adversarial tests exercise altered tool hashes, Host executable and module
allowlists, wrong PATH aliases, hostile pkgconf providers, split arguments,
rpath/plugin response-file attempts, and private dependency flags.

**Native blockers:** the controller must authenticate the installed
source-pinned verifier *before executing it*, protect its complete path and
receipt, establish the rootfs/mount identity, and attest the exact selected
tool/library bytes. An authority string in a JSON receipt is not, by itself,
authentication. ELF loader resolution, generated build commands and
complete cross-stage compiler closure must be checked on a real installed Host.

## Finding R-1: selected feature/source candidates

Original source candidate digests are recorded in
`project/graphics-drafts/rights-admission-evidence.json`; the archive
inspector now fails on disagreement with original pinned archive bytes.
GitHub Actions source archive verification
[41330909677](https://github.com/zog144/image-build/actions/runs/41330909677)
verified these SHA-256 values.

| Draft | Verified original source-candidate evidence | Native source-selection and rights questions |
| --- | --- | --- |
| LLVM 21.1.6 | Support notice and BLAKE3 license | Which bundled BLAKE3 units/generated code enter shared X86 libLLVM; exact third-party license delivery |
| Mesa 25.3.0 | llvmpipe `lp_screen.c`, GLX Meson file, GLAPI-generator notice | Full GLX/llvmpipe input list, generated code attribution, disabled Vulkan/imgui and unrelated driver exclusion |
| libdrm 2.4.128 | `xf86drm.c`, `xf86drm.h`, `xf86drmMode.c` | Copyright/license coverage for every compiled common object; disabled vendor/KMS/udev paths |
| libxshmfence 1.3.3 | `COPYING`, `src/Makefile.am` | Selected implementation/header and corresponding notice text |
| libXxf86vm 1.1.7 | `COPYING`, `src/XF86VMode.c` | Selected implementation, generated metadata, inherited xorgproto header rights |
| mesa-demos 9.0.0 | `glxgears.c` and `glxinfo.c` | Per-source copyrighted/public-domain terms and exactly linked supporting objects |

The six source-only draft install contracts now contain explicit original
rights-member delivery steps, and the corresponding expected manifest paths
are source-tested. These original-source/header copies are **partial evidence**;
they are not an assertion that all applicable rights are covered.

## Remaining authorization boundary

Do not upgrade `license.py` records to reviewed, promote
`project/graphics-drafts` into `project/package`, publish immutable
`applications-v1` graphics objects, or alter frozen October Boot A sources
on this evidence alone. The independent reviewer must reconcile the actual
native compilation source/object map, every generated and bundled component,
exact DESTDIR files, delivered notices, dependent dynamic libraries and
per-component redistribution terms. Both authentic native isolation and
independent rights approval are presently outstanding. The only eventual
runtime smoke is low-cost Xvnc/noVNC `glxgears`, without a performance gate.

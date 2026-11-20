# First Fonts executable Project-current producer — source handoff (2026-11-20)

## Exact failure and source correction

The failed native Fonts request reported:

```text
ImageBuildError: acl: catalogue-only; author and review stage recipes,
source SHA-256 digests and output manifests before building
```

PR #26 at `d78dfb74b8ce51f6160877edeb01343bd00759be`
already resolved the selected Project's active input generation and snapshots
Project-current definitions. It did **not** distinguish a broad,
non-executable catalogue under `project/package` from the reviewed
`project/package/<name>/stages/final` source definitions. Loading the
entire catalogue with `load_packages` reaches `acl` first and correctly
rejects its `catalogue-only` parent metadata. The original command,
operation ID, input receipt and outcome are retained unchanged.

This successor adds `src/zog/image_build/first_fonts.py` and connects the
**normal implicit** `pipeline.submit` path only when the selected Project's
actual package directory is `<Project>/source/project/package` and its
fixed reviewed targets are exactly:

```text
libpng-final → freetype-final → fontconfig-final
```

The producer materializes only the three **real final-stage recipe
directories** into `<same Project state>/image-build/remote-operations/
<new-operation-id>/fonts-stage-packages` through the existing
`recipe_snapshots.materialize` and `pins.snapshot`. Their build,
configure, test, install, dependency, integration, source URL/hash,
installed-manifest and upstream-license evidence metadata are read by the
same strict `metadata.load_package` validator as any normal package.
`ImageBuild.prepare_pipeline` then copies this *closed* package set and
its independently reviewed `commit-pin.py` into the normal immutable
pipeline recipe inventory, exactly as PR #26 does for conventional
already-flattened Project package definitions.

**The `catalogue-only` gate is not weakened.** Other catalogue entries
(including `acl`) are not promoted or silently ignored for ordinary
requests; requests outside this exact fixed Fonts graph still follow PR
#26's existing generic policy, including catalogue-only failure. The
original `package.py` files are catalogue parent metadata, not directly
runnable recipes. The executable `-final` stages have their own
complete stage files and no fictitious `kind=toolchain` input requirement.

## Exact reviewed source versions, release URLs and SHA-256

| Stage | Primary source | SHA-256 |
|---|---|---|
| libpng-final | https://downloads.sourceforge.net/libpng/libpng-1.6.58.tar.xz | `28eb403f51f0f7405249132cecfe82ea5c0ef97f1b32c5a65828814ae0d34775` |
| freetype-final | https://downloads.sourceforge.net/freetype/freetype-2.14.3.tar.xz | `36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f` |
| fontconfig-final | https://gitlab.freedesktop.org/api/v4/projects/890/packages/generic/fontconfig/2.18.3/fontconfig-2.18.3.tar.xz | `4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3` |

All three sources are already marked `downloaded-exact-release-sha256`
in the original reviewed `upstream.py` source records. Their
`stages/final/sources.py` files have the same exact source URL, digest,
archive declaration and extract destination `upstream`. No wheel,
source archive or accepted compiler receipt bytes are changed here.

A **separate new source-review lock**
`project/bootstrap/graphics-fonts-executable-pin.py` binds only the
three precise final-stage source objects and has review date
`2026-11-01`. It is source-commit-controlled package input metadata,
**not** a new signed gateway approval, not a replacement for the
original retained October compiler/monthly provenance, and never
changes a previously published receipt. On stage preparation,
`pins.snapshot` converts this reviewed source lock into an ordinary
per-operation `commit-pin.py`; the standard
`pins.validate` rejects a changed or absent source URL/hash.
The original private October historical pin is not copied into this
public repository.

## Actual stage steps and dependency graph

The existing source-reviewed `build.py` files remain the executable
recipes (they were authored earlier, not newly invented by this task):

1. **libpng 1.6.58.** Extract the exact release. Autoconf
   `./configure --prefix=/usr --libdir=/usr/lib --disable-static`,
   `make -j8`, `make check`, install with `DESTDIR`, preserve
   upstream `LICENSE`. Required installed outputs:
   `usr/lib/libpng16.so`, `usr/include/png.h`,
   `usr/share/licenses/libpng/LICENSE`.
2. **FreeType 2.14.3.** Depends on `libpng-final` for build and
   runtime. Configure shared library with zlib/bzip2/libpng enabled,
   HarfBuzz and Brotli disabled as in the original source profile,
   `make -j8`, compile/run the original FreeType version smoke test,
   install with `DESTDIR`. Required outputs:
   `usr/lib/libfreetype.so`,
   `usr/include/freetype2/ft2build.h`,
   and preserved `LICENSE.TXT`, `docs/FTL.TXT`,
   `docs/GPLv2.TXT` at exact `usr/share/licenses/freetype/` paths.
3. **Fontconfig 2.18.3.** Depends on `freetype-final` for build and
   runtime (libpng transitively). Configure with
   `--prefix=/usr --libdir=/usr/lib --sysconfdir=/etc
   --localstatedir=/var --disable-docs --enable-libxml2=no`,
   `make -j8`, `make check`, `DESTDIR` install and preserve
   upstream `COPYING`. Required outputs:
   `usr/lib/libfontconfig.so`, `usr/bin/fc-match`,
   `etc/fonts/fonts.conf`,
   `usr/share/licenses/fontconfig/COPYING`.

The strengthened `produce-manifest.py` files require the actual
installed upstream notice files. They retain `trees: ['usr','etc','var']`
and exact binary/header/config requirements; the existing
`licensing.prepare_readability`, `prepare_finalization` and
`preserve_licenses` pipeline still validates evidence from the
SHA-256 source and writes its separate immutable Zog package license
receipt. The original `license.py` declarations remain `declared`
and include unresolved bundled-component notices. **Source-only
compilation readiness is not public binary redistribution clearance.**

## Safety and provenance

- No new gateway-supplied selection fields, approval document, default
  source revision, host state copy, Project or compiler toolchain.
- The existing selected Project's active image-kind compiler generation
  remains the only input. No change to its manifest, historical
  accepted compiler receipt or generation output inventory.
- No implicit recovery/retry of the old Fonts request; the new reviewed
  source and new source lock are usable only for a separately assigned
  fresh native request.
- All stage definitions are copied and hashed in the same Project's
  normal immutable pipeline snapshot. The pipeline's
  `source_pins`, `recipes`, `selection`, and original owner
  operation identity bind stage outputs and later resume.
- Missing `build.py`, empty build/install phases, missing sources,
  missing/changed SHA-256, changed reviewed pin, incomplete output
  manifest, missing/altered notice evidence, and wrong dependency
  closure fail **before pipeline preparation completes**. No
  catalogue-only exception or metadata validation bypass is added.

## Tested and untested boundaries

The focused producer test makes a disposable **Project-current**
catalogue with a deliberately non-runnable `acl` entry, a synthetic
immutable `kind=image` selected generation and the actual three
source stage directories. It calls `RemoteOperations._prepare_pipeline`
using PR26's normal implicit arguments only, never
`pipeline.resume` or any runner. It then reads the real selected
package snapshot and checks exact execution phases, ordered
dependencies, license records, source hashes, required outputs,
normal pin snapshot, input generation and recovery idempotency.
Negative tests prove missing recipes, hashes and notices still
fail. Generic PR26 image submission regressions remain included.

**No native compiler job or source download was run by this source
implementation.** A passing prepare-only test does not prove the
chosen compiler root contains all headers and linker capabilities.

## Genuine native inputs to confirm

The accepted `kind=image` compiler generation provides GCC/G++,
assembler/linker, Make, CMake and Python per the retained evidence.
It has **not** yet been demonstrated here that this exact selected
root provides the full **zlib headers/library**, **bzip2 development
headers/library**, **Expat**, **pkgconf/pkg-config**, complete build
utilities, and a usable `/bin/bash` environment for all three
configure/test steps. The original stage integration metadata
assumes those capabilities. Host-deploy Work / image-build Work
should read back the real root and report any missing packages as
*the actual* next prerequisites, without manufacturing a replacement
compiler generation merely for the prior `kind=toolchain` label.
A source-only CI run cannot certify ABI, runtime linker/library
search paths, or that the archive downloads and tests succeed in
the real sandbox; those remain native execution evidence.

## Work handoff

1. Review and select the exact source successor and original PR26
   implicit selection behavior, without changing `certbot-seed`
   or its current input generation.
2. Install the reviewed producer **in the existing selected Project**
   via the normal protected host-deploy path, retaining its own Git
   source revision and installed byte evidence. Verify the new
   reviewed Fonts source-pin file, all stage source files, license
   files and manifests are present in that Project's checkout.
3. Run supported no-build readiness on the installed source and
   selected Project state. It must show the exact closed
   `libpng-final`, `freetype-final`, `fontconfig-final`
   package definitions, current active `kind=image` input,
   source pin and executable-phase/order metadata. Check real
   compiler capabilities before authorizing compilation.
4. Preserve the previous failed request and original receipt
   unchanged. Only after separate authorization use **a fresh**
   request/operation identity through the approved host-deploy
   consumer and normal root-control/box-control path.
5. Verify actual archive hashes/notice bytes, real configure/build/
   test/install execution, final required binary/config/notice
   outputs, Build Record and a **new separate immutable image
   generation**. Do not overwrite the input compiler generation.

No request was submitted, retried, or executed by Regular.

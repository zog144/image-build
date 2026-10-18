# Font and XCB source preparation

Two ordered native batches are prepared, not live-accepted:

| Plan | Source releases |
|---|---|
| `project/bootstrap/graphics-fonts.py` | libpng 1.6.58, FreeType 2.14.3, Fontconfig 2.18.3 |
| `project/bootstrap/graphics-xcb.py` | Check 0.15.2, libevdev 1.14.0, Python libevdev 0.13.1 (test support), xorgproto 2026.1, libXau 1.0.12, libXdmcp 1.1.5, xcb-proto 1.17.0, libxcb 1.17.0 |

All archives were downloaded from their recorded upstream release endpoints.
Monthly pins and version-bound license declarations bind SHA-256 of the exact
archive and notice files. Declarations are not public-distribution clearance;
unresolved per-file/component review remains explicit. No upstream code or
archives are vendored. FreeType's FTL option requires attribution when selected;
its alternative GPL and bundled component notices remain preserved.

## Build choices and prerequisites

Use the accepted refreshed self-hosted base and exact retained package outputs.
Require GCC, make, Python, pkgconf, Meson/Ninja, zlib, bzip2, Expat and gperf.
Check these bindings before execution; never substitute libraries from the Work
container. The XCB batch follows the accepted fonts generation.

FreeType deliberately has no HarfBuzz or Brotli support in this foundation pass.
Those features require a later reviewed dependency/rebuild pass. System zlib,
bzip2 and PNG are required, not autodetected away. No APNG patch is applied to
libpng. Fontconfig uses Expat, shared libraries and its Autotools build. Its full
configured `make check` runs; this does not cover the separate Meson/Python suite,
external font downloads, bubblewrap sandbox tests, JSON-C-dependent tests when
JSON-C is absent, or static-only tests. No failed test is waived. Test logs and
upstream skips must be retained and reported. A later extended Fontconfig test
pass needs pinned pytest/TAP dependencies, fonts and a suitable sandbox contract.
DESTDIR installation avoids executing fc-cache against the host. This batch
installs font infrastructure, not a font collection or desktop.

FreeType has no standard make-check suite: an original library initialization,
version and teardown smoke test is used, explicitly not comprehensive coverage.
xcb-proto receives XML parsing/import checks in addition to its make-check target.
libxcb requires Check explicitly so its unit tests cannot silently disappear;
its check_all PASS result and XDM authentication feature are required.

The Xorg protocol test prerequisite is now represented explicitly in the graph:
libevdev 1.14.0 and Python libevdev 0.13.1 precede xorgproto. The xorgproto
`evdev-keysym-check` still performs its explicit import guard before Meson, so an
unavailable binding cannot become an exit-77 false success.

Native libevdev's upstream Meson tests are built. Upstream marks its device-facing
library/kernel tests with the `needs-uinput` suite; those tests create kernel input
devices through `/dev/uinput`. The package recipe runs the complementary upstream
test set and grants no extra device/root privilege. Full `needs-uinput` execution is
a separate host-level prerequisite, not a skipped success. Fedora Rawhide 1.14.0
disables the upstream tests entirely; Zog deliberately retains the non-device subset.

Python libevdev's upstream pytest suite was also reviewed. It contains root-only
`/dev/input` and uinput cases. The Zog package performs the device-independent import
and event-code checks that xorgproto consumes. The upstream wheel definition packages
the pure `libevdev` directory without generated payload; for this test-support role,
Zog installs that reviewed directory directly rather than adding hatchling solely as
an execution dependency. Full device pytest coverage remains external evidence.

## Comparable generation acceptance

Use the modern v2 installed-verification producer for both fresh generations.
Use exactly `project/bootstrap/graphics-common-check.sh` for both installed checks;
never append XCB-specific commands to the second copy. Package-specific tests
remain separate. The shared test exercises PNG memory encoding/decoding,
FreeType initialization and version consistency, Fontconfig pattern parsing and
Python ssl/SQLite. It does not claim rendering, font matching or an X server.

Freeze the same explicit execution-environment contract and digest, controller
policy and command definition for both runs. Record different subject inventory
and generation IDs separately. Do not import old v1 execution rows into these
new checks. Preserve all previous generations and observations unchanged. Export
both snapshots and require integrate-observe to confirm a unique cross-generation
match with equal definition/environment digests and no mixed-contract ambiguity.
PASS/PASS establishes comparability, not evidence of a detected regression.

Native tool promotion produces kind `toolchain`. After acceptance, use the
application-image publisher to produce a NEW kind `image` generation from exact
accepted outputs, preserving provenance and application_software_compatibility.
Verify kind, descriptor, canonical export and consumer binding before handing out
an application generation ID. Do not offer a toolchain ID for application launch.

## Execution hold

Recipe preparation does not resolve host ownership. No compilation, installation,
service change or generation publication on the compiler host is authorized by
this source pass. Resume only after the coordinated host-deploy ownership
transition and an explicitly supported build submission route. The initial
read-only gateway acceptance does not itself authorize build.submit.


## Distribution packaging review

The maintained RPM review for this graphics work is tracked in
`docs/image-build/graphics-rpm-review.md`. Distribution package names are evidence only; Zog
maps them to upstream source projects and explicit capabilities. The review records
Fedora Rawhide at immutable branch revisions. The openSUSE Factory source API returned
HTTP 401 from the reproducible research job on 2026-10-10, so each affected row records
that access limitation and the fallback maintained evidence used instead of pretending
that an unavailable Factory spec was inspected.

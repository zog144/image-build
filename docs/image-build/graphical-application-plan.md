# Post-install graphical application build plan

Status: staged source planning. greetd/agreety now additionally freeze the complete
upstream Cargo.lock crates.io source closure, but remain `catalogue-only` until
per-crate license/notice review, PAM/rootfs ABI selection and native build acceptance
are complete. The other entries remain source-pinned plans. None are eligible for
automatic installation or runtime launch.

The objective is to publish optional graphical software through the existing
`applications-v1` artifact/view contracts after console-first installation. None
of the entries in this plan is added to the Basic/rootfs dependency closure merely
to make host-welcome graphical.

## Reviewed source pins

| application | version | SHA-256 | publication intent |
| --- | --- | --- | --- |
| greetd | 0.10.3 | `ee5cb70e0add4ca9c9fe57e47581ab0002d44c07743fb5492469f3b570db640b` | separate login/session daemon artifact |
| agreety | 0.10.3 | same greetd source | separate text-greeter artifact |
| X.Org Server | 21.1.25 | `6ad4e3c7b59a309b32c92e5c15ce1267110f9e13f1ac78da62361a628da1a0eb` | separate X11 server artifact |
| i3 | 4.25.1 | `4a742bbe81b9e5ee6057f42a8e3c691d88894e93f1a5d81fe239128512ac05c0` | minimal desktop/window-manager artifact |
| Firefox ESR | 153.5.0esr | `28714a7d4f9b38c7aafbe38022de7775a3d9cb3c1ebf19a567c26eb761e3410b` | kiosk browser artifact |
| TurboVNC | 3.3.1 | `9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da` | follow-on remote X11 artifact |
| VirtualGL | 3.1.5 | `8a3249c4fa8eea928362ca97b8fe16e5b356e3a18cd16d87e3efa72a870750b6` | follow-on remote graphics artifact |

Each exact URL/hash pair is recorded in the corresponding
`project/package/<name>/sources.py`. A catalogue entry cannot be loaded by
`load_package()`; this is deliberate until complete recipes, notices and output
manifests are reviewed.

Chromium and a Wayland compositor/graphical greeter are **not source-pinned in this
checkpoint**. Chromium requires an explicit source/DEPS/toolchain/download policy,
and the Wayland stack requires a separately reviewed dependency choice. Neither
should be represented by a misleading single archive pin before that review.

## Stage 1 — greetd and agreety

Build greetd and agreety from the same pinned 0.10.3 source but publish them as
separate immutable artifacts/views.

Before authoring the final recipes:

1. **DONE for source identity:** freeze the full Cargo dependency closure from upstream `Cargo.lock`; the exact crates.io URL/checksum set is retained in both `greetd/cargo-sources.py` and `agreety/cargo-sources.py`. Per-crate license/notice review remains a blocker before binary publication;
2. verify the selected Rust toolchain is a reviewed image-build input;
3. determine the exact PAM ABI/configuration expected by the target rootfs;
4. review upstream/distro PAM-related fixes instead of silently copying a distro
   patch;
5. inventory every installed file and retain GPLv3 plus dependency notices;
6. bind rootfs dynamic libraries and NSS/PAM/logind expectations through the
   compatibility descriptor.

**Privilege boundary:** compiling/publishing greetd does not authorize running it as
a login/session manager. The controller-owned privileged greetd role remains
NO-GO until box-control/root-control review a fixed executable, configuration,
PAM/session, VT/seat and logind allowlist. agreety publication does not imply that
role exists.

Initial acceptance:
- source-only recipe tests;
- reproducible build/install inventory;
- immutable artifact/view publication;
- non-privileged CLI/help smoke where applicable.

No PAM login or local seat is exercised at this stage.

## Stage 2 — X.Org Server

The source pin is X.Org Server 21.1.25. The existing catalogue already contains an
early subset of X11 libraries/protocol inputs, including libX11/libxcb, Xorg
protocol data, xtrans, several X extensions, font libraries and xcb-util projects.

Before a buildable Xorg recipe exists, close the missing runtime/build graph,
including at minimum the selected policy for:

- pixman;
- libdrm and graphics device access;
- Mesa/glamor and libepoxy if glamor is enabled;
- xkeyboard-config/xkbcomp and keyboard input;
- libinput/udev or the explicitly selected input path;
- font and DDX/module loading policy;
- systemd/logind/seat interaction and required device permissions.

The artifact must not smuggle host driver/module directories through mutable raw
paths. Exact module/driver paths and libraries belong in the immutable artifact or
an explicitly controller-owned device/runtime capability.

Acceptance order:
1. source-only build and installed-file manifest;
2. immutable artifact/view and rootfs compatibility;
3. virtual X11/Xvfb-style acceptance without a physical seat;
4. selected Xorg server against disposable virtual devices;
5. only later, authorized physical-seat/DRM/input/logind acceptance.

A successful virtual display is not physical-seat readiness.

## Stage 3 — i3

The source pin is i3 4.25.1 under its BSD-3-Clause primary license.

A final recipe needs the selected versions/notices for its actual dependency graph,
including the required XCB helper libraries plus cairo/pango, PCRE2,
startup-notification, libxkbcommon, yajl, GLib/intl and libev where selected by the
build. Dependencies not already reviewed by image-build become separate catalogue
work, not host-package fallbacks.

Initial native acceptance runs i3 inside the disposable virtual X11 stage and
proves its runtime ELF closure before any real local-seat test.

## Stage 4 — Firefox ESR kiosk runtime

Firefox ESR 153.5.0esr is source-pinned only. Its source archive is intentionally
not treated as a simple small-package recipe.

Before authoring the final application recipe:

- freeze Firefox's complete source/build-tool closure, including Rust/cargo,
  Python/build tools and any Node/clang/lld/cbindgen requirements selected by the
  build;
- choose explicitly between bundled and reviewed system libraries rather than
  inheriting host libraries accidentally;
- review NSS/NSPR, ICU, graphics/font/media, GTK/X11, audio and D-Bus runtime
  requirements;
- complete MPL-2.0 and bundled third-party notice/provenance review;
- define a deterministic kiosk launcher and writable-profile/cache/download policy.

Browser profile/cache state is writable application data and must remain outside
the immutable software artifact.

Acceptance:
1. source-only and build-tool reproducibility;
2. immutable artifact/view publication;
3. offline launch in disposable virtual X11;
4. deterministic kiosk launcher/startup page;
5. networking/media tests in an isolated acceptance environment;
6. only after the local-seat stack is approved, physical-seat kiosk acceptance.

Host-welcome must not embed another browser engine merely for its welcome screen.

## Follow-on — TurboVNC and VirtualGL

TurboVNC 3.3.1 and VirtualGL 3.1.5 are source-pinned for the follow-on comparison.
Their source/component licenses still need complete file/component review before
binary publication.

Remote TurboVNC workspace acceptance remains a separate concept from a physical
local seat. It must not be used as evidence that greetd/PAM/logind/local DRM works.

## Chromium and Wayland

Chromium remains a comparison target, but this checkpoint deliberately does not
create a fake one-file source pin. Its DEPS/CIPD/third-party source acquisition,
codec/notice and toolchain policy must be frozen first.

A Wayland compositor and graphical greeter likewise remain optional follow-on
applications. The project must first choose the compositor/greeter and freeze the
Wayland/libinput/libdrm/Mesa/session dependency strategy.

## Publication and rollback contract

Every accepted graphical application must use the existing application software
store:

1. begin durable install operation;
2. build/install only reviewed source inputs into the staging root;
3. finalize immutable `applications-v1` artifact;
4. publish a deterministic view;
5. verify `application-software-consumer-v1` against the selected rootfs;
6. retain artifact/view identities while selected or while cleanup/recovery is
   pending.

Rollback is selection of the prior retained immutable view, not mutation of the
published artifact.

## Native host-deploy evidence required

For each promoted recipe return:

- exact source/patch/dependency hashes;
- compiler/build commands and environment identity;
- installed-file manifest and artifact SHA-256;
- view SHA-256 and consumer binding digest;
- ELF interpreter/NEEDED/RPATH/RUNPATH for native executables/modules;
- license/notice paths and source availability;
- selected rootfs compatibility descriptor;
- virtual-display acceptance evidence;
- controller attach result;
- for physical-seat work only: separate approved PAM/logind/VT/DRM/input evidence.

Until those records exist, the catalogue entries mean **source-pinned plan**, not
installed, runnable or GUI-ready software.

# Graphics recipe preparation status

This file is the durable source-preparation ledger for the October 2026 graphics
foundation work.  It deliberately separates recipe/source readiness from compiler-host
execution.

Status vocabulary:

- **researched**: upstream/build-system and distribution packaging metadata inspected.
- **recipe-authored**: Zog source/dependency/build/test/install/manifest metadata exists.
- **CI-validated**: repository metadata/graph tests pass.
- **compiled**: a compiler host produced retained package output.
- **live-accepted**: installed/runtime evidence was accepted on the target host.

No row may advance to **compiled** or **live-accepted** from this regular chat.

## Completed source-preparation checkpoint

| Batch | State | Notes |
|---|---|---|
| fonts | recipe-authored / CI-validated | libpng 1.6.58, FreeType 2.14.3, Fontconfig 2.18.3 |
| XCB core | recipe-authored / CI-validated | Check 0.15.2, xorgproto 2026.1, libXau 1.0.12, libXdmcp 1.1.5, xcb-proto 1.17.0, libxcb 1.17.0 |
| xorgproto libevdev prerequisite | recipe-authored / CI-validated | libevdev 1.14.0 and Python libevdev 0.13.1; privileged uinput/device suites remain explicit external evidence |
| consumer-driven X11 core | recipe-authored / CI-validated | xtrans, libX11, libXext, libXfixes, libXi, libXtst, libXv, libxkbfile, libfontenc, libXfont2; libX11 includes four exact upstream 2026 security fixes; dedicated `graphics-recipes` run `38088814898` passed at `002343c169985e4b3909a3e21b242838f92796ab` |
| XCB/i3 support phase 1 | recipe-authored / CI pending | xcb-util 0.4.1, xcb-util-image 0.4.1, xcb-util-keysyms 0.4.1, xcb-util-wm 0.4.2, xcb-util-xrm 1.3; source preparation only |
| XCB cursor closure | researched / evidence correction pending | xcb-util-renderutil 0.3.10 and xcb-util-cursor 0.1.6; current research workflow omitted renderutil from the immutable Fedora probe, so neither row is advanced to recipe-authored yet |
| X11 session support | recipe-authored / CI pending | libICE 1.1.2, libSM 1.2.6, libXt 1.3.1; required by startup-notification; libSM binds libuuid from the retained util-linux native-environment output; source preparation only |
| comparable generation check | authored only | common installed check remains unchanged; no compiler-host run is claimed |

The XCB/libevdev checkpoint was closed at
`4380187c07a615c695456e10bb67f240c0bd3d9b`, with the validation correction at
`b12d1a8e11ba31c36edf3d6c3d8983377c2e61f7`.

## Next recipe batches

### A. Xorg client/runtime foundation

The first consumer-driven core is authored. It intentionally treats xorgproto/XCB,
FreeType, zlib and bzip2 as inherited accepted-generation capabilities rather than
rebuilding them. libX11 1.8.13 is not used bare: four official post-release upstream
security commits are source-pinned, zero-fuzz applied and typed with before/after
file hashes.

The remaining Xorg library candidates below are deferred until xterm/i3 or another
selected consumer requires them. Research and author only the subset needed by xterm,
i3, TurboVNC and VirtualGL.
The current candidate set, derived from the Xorg/BLFS graph and the upstream
consumers, is:

- xtrans 1.6.0
- libX11 1.8.13
- libXext 1.3.7
- libICE 1.1.2
- libSM 1.2.6
- libXt 1.3.1
- libXmu 1.3.1
- libXpm 3.5.19
- libXaw 1.0.16
- libXfixes 6.0.2
- libXcomposite 0.4.7
- libXrender 0.9.12
- libXcursor 1.2.3
- libXdamage 1.1.7
- libfontenc 1.1.9
- libXfont2 2.0.9
- libXft 2.3.9
- libXi 1.8.3
- libXinerama 1.1.6
- libXrandr 1.5.5
- libXtst 1.2.5
- libXv 1.0.13
- libxkbfile 1.2.0

Do not automatically import the entire BLFS Xorg library bundle.  Add
libXpresent, libXRes, libXvMC, libXxf86*, libpciaccess or libxshmfence only when
a selected consumer or selected feature requires them.

### B. XCB/i3 support

Candidate source projects:

- xcb-util 0.4.1
- xcb-util-image 0.4.1
- xcb-util-keysyms 0.4.1
- xcb-util-renderutil 0.3.10
- xcb-util-wm 0.4.2
- xcb-util-cursor 0.1.6
- xcb-util-xrm 1.3
- libev 4.33
- yajl 2.1.0
- startup-notification 0.12
- libxkbcommon 1.13.2 (stable; do not select the 1.14 beta)
- xkeyboard-config 2.48
- PCRE2 10.47 (already present in the source catalogue; required directly by i3)
- Cairo/Pango text stack and their required source dependencies
- one pinned basic font needed for xterm/i3 runtime acceptance

i3 4.25.1 is not considered recipe-ready until its Pango/Cairo, GLib/GObject,
xkbcommon/xkbcommon-x11, XCB XKB/RandR/Shape/Xinerama, PCRE2, libev, YAJL and
startup-notification closure is explicit. xcb-util-cursor is a direct consumer edge;
xcb-util-image and xcb-util-renderutil are therefore required through the cursor
library rather than being arbitrary bundle imports. Do not hide those dependencies
behind host distribution packages.

### C. xterm and i3

- xterm: pin the current reviewed release, luit/runtime font requirement and exact
  Xorg library features used by configure.
- i3: pin a stable release and explicitly map its XCB utilities, Pango, libev, yajl,
  startup-notification and xkbcommon dependencies.
- Keep launcher/status/lock extras out of the first Basic image unless required by
  station-access.

### D. TurboVNC

Initial Zog profile is server-focused.  Review and pin the exact upstream release
before authoring.  The profile should deliberately decide:

- viewer: off unless required by a Zog consumer;
- bundled noVNC web server: off when station-access owns browser presentation;
- PAM authentication: off unless the workspace architecture explicitly chooses it;
- NV-CONTROL: off for the generic Basic image;
- DRI3: off for the first software-rendered acceptance unless separately justified;
- TLS: retain upstream OpenSSL server support unless station-access architecture makes
  it redundant;
- zlib-ng: explicitly decide bundled-vs-system rather than accepting an implicit
  network/download path.

Required source capabilities still include X11, Xau, Xdmcp, xkbfile, xfont2,
Pixman, OpenGL/GLX headers, libjpeg-turbo/TurboJPEG and XKB data.

### E. VirtualGL

Pin the exact stable release and build server/client components needed by the Zog
workspace architecture.  Explicitly review X11/XCB, OpenGL/GLX/EGL, TurboJPEG and
X Video support.  Disable optional OpenCL or other acceleration surfaces unless they
are deliberately selected and their dependency/driver contract is represented.

## Distribution/RPM review policy

Before a new project enters a Zog batch:

1. inspect its exact upstream build metadata;
2. inspect the Fedora Rawhide spec at an immutable revision;
3. inspect the openSUSE Factory spec when accessible;
4. when the Factory source API is unavailable, record that exact limitation and use
   a maintained public OBS/openSUSE spec only as secondary evidence;
5. record distribution-only patches/features without automatically copying them;
6. pin source archive, digest, notice hashes and any accepted patches;
7. record optional/test-only dependencies and device/root/network prerequisites.

The first matrix is `docs/graphics-rpm-review.md`.  Extend it batch-by-batch.

## Execution hold

All rows above remain source preparation until a supported host-deploy/image-build
submission route is explicitly authorized for the compiler host.  GitHub Actions may
validate metadata and download exact public sources for evidence; it is not evidence
that the Zog rootfs package was compiled or installed.

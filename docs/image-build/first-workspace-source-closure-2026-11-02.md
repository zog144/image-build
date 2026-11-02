# First Workspace graphical source closure — exact downstream constraints

This record deliberately prevents a partial XCB/X11/i3/Xvnc graph from being
marked source-complete. It does **not** authorize a Host build, grant a new
generation, or replace an accepted predecessor.

The exact source archive hashes and original COPYING members of
xcb-util-renderutil 0.3.10 and xcb-util-cursor 0.1.6 were checked in
[GitHub Actions 41456545723](https://github.com/zog144/image-build/actions/runs/41456545723).
Both now have canonical-format *catalogue-only* recipe metadata, with
source/header attribution and native acceptance still outstanding.

`project/graphics-first-workspace/closure.json` freezes the consumer-driven
dependency obligations of i3 4.25.1, xterm patch 412 and TurboVNC 3.3.1.
The i3 required pkg-config names were read from the tagged upstream
`meson.build`. A relevant XCB cursor chain must resolve image + renderutil
and their XCB/transitive dependencies; libICE/libSM/libXt must remain
native-unaccepted until compiler evidence. xterm patch 412 is source-pinned from the independently published archive SHA-256,
but its build-stage, inherited X11 dependencies, luit and fonts, original
notice inventory and native acceptance are not yet package-ready.

The TurboVNC source 3.3.1 server-only profile is drawn from upstream
`CMakeLists.txt`, `unix/CMakeLists.txt` and `BUILDING.md`. It disables
the Java viewer, built-in noVNC server, NV-CONTROL and service-file
installation, and requires static selected Xorg paths and a declared
TurboJPEG/OpenSSL software root. It also disables in-tree zlib-ng in favor
of source-built Zog zlib. These flags are **planned**, not a successful
CMake configure against Zog-provided bytes.

The intended Zog runtime is one Xvnc/i3/xterm Workspace at a fixed virtual
resolution and, later, one low-cost source-built Mesa llvmpipe `glxgears`
smoke without an FPS threshold. GLX remains a Workspace predecessor, not a
Basic-console rootfs feature.

## Native and source admission hold

Before a compiler is enabled, fill every currently missing project with
source-pinned, original notice-verified canonical recipe definitions and
independent rights evidence; show the exact selected i3 and TurboVNC source
and build graph; run metadata CI and then a genuine protected worker
compilation with source, ELF and linker closure. This plan is a **negative
readiness gate** until those conditions are actually true.

Do not auto-expand Xorg libraries, use host-installed Cairo/Pango/JPEG,
replace selected generation IDs, or infer native completion from this file.

## i3 non-graphical source input checkpoint — November 2

Additional source recipe records: libev 4.33, YAJL 2.1.0,
startup-notification 0.12, libxkbcommon 1.13.2 and
xkeyboard-config 2.48. Original source archives and license/COPYING
member SHA-256 were inspected in GitHub Actions #41498150323.
The exact independently published digest was known in advance for
libev and xkeyboard-config; YAJL's upstream GitHub tag reproduced the
previously published archive SHA. libxkbcommon's tag and the
startup-notification direct release archive are observed but still
require immutable upstream/provenance and legal review.

Each carries catalogue-only metadata and a source stage. The real
flat package loader checks the new five-stage ordering, including
xcb-util → startup-notification and xkeyboard-config → libxkbcommon.
No package was promoted to a monthly pin; dependency fallback to Host
must be denied by the later true isolated native worker. Review
libxkbcommon's upstream compatibility patch and the legacy YAJL CMake
output paths during that native review.

The still-missing GLib/GObject/Pango/Cairo/Pixman/Harfbuzz/Fribidi
and xterm/Xaw/font/TurboJPEG source closure is **not** solved by this
checkpoint. See `closure.json`.

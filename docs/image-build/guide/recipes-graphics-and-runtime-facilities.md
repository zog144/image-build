# Recipes, graphics and runtime facilities

## Recipe graph is not an installed desktop

The graphics build work deliberately separates researched upstream/distribution metadata, authored Zog recipes, successful repository CI, compiler-host execution and **live-accepted** installed runtime behavior. A passing dependency-resolution test is not evidence that Xvnc, X11 authorization, i3, VirtualGL or GPU devices work on the target host.

The [graphics recipe status ledger](../graphics-recipe-status.md) uses a stepped vocabulary: `researched`, `recipe-authored`, `CI-validated`, `compiled`, and `live-accepted`. Source preparation can add exact recipes, archives and pinned notices without making the stronger statements. Retained host results must be checked before advancing an entry, and the ledger's dated checkpoints are not a live-current status probe.

## Ordered foundations

The graphics foundation begins with libpng/FreeType/Fontconfig and XCB/Xorg protocol plus client/runtime libraries. Dependency planning then covers X11/XCB, keyboard and window manager prerequisites, followed by xterm, i3, TurboVNC and optional VirtualGL. These are not interchangeable runtime roles: libraries and protocol data enable a graphical stack, i3 is the minimal window manager, TurboVNC supplies the headless X/VNC server and VirtualGL is an additional rendering path requiring its own hardware/GLX/EGL decisions.

Build options must be deliberate—disabling an optional HarfBuzz/Brotli, OpenCL, XVideo or server feature is not proof of feature parity with Fedora/openSUSE. Distribution RPM specs and patches provide **review evidence**, not permission to copy their build decisions or auto-apply patches to Zog. Pin the primary source archive/digest and notice identities independently. See [graphics foundation](../graphics-foundation.md), [distribution/RPM review](../graphics-rpm-review.md) and [recipe progression](../graphics-recipe-status.md).

## Immutable software and private runtime scaffolds

The rootfs contains immutable executable, library and data material, but an executing desktop needs writable ephemeral facilities for socket directories and controller-owned credentials. The [runtime facility normalization contract](../runtime-facilities.md) separates canonical empty scaffold roots from transient child entries. It records those roots in the published generation manifest and leaves runtime-only entries for the owning controller.

When a package output contains a runtime-created directory, the producer may create a **new** normalized immutable generation whose manifest records the empty scaffold; it cannot edit an already-published generation in place. Box-control/root-control independently require an allowed empty real directory, reject symlinks and nonempty contents, and supply runtime-owned transient facilities. The policy is not a writable OverlayFS or unrestricted system directory grant.

## Workspace and application integration

Image-build must publish the foreground X server launcher and selected library closure, including directories the controller must bind, before station-access can use it. The controller owns DISPLAY, Xauthority, X11 socket and private VNC endpoint identities. Station-access's noVNC/websockify is a proxy into that approved runtime, not a replacement for server-side authentication or a source of arbitrary mount paths.

Normal application software (such as Django plus compiled React) belongs in separate immutable application artifacts and symlink-composed views; the base generation should not accumulate those application dependencies merely because the desktop needs them. Writable database and secrets STATE remain outside published software.

## Acceptance ladder

1. Validate exact source archives, pins, upstream notices, licensing exceptions and dependency/feature choices.
2. Check recipe schema, closure and static CI with recorded immutable source revision.
3. Build on an admitted host-deploy lane and retain exact output/command provenance.
4. Verify installed binaries/libraries in a read-only generation using runtime-appropriate probes.
5. Validate real TurboVNC/X11/VNC endpoint, controller-owned credentials, i3, client application attachment and shutdown/reboot recovery.
6. Treat VirtualGL/GPU/driver support as a separately accepted capability rather than inferring it from the server stack.

A source ledger is not a complete live acceptance report. Preserve explicit missing device, test and license evidence.

## Detailed references

- [Graphics source/release preparation](../graphics-foundation.md)
- [Graphics recipe maturity and remaining batches](../graphics-recipe-status.md)
- [Distribution packaging decisions and pending sources](../graphics-rpm-review.md)
- [Immutable runtime facilities](../runtime-facilities.md)
- [Application software and views](immutable-artifacts-and-generations.md)
- [Systemd native prerequisites](../systemd-native.md)

Avoid updating the old ledger's `compiled` or `live-accepted` fields on the basis of this prose alone.

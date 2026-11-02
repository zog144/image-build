# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"\ntest -n \"${PKG_CONFIG_LIBDIR:-}\"\npkgconf --exists libstartup-notification-1.0 xcb xcb-xkb xcb-xinerama xcb-randr xcb-shape xcb-util xcb-cursor xcb-keysyms xcb-icccm xcb-xrm xkbcommon xkbcommon-x11 yajl libpcre2-8 cairo pangocairo glib-2.0 gobject-2.0\nmeson setup build-i3 upstream/i3-4.25.1 --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Dauto_features=disabled -Ddocs=false -Dmans=false"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-i3 -j 4"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -f build-i3/config.h\ntest -f build-i3/meson-info/intro-dependencies.json\n# Actual selected pkgconf/header/link closure remains a native gate."
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"\nDESTDIR=\"$DESTDIR\" meson install -C build-i3\ninstall -Dm644 upstream/i3-4.25.1/LICENSE \"$DESTDIR/usr/share/licenses/i3/LICENSE\""
    ]
  ]
}

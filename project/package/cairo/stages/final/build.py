# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"\ntest -n \"${PKG_CONFIG_LIBDIR:-}\"\ntest -n \"${ZOG_GRAPHICAL_SOURCE_ROOT:-}\"\nmeson setup build-cairo upstream/cairo-1.18.4 --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Dxcb=enabled -Dxlib=enabled -Dfontconfig=enabled -Dfreetype=enabled -Dpng=enabled -Dzlib=enabled -Dglib=disabled -Dxlib-xcb=disabled -Dtee=disabled -Dlzo=disabled -Dsymbol-lookup=disabled -Dtests=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-cairo -j 4"
    ]
  ],
  "test": [],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"\nDESTDIR=\"$DESTDIR\" meson install -C build-cairo\ninstall -Dm644 upstream/cairo-1.18.4/COPYING \"$DESTDIR/usr/share/licenses/cairo/COPYING\""
    ]
  ]
}

# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"\ntest -n \"${PKG_CONFIG_LIBDIR:-}\"\ntest -n \"${ZOG_GRAPHICAL_SOURCE_ROOT:-}\"\nmeson setup build-pango upstream/pango-1.56.4 --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Dauto_features=disabled -Ddocumentation=false -Dman-pages=false -Dintrospection=disabled -Dbuild-testsuite=false -Dbuild-examples=false -Dlibthai=disabled -Dxft=disabled -Dfreetype=enabled -Dfontconfig=enabled -Dcairo=enabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-pango -j 4"
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
      "test -n \"${DESTDIR:-}\"\nDESTDIR=\"$DESTDIR\" meson install -C build-pango\ninstall -Dm644 upstream/pango-1.56.4/COPYING \"$DESTDIR/usr/share/licenses/pango/COPYING\""
    ]
  ]
}

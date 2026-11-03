# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "command -v meson; command -v ninja\npkg-config --exists x11 xext\nmeson setup build-xxf86vm upstream/libXxf86vm-1.1.7 --prefix=/usr --libdir=lib --buildtype=release -Dauto_features=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-xxf86vm -j 2"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -f build-xxf86vm/meson-info/intro-buildoptions.json"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; DESTDIR=\"$DESTDIR\" meson install -C build-xxf86vm\nfor f in \"$DESTDIR/usr/lib/libXxf86vm.so\" \"$DESTDIR/usr/lib/pkgconfig/xxf86vm.pc\"; do test -e \"$f\"; done\ninstall -Dm644 \"upstream/libXxf86vm-1.1.7/COPYING\" \"$DESTDIR/usr/share/licenses/libXxf86vm/COPYING\""
    ]
  ]
}

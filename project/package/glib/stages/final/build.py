# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"\ntest -n \"${PKG_CONFIG_LIBDIR:-}\"\ntest -n \"${ZOG_GRAPHICAL_SOURCE_ROOT:-}\"\nmeson setup build-glib upstream/glib-2.86.5 --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Dauto_features=disabled -Dtests=false -Dinstalled_tests=false -Ddocumentation=false -Dintrospection=disabled -Dman-pages=disabled -Dlibmount=disabled -Dselinux=disabled -Dsysprof=disabled -Dnls=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-glib -j 4"
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
      "test -n \"${DESTDIR:-}\"\nDESTDIR=\"$DESTDIR\" meson install -C build-glib\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/Apache-2.0.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/Apache-2.0.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/CC0-1.0.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/CC0-1.0.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/GPL-2.0-or-later.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/GPL-2.0-or-later.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/LGPL-2.1-only.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/LGPL-2.1-only.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/LGPL-2.1-or-later.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/LGPL-2.1-or-later.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/LLVM-exception.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/LLVM-exception.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/LicenseRef-old-glib-tests.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/LicenseRef-old-glib-tests.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/MIT.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/MIT.txt\"\ninstall -Dm644 upstream/glib-2.86.5/LICENSES/MPL-1.1.txt \"$DESTDIR/usr/share/licenses/glib/LICENSES/MPL-1.1.txt\""
    ]
  ]
}

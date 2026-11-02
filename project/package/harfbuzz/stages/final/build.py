# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/harfbuzz-11.5.0\nmeson setup build-zog --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Dauto_features=disabled -Ddefault_library=shared -Dglib=disabled -Dgobject=disabled -Dcairo=disabled -Dfreetype=disabled -Dicu=disabled -Dgraphite2=disabled -Ddocs=disabled -Dtests=disabled -Dutilities=disabled -Dintrospection=disabled -Dchafa=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/harfbuzz-11.5.0\nninja -C build-zog"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/harfbuzz-11.5.0\nninja -C build-zog test"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/harfbuzz-11.5.0\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" ninja -C build-zog install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/harfbuzz/COPYING\""
    ]
  ]
}

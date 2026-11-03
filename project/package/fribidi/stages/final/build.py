# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/fribidi-1.0.16\nmeson setup build-zog --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Dauto_features=disabled -Ddefault_library=shared -Dbin=false -Ddocs=false -Dtests=false"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/fribidi-1.0.16\nninja -C build-zog"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/fribidi-1.0.16\nninja -C build-zog test"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/fribidi-1.0.16\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" ninja -C build-zog install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/fribidi/COPYING\""
    ]
  ]
}

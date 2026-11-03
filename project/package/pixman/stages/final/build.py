# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/pixman-0.46.4\nmeson setup build-zog --prefix=/usr --libdir=lib --buildtype=release --wrap-mode=nodownload -Ddefault_library=shared"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/pixman-0.46.4\nninja -C build-zog"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/pixman-0.46.4\nninja -C build-zog test"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/pixman-0.46.4\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" ninja -C build-zog install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/pixman/COPYING\""
    ]
  ]
}

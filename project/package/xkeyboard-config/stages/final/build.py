# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xkeyboard-config-2.48\nmeson setup build-zog --prefix=/usr --libdir=lib --buildtype=release"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xkeyboard-config-2.48\nninja -C build-zog"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xkeyboard-config-2.48\nninja -C build-zog test"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xkeyboard-config-2.48\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" ninja -C build-zog install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/xkeyboard-config/COPYING\""
    ]
  ]
}

# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libxkbcommon-1.13.2\nmeson setup build-zog --prefix=/usr --libdir=lib --buildtype=release -Denable-x11=true -Denable-wayland=false -Denable-tools=false -Denable-docs=false -Denable-xkbregistry=false -Denable-bash-completion=false -Dxkb-config-root=/usr/share/X11/xkb"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libxkbcommon-1.13.2\nninja -C build-zog"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libxkbcommon-1.13.2\nninja -C build-zog test"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libxkbcommon-1.13.2\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" ninja -C build-zog install\ninstall -Dm644 LICENSE \"$DESTDIR/usr/share/licenses/libxkbcommon/LICENSE\""
    ]
  ]
}

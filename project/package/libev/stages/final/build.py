# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libev-4.33\n./configure --prefix=/usr --libdir=/usr/lib --disable-static"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libev-4.33\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libev-4.33\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libev-4.33\ntest -n \"$DESTDIR\"\nmake DESTDIR=\"$DESTDIR\" install\ninstall -Dm644 LICENSE \"$DESTDIR/usr/share/licenses/libev/LICENSE\""
    ]
  ]
}

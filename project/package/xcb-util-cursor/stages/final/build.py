# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-cursor-0.1.6\n./configure --prefix=/usr --libdir=/usr/lib --disable-static --disable-silent-rules"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-cursor-0.1.6\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-cursor-0.1.6\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-cursor-0.1.6\ntest -n \"$DESTDIR\"\nmake DESTDIR=\"$DESTDIR\" install\nfind \"$DESTDIR/usr/lib\" -name '*.la' -delete\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/xcb-util-cursor/COPYING\""
    ]
  ]
}

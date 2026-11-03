# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-renderutil-0.3.10\n./configure --prefix=/usr --libdir=/usr/lib --disable-static --disable-silent-rules"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-renderutil-0.3.10\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-renderutil-0.3.10\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xcb-util-renderutil-0.3.10\ntest -n \"$DESTDIR\"\nmake DESTDIR=\"$DESTDIR\" install\nfind \"$DESTDIR/usr/lib\" -name '*.la' -delete\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/xcb-util-renderutil/COPYING\""
    ]
  ]
}

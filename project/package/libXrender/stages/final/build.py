# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXrender-0.9.12\n./configure --prefix=/usr --libdir=/usr/lib --disable-static --disable-silent-rules"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXrender-0.9.12\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXrender-0.9.12\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXrender-0.9.12\ntest -n \"$DESTDIR\"\nmake DESTDIR=\"$DESTDIR\" install\nfind \"$DESTDIR/usr/lib\" -name '*.la' -delete\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/libXrender/COPYING\""
    ]
  ]
}

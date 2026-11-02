# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/mkfontscale-1.2.3\n./configure --prefix=/usr --libdir=/usr/lib --disable-silent-rules"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/mkfontscale-1.2.3\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/mkfontscale-1.2.3\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/mkfontscale-1.2.3\ntest -n \"${DESTDIR:-}\"\nmake DESTDIR=\"$DESTDIR\" install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/mkfontscale/COPYING\""
    ]
  ]
}

# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/luit-1.1.1\n./configure --prefix=/usr --libdir=/usr/lib --disable-silent-rules"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/luit-1.1.1\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/luit-1.1.1\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/luit-1.1.1\ntest -n \"${DESTDIR:-}\"\nmake DESTDIR=\"$DESTDIR\" install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/luit/COPYING\""
    ]
  ]
}

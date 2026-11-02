# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXft-2.3.9\n./configure --prefix=/usr --libdir=/usr/lib --disable-silent-rules --disable-static"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXft-2.3.9\nmake -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXft-2.3.9\nmake check"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libXft-2.3.9\ntest -n \"${DESTDIR:-}\"\nmake DESTDIR=\"$DESTDIR\" install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/libXft/COPYING\""
    ]
  ]
}

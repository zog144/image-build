# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libxshmfence-1.3.3\n./configure --prefix=/usr --libdir=/usr/lib --disable-static"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "make -C upstream/libxshmfence-1.3.3 -j2"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -f upstream/libxshmfence-1.3.3/Makefile\n# Native ELF/symbol and memory fence smoke requires admitted compiler."
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; make -C upstream/libxshmfence-1.3.3 DESTDIR=\"$DESTDIR\" install\nfor f in \"$DESTDIR/usr/lib/libxshmfence.so\" \"$DESTDIR/usr/include/X11/xshmfence.h\" \"$DESTDIR/usr/lib/pkgconfig/xshmfence.pc\"; do test -e \"$f\"; done"
    ]
  ]
}

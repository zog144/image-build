# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xterm-412\n./configure --prefix=/usr --libdir=/usr/lib --with-app-defaults=/usr/share/X11/app-defaults --disable-setuid --disable-setgid --enable-256-color"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xterm-412\nmake -j8"
    ]
  ],
  "test": [],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/xterm-412\ntest -n \"$DESTDIR\"\nmake DESTDIR=\"$DESTDIR\" install\nmake DESTDIR=\"$DESTDIR\" install-ti\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/xterm/COPYING\""
    ]
  ]
}

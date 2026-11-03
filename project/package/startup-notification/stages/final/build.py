# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/startup-notification-0.12\n./configure --prefix=/usr --libdir=/usr/lib --disable-static"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/startup-notification-0.12\nmake -j8"
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
      "cd upstream/startup-notification-0.12\ntest -n \"$DESTDIR\"\nmake DESTDIR=\"$DESTDIR\" install\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/startup-notification/COPYING\""
    ]
  ]
}

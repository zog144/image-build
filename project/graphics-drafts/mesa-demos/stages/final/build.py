# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "command -v meson; command -v ninja\npkg-config --exists gl glx x11 xext\nmeson setup build-demos upstream/mesa-demos-9.0.0 --prefix=/usr --libdir=lib --buildtype=release -Dx11=enabled -Degl=disabled -Dgles1=disabled -Dgles2=disabled -Dvulkan=disabled -Dglut=disabled -Dauto_features=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-demos glxgears glxinfo"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "for tool in glxgears glxinfo; do test \"$(find build-demos -type f -name \"$tool\" | wc -l)\" -eq 1; done\n# No Xvnc here, no FPS test."
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"\nfor tool in glxgears glxinfo; do\n  found=$(find build-demos -type f -name \"$tool\" -print)\n  test \"$(printf '%s\\n' \"$found\" | sed '/^$/d' | wc -l)\" -eq 1\n  install -Dm755 \"$found\" \"$DESTDIR/usr/bin/$tool\"\ndone\ninstall -Dm644 \"upstream/mesa-demos-9.0.0/src/xdemos/glxgears.c\" \"$DESTDIR/usr/share/licenses/mesa-demos/glxgears.c\"\ninstall -Dm644 \"upstream/mesa-demos-9.0.0/src/xdemos/glxinfo.c\" \"$DESTDIR/usr/share/licenses/mesa-demos/glxinfo.c\""
    ]
  ]
}

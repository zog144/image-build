# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libjpeg-turbo-3.2.0\ncmake -S . -B build-zog -G Ninja -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Release -DENABLE_SHARED=ON -DENABLE_STATIC=OFF -DWITH_TURBOJPEG=ON -DWITH_JNA=OFF -DWITH_TOOLS=OFF -DWITH_TESTS=OFF -DWITH_SIMD=OFF"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/libjpeg-turbo-3.2.0\ncmake --build build-zog --parallel 8"
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
      "cd upstream/libjpeg-turbo-3.2.0\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" cmake --install build-zog --prefix /usr\ninstall -Dm644 LICENSE.md \"$DESTDIR/usr/share/licenses/libjpeg-turbo/LICENSE.md\""
    ]
  ]
}

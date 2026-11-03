# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/yajl-2.1.0\ncmake -S . -B build-zog -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DCMAKE_SKIP_RPATH=ON"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/yajl-2.1.0\ncmake --build build-zog --parallel 8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/yajl-2.1.0\ncd build-zog && ctest --output-on-failure"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/yajl-2.1.0\ntest -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" cmake --install build-zog --prefix /usr\ninstall -Dm644 COPYING \"$DESTDIR/usr/share/licenses/yajl/COPYING\""
    ]
  ]
}

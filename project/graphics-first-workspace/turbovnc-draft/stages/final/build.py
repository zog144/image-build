# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"$ZOG_GRAPHICAL_TOOLCHAIN_ATTESTATION\"\ncmake -S upstream/turbovnc-3.3.1 -B build-xvnc -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib -DTVNC_BUILDVIEWER=OFF -DTVNC_BUILDSERVER=ON -DTVNC_BUILDWEBSERVER=OFF -DTVNC_NVCONTROL=OFF -DTVNC_BUILDSYSTEMD=OFF -DTVNC_STATIC_XORG_PATHS=ON -DTVNC_USETLS=1 -DTVNC_DLOPENSSL=OFF -DTVNC_ZLIBNG=OFF -DTJPEG_INCLUDE_DIR=/usr/include -DTJPEG_LIBRARY=/usr/lib/libturbojpeg.so -DXKB_BASE_DIRECTORY=/usr/share/X11/xkb -DXKB_BIN_DIRECTORY=/usr/bin -DXORG_DRI_DRIVER_PATH=/usr/lib/dri -DXORG_FONT_PATH=/usr/share/fonts -DXORG_REGISTRY_PATH=/usr/share/X11/xserver"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cmake --build build-xvnc --parallel 4"
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
      "test -n \"$DESTDIR\"\nDESTDIR=\"$DESTDIR\" cmake --install build-xvnc --prefix /usr\ninstall -Dm644 upstream/turbovnc-3.3.1/LICENSE.txt \"$DESTDIR/usr/share/licenses/turbovnc/LICENSE.txt\"\ninstall -Dm644 upstream/turbovnc-3.3.1/unix/Xvnc/programs/Xserver/COPYING \"$DESTDIR/usr/share/licenses/turbovnc/Xserver-COPYING\"\ninstall -Dm644 upstream/turbovnc-3.3.1/unix/Xvnc/lib/libsha1/COPYING \"$DESTDIR/usr/share/licenses/turbovnc/libsha1-COPYING\""
    ]
  ]
}

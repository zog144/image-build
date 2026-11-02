# Data only; parsed with ast.literal_eval.
{
  "project": "turbovnc",
  "stage_id": "final",
  "version": "3.3.1",
  "native_admission": "HOLD: exact compile/link provenance and GLX loader, bundled Xorg source maps; DRI3 and zlib-ng excluded; protected current authority and rights",
  "base_contract": "Protected immutable Zog software-only root; no automatic host Xorg include/lib search, user namespace, /dev/dri or distro libjpeg fallback.",
  "selected_feature_flags": [
    "-DTVNC_BUILDVIEWER=OFF",
    "-DTVNC_BUILDSERVER=ON",
    "-DTVNC_BUILDWEBSERVER=OFF",
    "-DTVNC_NVCONTROL=OFF",
    "-DTVNC_BUILDSYSTEMD=OFF",
    "-DTVNC_STATIC_XORG_PATHS=ON",
    "-DTVNC_USETLS=1",
    "-DTVNC_DLOPENSSL=OFF",
    "-DTVNC_ZLIBNG=OFF",
    "-DTJPEG_INCLUDE_DIR=/usr/include",
    "-DTJPEG_LIBRARY=/usr/lib/libturbojpeg.so",
    "-DXKB_BASE_DIRECTORY=/usr/share/X11/xkb",
    "-DXKB_BIN_DIRECTORY=/usr/bin",
    "-DXORG_DRI_DRIVER_PATH=/usr/lib/dri",
    "-DXORG_FONT_PATH=/usr/share/fonts",
    "-DXORG_REGISTRY_PATH=/usr/share/X11/xserver",
    "-DTVNC_DRI3=OFF"
  ],
  "source_original_run": "41500603254",
  "test_scope": "Build options authored from tagged CMake. No compiled Xvnc executable, running server or notice delivery accepted.",
  "required_pkg_config": [
    "xfont2",
    "pixman-1",
    "x11",
    "xau",
    "xdmcp",
    "xkbfile",
    "gl",
    "zlib"
  ],
  "selected_bundled_originals": {
    "Xserver/COPYING": "4cc0447a22635c7b2f1a93fec4aa94f1970fadeb72a063de006b51cf4963a06f",
    "libsha1/COPYING": "4c387926596bfeacc5b72ebeb96ab36c299a07568e18592c727a6c11dd512c20",
    "zlib-ng/LICENSE.md": "6c9f0d975b41afaa34d22f55bb8986ce69e5cb7ad327cb2b28820cd425edf5ee"
  },
  "selected_cmake_sources_sha256": {
    "unix/Xvnc/programs/Xserver/CMakeLists.txt": "upstream selected archive currently requires source member SHA independently; native emission is hold",
    "unix/Xvnc/CMakeLists.txt": "54444d6b340213218d358bec0d10d4633b9683431567f39e3e089200e515d4a3"
  },
  "missing_native_predecessor": "xkbcomp source package and authenticated installed executable; GLX opengl headers and software Mesa accepted generation"
}

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
    "-DTVNC_USETLS=OpenSSL",
    "-DTVNC_DLOPENSSL=OFF",
    "-DTVNC_ZLIBNG=OFF",
    "-DTJPEG_INCLUDE_DIR=/usr/include",
    "-DTJPEG_LIBRARY=/usr/lib/libturbojpeg.so",
    "-DXKB_BASE_DIRECTORY=/usr/share/X11/xkb",
    "-DXKB_BIN_DIRECTORY=/usr/bin",
    "-DXORG_DRI_DRIVER_PATH=/usr/lib/dri",
    "-DXORG_FONT_PATH=/usr/share/fonts",
    "-DXORG_REGISTRY_PATH=/usr/share/X11/xserver",
    "-DTVNC_DRI3=OFF",
    "-DTVNC_USEPAM=OFF"
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
    "unix/Xvnc/programs/Xserver/CMakeLists.txt": "4e52b66d996039bb1450690cc694691670c8f5c4cad387d8f057eeaa28feede4",
    "unix/Xvnc/CMakeLists.txt": "54444d6b340213218d358bec0d10d4633b9683431567f39e3e089200e515d4a3"
  },
  "missing_native_predecessor": "Source-pinned xkbcomp now authored, but requires authenticated native installed executable; Mesa GLX software loader and signed generation remain separate HOLD",
  "source_exclusion_observations": {
    "DRI3": "option ON upstream; excluded by explicit OFF, requires native link/ELF confirmation",
    "PAM": "option ON upstream; disable server PAM integration with explicit OFF",
    "bundled_zlib_ng": "ExternalProject_Add guarded by TVNC_ZLIBNG; disable and require protected Zog zlib",
    "NVCONTROL": "non-essential XNVCtrl disabled; source-only flag",
    "device_access": "GLX swrast DRI driver directory is not authority to access /dev/dri; selected linked objects and open syscalls unobserved",
    "TLS": "OpenSSL selected explicitly; no implicit '1' fallback"
  }
}

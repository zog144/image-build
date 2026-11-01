# Data only; parsed with ast.literal_eval.
{
  "project": "mesa",
  "stage_id": "final",
  "base_contract": "Source-built accepted Zog toolchain and exact immutable graphical predecessor software view; zero unpinned host libraries.",
  "native_admission": "HOLD until original archive/dependency closure, build-config tests and rights review.",
  "unresolved": [
    "libdrm is not source-admitted",
    "Python Mako and PyYAML source/ABI closure",
    "Exact Mesa 25.3.0 Meson options, GLX loader and output paths untested",
    "Original archive notice/component hashes pending"
  ],
  "device_policy": "No /dev/dri, kernel graphics devices, GPU/Vulkan drivers or Wayland requirement.",
  "runtime_smoke": "ELF/GLX dependency closure; no native acceptance claimed.",
  "inherited_glx_pkgconfig": [
    "x11",
    "xext",
    "x11-xcb",
    "xcb",
    "xcb-randr",
    "xcb-glx",
    "xcb-shm",
    "xcb-dri3",
    "xcb-present",
    "xcb-sync",
    "xcb-xfixes",
    "xshmfence",
    "xxf86vm",
    "libdrm",
    "expat",
    "zlib"
  ],
  "immutable_elf_check": "Native-only: verify DT_NEEDED/SONAME/RPATH/RUNPATH, swrast LLVM shared linkage and zero Host graphic library leakage; do not infer runtime libdrm requirement from build-only pkg-config."
}

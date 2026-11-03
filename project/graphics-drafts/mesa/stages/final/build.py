# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"\ntest -n \"${ZOG_GRAPHICS_TOOLCHAIN_VERIFIER:-}\"; python3 \"$ZOG_GRAPHICS_TOOLCHAIN_VERIFIER\" --attestation \"$ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION\" --phase mesa\ncommand -v meson; command -v ninja; command -v llvm-config\ntest -x /usr/bin/llvm-tblgen\n# Native toolchain attester must bind this executable to the selected llvm-final generation.\nllvm-config --version | grep -Fx 21.1.6\nllvm-config --targets-built | tr ' ' '\\n' | grep -Fx X86\ntest \"$(llvm-config --has-rtti)\" = YES\ntest \"$(llvm-config --shared-mode)\" = shared\npkg-config --exists x11 xext x11-xcb xcb xcb-randr xcb-glx xcb-shm xcb-dri3 xcb-present xcb-sync xcb-xfixes xshmfence xxf86vm libdrm expat zlib\nmeson setup build-mesa upstream/mesa-25.3.0 --prefix=/usr --libdir=lib --buildtype=release -Dplatforms=x11 -Dgallium-drivers=swrast -Dvulkan-drivers= -Dglx=dri -Degl=disabled -Dgbm=disabled -Dglvnd=disabled -Dllvm=enabled -Dshared-llvm=enabled -Dopengl=true -Dbuild-tests=false -Dallow-fallback-for= -Dauto_features=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-mesa -j 2"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -f build-mesa/meson-info/intro-buildoptions.json\npython3 - <<'PY'\nimport json\nfrom pathlib import Path\noptions={x['name']:x['value'] for x in json.loads(Path('build-mesa/meson-info/intro-buildoptions.json').read_text())}\nassert options['gallium-drivers']==['swrast']\nassert options['glx']=='dri'\nassert options['vulkan-drivers']==[]\nassert options['llvm'] in ('enabled','True',True)\nPY\n# Renderer and GLX functional verification is native-only, never source CI."
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; meson install -C build-mesa --destdir \"$DESTDIR\"\ntest -e \"$DESTDIR/usr/lib/libGL.so\"\ntest -e \"$DESTDIR/usr/lib/dri/swrast_dri.so\"\ninstall -Dm644 \"upstream/mesa-25.3.0/docs/license.rst\" \"$DESTDIR/usr/share/licenses/mesa/license.rst\"\ninstall -Dm644 \"upstream/mesa-25.3.0/src/mesa/glapi/glapi/gen/license.py\" \"$DESTDIR/usr/share/licenses/mesa/glapi-generator-license.py\""
    ]
  ]
}

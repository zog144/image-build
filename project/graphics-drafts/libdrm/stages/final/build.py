# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "command -v meson; command -v ninja; command -v pkg-config\nmeson setup build-libdrm upstream/libdrm-2.4.128 --prefix=/usr --libdir=lib --buildtype=release -Dintel=disabled -Dradeon=disabled -Damdgpu=disabled -Dnouveau=disabled -Dvmwgfx=disabled -Domap=disabled -Dexynos=disabled -Dfreedreno=disabled -Dtegra=disabled -Dvc4=disabled -Detnaviv=disabled -Dcairo-tests=disabled -Dman-pages=disabled -Dvalgrind=disabled -Dinstall-test-programs=False -Dudev=False -Dtests=False -Dauto_features=disabled"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "meson compile -C build-libdrm -j 2"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -f build-libdrm/meson-info/intro-buildoptions.json\npython3 - <<'PY'\nimport json\nfrom pathlib import Path\nopts={x['name']:x['value'] for x in json.loads(Path('build-libdrm/meson-info/intro-buildoptions.json').read_text())}\nfor key in ('intel','radeon','amdgpu','nouveau','freedreno','vmwgfx','etnaviv'):\n assert opts[key] == 'disabled', (key, opts[key])\nassert opts['tests'] == False\nPY\n# No kernel /dev/dri or hardware APIs are exercised."
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; DESTDIR=\"$DESTDIR\" meson install -C build-libdrm\nfor required in \"$DESTDIR/usr/lib/libdrm.so\" \"$DESTDIR/usr/include/xf86drm.h\" \"$DESTDIR/usr/lib/pkgconfig/libdrm.pc\"; do test -e \"$required\"; done\ninstall -Dm644 \"upstream/libdrm-2.4.128/xf86drm.c\" \"$DESTDIR/usr/share/licenses/libdrm/xf86drm.c\"\ninstall -Dm644 \"upstream/libdrm-2.4.128/xf86drm.h\" \"$DESTDIR/usr/share/licenses/libdrm/xf86drm.h\""
    ]
  ]
}

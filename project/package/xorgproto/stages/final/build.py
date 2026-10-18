# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/xorgproto-2026.1\n'
                'meson setup build --prefix=/usr --libdir=lib --wrap-mode=nodownload '
                '-Dlegacy=false']],
 'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            'cd upstream/xorgproto-2026.1\nninja -C build']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/xorgproto-2026.1\n'
           "python3 -c 'import libevdev; assert libevdev.EV_KEY.KEY_MAX.value > 0'\n"
           'meson test -C build --print-errorlogs']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/xorgproto-2026.1\n'
              'test -n "$DESTDIR"\n'
              'DESTDIR="$DESTDIR" meson install -C build --no-rebuild\n'
              'install -d "$DESTDIR/usr/share/licenses/xorgproto"\n'
              'install -Dm644 COPYING-applewmproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-applewmproto"\n'
              'install -Dm644 COPYING-bigreqsproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-bigreqsproto"\n'
              'install -Dm644 COPYING-compositeproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-compositeproto"\n'
              'install -Dm644 COPYING-damageproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-damageproto"\n'
              'install -Dm644 COPYING-dmxproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-dmxproto"\n'
              'install -Dm644 COPYING-dri2proto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-dri2proto"\n'
              'install -Dm644 COPYING-dri3proto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-dri3proto"\n'
              'install -Dm644 COPYING-evieproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-evieproto"\n'
              'install -Dm644 COPYING-fixesproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-fixesproto"\n'
              'install -Dm644 COPYING-fontcacheproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-fontcacheproto"\n'
              'install -Dm644 COPYING-fontsproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-fontsproto"\n'
              'install -Dm644 COPYING-glproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-glproto"\n'
              'install -Dm644 COPYING-inputproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-inputproto"\n'
              'install -Dm644 COPYING-kbproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-kbproto"\n'
              'install -Dm644 COPYING-lg3dproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-lg3dproto"\n'
              'install -Dm644 COPYING-pmproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-pmproto"\n'
              'install -Dm644 COPYING-presentproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-presentproto"\n'
              'install -Dm644 COPYING-printproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-printproto"\n'
              'install -Dm644 COPYING-randrproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-randrproto"\n'
              'install -Dm644 COPYING-recordproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-recordproto"\n'
              'install -Dm644 COPYING-renderproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-renderproto"\n'
              'install -Dm644 COPYING-resourceproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-resourceproto"\n'
              'install -Dm644 COPYING-scrnsaverproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-scrnsaverproto"\n'
              'install -Dm644 COPYING-trapproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-trapproto"\n'
              'install -Dm644 COPYING-videoproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-videoproto"\n'
              'install -Dm644 COPYING-windowswmproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-windowswmproto"\n'
              'install -Dm644 COPYING-x11proto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-x11proto"\n'
              'install -Dm644 COPYING-xcmiscproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xcmiscproto"\n'
              'install -Dm644 COPYING-xextproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xextproto"\n'
              'install -Dm644 COPYING-xf86bigfontproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xf86bigfontproto"\n'
              'install -Dm644 COPYING-xf86dgaproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xf86dgaproto"\n'
              'install -Dm644 COPYING-xf86driproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xf86driproto"\n'
              'install -Dm644 COPYING-xf86miscproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xf86miscproto"\n'
              'install -Dm644 COPYING-xf86rushproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xf86rushproto"\n'
              'install -Dm644 COPYING-xf86vidmodeproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xf86vidmodeproto"\n'
              'install -Dm644 COPYING-xineramaproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xineramaproto"\n'
              'install -Dm644 COPYING-xwaylandproto '
              '"$DESTDIR/usr/share/licenses/xorgproto/COPYING-xwaylandproto"']]}

# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/xcb-util-xrm-1.3\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static --disable-silent-rules']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/xcb-util-xrm-1.3\nmake -j8']],
 'test': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/xcb-util-xrm-1.3\nmake check']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/xcb-util-xrm-1.3\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'find "$DESTDIR/usr/lib" -name \'*.la\' -delete\n'
              'install -d "$DESTDIR/usr/share/licenses/xcb-util-xrm"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/xcb-util-xrm/COPYING"']]}

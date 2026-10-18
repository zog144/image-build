# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/xcb-util-0.4.1\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static --disable-silent-rules']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/xcb-util-0.4.1\nmake -j8']],
 'test': [],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/xcb-util-0.4.1\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'find "$DESTDIR/usr/lib" -name \'*.la\' -delete\n'
              'install -d "$DESTDIR/usr/share/licenses/xcb-util"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/xcb-util/COPYING"']]}

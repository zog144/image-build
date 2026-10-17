# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/libXau-1.0.12\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/libXau-1.0.12\nmake -j8']],
 'test': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/libXau-1.0.12\nmake check']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/libXau-1.0.12\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/libXau"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/libXau/COPYING"']]}

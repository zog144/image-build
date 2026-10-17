# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/check-0.15.2\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static --disable-subunit']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/check-0.15.2\nmake -j8']],
 'test': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/check-0.15.2\nmake check']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/check-0.15.2\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/check"\n'
              'install -Dm644 COPYING.LESSER "$DESTDIR/usr/share/licenses/check/COPYING.LESSER"\n'
              'rm -f "$DESTDIR/usr/share/info/dir"']]}

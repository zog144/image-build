# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/fontconfig-2.18.3\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static --sysconfdir=/etc '
                '--localstatedir=/var --disable-docs --enable-libxml2=no']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/fontconfig-2.18.3\nmake -j8']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/fontconfig-2.18.3\nmake check']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/fontconfig-2.18.3\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/fontconfig"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/fontconfig/COPYING"']]}

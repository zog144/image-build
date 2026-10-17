# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/libxcb-1.17.0\n'
                'pkg-config --exists "check >= 0.9.6" xdmcp\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static --without-doxygen '
                '--disable-devel-docs\n'
                'grep -q "^#define HASXDMAUTH 1" src/config.h']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/libxcb-1.17.0\nmake -j8']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/libxcb-1.17.0\n'
           'test -x tests/check_all || make -C tests check_all\n'
           'make check\n'
           'test -f tests/check_all.trs\n'
           "grep -q '^:test-result: PASS' tests/check_all.trs"]],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/libxcb-1.17.0\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/libxcb"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/libxcb/COPYING"']]}

# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/libXdmcp-1.1.5\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static --enable-unit-tests '
                '--disable-docs']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/libXdmcp-1.1.5\nmake -j8']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/libXdmcp-1.1.5\n'
           'make check\n'
           'test -f test/Array.trs\n'
           "grep -q '^:test-result: PASS' test/Array.trs"]],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/libXdmcp-1.1.5\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/libXdmcp"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/libXdmcp/COPYING"']]}

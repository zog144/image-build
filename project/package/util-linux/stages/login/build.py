# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/util-linux-2.42.2\n'
                './configure --prefix=/usr --bindir=/usr/bin --sbindir=/usr/sbin --libdir=/usr/lib '
                '--disable-all-programs --enable-login --disable-pylibmount --disable-static '
                '--disable-liblastlog2 --without-python --disable-makeinstall-chown '
                '--disable-makeinstall-setuid']],
 'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            'cd upstream/util-linux-2.42.2\nmake -j8 login']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/util-linux-2.42.2\n./login --version']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/util-linux-2.42.2\n'
              'install -Dm755 login "$DESTDIR/usr/bin/login"\n'
              'install -d "$DESTDIR/usr/share/licenses/util-linux-login"\n'
              'cp -a COPYING README.licensing Documentation/licenses '
              '"$DESTDIR/usr/share/licenses/util-linux-login/"']]}

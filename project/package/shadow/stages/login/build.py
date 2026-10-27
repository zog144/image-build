# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/shadow-4.20.2\n'
                './configure --prefix=/usr --bindir=/usr/bin --sbindir=/usr/sbin '
                '--disable-man --disable-logind --disable-subordinate-ids '
                '--without-libpam --without-audit --without-selinux --without-acl '
                '--without-btrfs --without-tcb --without-nscd --without-sssd '
                '--without-su --without-libbsd --without-skey']],
 'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            'cd upstream/shadow-4.20.2\n'
            'test -f config.h\n'
            'test -f lib/Makefile\n'
            'test -f src/Makefile\n'
            'make -C lib -j8 libshadow.la\n'
            'test -f lib/libshadow.la\n'
            'make -C src -j8 login']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/shadow-4.20.2\n'
           'test -f config.h\n'
           'test -f lib/libshadow.la\n'
           'test -x src/login\n'
           "readelf -h src/login | grep -q 'Class:.*ELF64'\n"
           "! readelf -d src/login | grep -q 'libpam'\n"
           "readelf -d src/login | grep -q 'libcrypt'"]],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/shadow-4.20.2\n'
              'install -Dm755 src/login "$DESTDIR/usr/bin/login"']]}

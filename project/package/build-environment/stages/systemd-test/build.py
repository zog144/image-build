# Reviewed public candidate; data only, parsed with ast.literal_eval.
{'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cmp inputs/os-release build/os-release\n'
           '. inputs/os-release\n'
           'test "$ID" = zog\n'
           'test "$BUILD_ID" = systemd-261.2-test\n'
           'test "$NAME" = \'Zog build environment\'']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'install -Dm644 build/os-release "$DESTDIR/etc/os-release"\n'
              'install -Dm644 inputs/COPYRIGHT '
              '"$DESTDIR/usr/share/licenses/build-environment/COPYRIGHT"'],
             ['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'install -Dm644 "inputs/LICENSES/BSD-3-Clause.txt" '
              '"$DESTDIR/usr/share/licenses/build-environment/LICENSES/BSD-3-Clause.txt"\n'
              'install -Dm644 "inputs/LICENSES/GPL-3.0-only.txt" '
              '"$DESTDIR/usr/share/licenses/build-environment/LICENSES/GPL-3.0-only.txt"']],
 'build': [['/bin/bash',
            '-eu',
            '-c',
            'mkdir -p build\ninstall -m644 inputs/os-release build/os-release']]}

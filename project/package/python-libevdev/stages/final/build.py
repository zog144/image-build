# Data only; parsed with ast.literal_eval.
{'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            'cd upstream/libevdev-0.13.1\n'
            'python3 -m compileall -q libevdev\n']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/libevdev-0.13.1\n'
           'PYTHONPATH=. python3 - <<\'ZOG_TEST\'\n'
           'import libevdev\n'
           'assert libevdev.EV_KEY.KEY_MAX.value > 0\n'
           'assert libevdev.EV_ABS.ABS_MAX.value > 0\n'
           'assert libevdev.EV_REL.REL_X.value >= 0\n'
           'print("ZOG_PYTHON_LIBEVDEV_CONSTANTS", libevdev.EV_KEY.KEY_MAX.value)\n'
           'ZOG_TEST\n']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/libevdev-0.13.1\n'
              'site="$DESTDIR/usr/lib/python3.15/site-packages"\n'
              'install -d "$site" "$DESTDIR/usr/share/licenses/python-libevdev"\n'
              'cp -a libevdev "$site/"\n'
              'install -m 0644 COPYING "$DESTDIR/usr/share/licenses/python-libevdev/COPYING"\n'
              'PYTHONPATH="$site" python3 -s -c \'import libevdev; assert libevdev.EV_KEY.KEY_MAX.value > 0; print("ZOG_INSTALLED_IMPORT", libevdev.EV_KEY.KEY_MAX.value)\'\n']],
 'environment': {'PYTHONNOUSERSITE': '1'}}

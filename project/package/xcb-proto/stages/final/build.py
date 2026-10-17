# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/xcb-proto-1.17.0\n./configure --prefix=/usr --libdir=/usr/lib ']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/xcb-proto-1.17.0\nmake -j8']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/xcb-proto-1.17.0\n'
           'make check\n'
           "PYTHONPATH=. python3 - <<'EOF'\n"
           'import pathlib,xml.etree.ElementTree as ET\n'
           'import xcbgen.state\n'
           "paths=list(pathlib.Path('src').glob('*.xml')); assert len(paths)>20\n"
           "for path in paths: assert ET.parse(path).getroot().tag == 'xcb'\n"
           "print('XCB_XML_PARSE_PASS', len(paths))\n"
           'EOF']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/xcb-proto-1.17.0\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/xcb-proto"\n'
              'install -Dm644 COPYING "$DESTDIR/usr/share/licenses/xcb-proto/COPYING"']]}

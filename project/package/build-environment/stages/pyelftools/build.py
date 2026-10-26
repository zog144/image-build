# Data only; parsed with ast.literal_eval.
{'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            'cd upstream/pyelftools-0.33\n'
            "python3 - <<'PYCHECK'\n"
            'import sys\n'
            "assert sys.version_info[:2] == (3, 15), sys.version\n"
            'import elftools\n'
            "assert elftools.__version__ == '0.33'\n"
            'from elftools.elf.elffile import ELFFile\n'
            'with open(sys.executable, "rb") as stream:\n'
            ' elf = ELFFile(stream)\n'
            ' assert elf.num_sections() > 0\n'
            "print('ZOG_PYELFTOOLS_BUILD_INPUT_PASS')\n"
            'PYCHECK']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/pyelftools-0.33\n'
           'test -f LICENSE\n'
           'test -f elftools/construct/LICENSE\n'
           "PYTHONPATH=. python3 -c \"from elftools.elf.elffile import ELFFile; import elftools; assert elftools.__version__ == '0.33'\""]],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/pyelftools-0.33\n'
              'dest="$DESTDIR/usr/lib/python3.15/site-packages"\n'
              'install -d "$dest"\n'
              'cp -a elftools "$dest/"\n'
              'find "$dest/elftools" -type d -name __pycache__ -prune -exec rm -rf {} +\n'
              'install -d "$DESTDIR/usr/share/licenses/build-pyelftools"\n'
              'install -m644 LICENSE "$DESTDIR/usr/share/licenses/build-pyelftools/LICENSE"\n'
              'install -m644 elftools/construct/LICENSE '
              '"$DESTDIR/usr/share/licenses/build-pyelftools/CONSTRUCT-LICENSE"']]}

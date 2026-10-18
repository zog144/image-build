# Data only; parsed with ast.literal_eval.
{'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/freetype-2.14.3\n'
                './configure --prefix=/usr --libdir=/usr/lib --disable-static '
                '--enable-freetype-config --with-zlib=yes --with-bzip2=yes --with-png=yes '
                '--with-harfbuzz=no --with-brotli=no']],
 'build': [['/bin/bash', '-eu', '-o', 'pipefail', '-c', 'cd upstream/freetype-2.14.3\nmake -j8']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/freetype-2.14.3\n'
           "cat > ft-smoke.c <<'EOF'\n"
           '#include <ft2build.h>\n'
           '#include FT_FREETYPE_H\n'
           'int main(void) { FT_Library l; FT_Int a,b,c;\n'
           ' if (FT_Init_FreeType(&l)) return 1;\n'
           ' FT_Library_Version(l,&a,&b,&c);\n'
           ' if (a != FREETYPE_MAJOR || b != FREETYPE_MINOR || c != FREETYPE_PATCH) return 2;\n'
           ' return FT_Done_FreeType(l); }\n'
           'EOF\n'
           './builds/unix/libtool --mode=link cc -Iinclude ft-smoke.c objs/libfreetype.la -o '
           'ft-smoke\n'
           './ft-smoke']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/freetype-2.14.3\n'
              'test -n "$DESTDIR"\n'
              'make DESTDIR="$DESTDIR" install\n'
              'install -d "$DESTDIR/usr/share/licenses/freetype"\n'
              'install -Dm644 LICENSE.TXT "$DESTDIR/usr/share/licenses/freetype/LICENSE.TXT"\n'
              'install -Dm644 docs/FTL.TXT "$DESTDIR/usr/share/licenses/freetype/docs/FTL.TXT"\n'
              'install -Dm644 docs/GPLv2.TXT '
              '"$DESTDIR/usr/share/licenses/freetype/docs/GPLv2.TXT"\n'
              'install -Dm644 src/bdf/README '
              '"$DESTDIR/usr/share/licenses/freetype/src/bdf/README"\n'
              'install -Dm644 src/pcf/README '
              '"$DESTDIR/usr/share/licenses/freetype/src/pcf/README"\n'
              'install -Dm644 src/gzip/zlib.h '
              '"$DESTDIR/usr/share/licenses/freetype/src/gzip/zlib.h"\n'
              'install -Dm644 src/autofit/ft-hb-ft.c '
              '"$DESTDIR/usr/share/licenses/freetype/src/autofit/ft-hb-ft.c"']]}

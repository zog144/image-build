# Keep these exact bytes for both generations' installed-native-tools check.
set -eu
export LC_ALL=C
pkg-config --exists libpng freetype2 fontconfig
cat > graphics-common.c <<'EOF'
#include <png.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include <fontconfig/fontconfig.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    png_image out = {0}, in = {0};
    png_byte pixel[4] = {21, 42, 63, 255}, decoded[4];
    png_alloc_size_t size = 0;
    out.version = PNG_IMAGE_VERSION; out.width = out.height = 1;
    out.format = PNG_FORMAT_RGBA;
    if (!png_image_write_to_memory(&out, NULL, &size, 0, pixel, 0, NULL)) return 1;
    void *data = malloc(size); if (!data) return 2;
    if (!png_image_write_to_memory(&out, data, &size, 0, pixel, 0, NULL)) return 3;
    in.version = PNG_IMAGE_VERSION;
    if (!png_image_begin_read_from_memory(&in, data, size)) return 4;
    in.format = PNG_FORMAT_RGBA;
    if (!png_image_finish_read(&in, NULL, decoded, 0, NULL)) return 5;
    if (memcmp(pixel, decoded, sizeof pixel)) return 6;
    png_image_free(&in); free(data);
    FT_Library library;
    if (FT_Init_FreeType(&library)) return 7;
    FT_Int major, minor, patch;
    FT_Library_Version(library, &major, &minor, &patch);
    if (major != FREETYPE_MAJOR || minor != FREETYPE_MINOR || patch != FREETYPE_PATCH) return 8;
    if (FT_Done_FreeType(library)) return 9;
    FcPattern *pattern = FcNameParse((const FcChar8 *)"sans:size=12");
    if (!pattern) return 10;
    double size_value;
    int valid = FcPatternGetDouble(pattern, FC_SIZE, 0, &size_value) == FcResultMatch && size_value == 12;
    FcPatternDestroy(pattern);
    if (!valid || FcGetVersion() != FC_VERSION) return 11;
    return 0;
}
EOF
cc -Wall -Wextra -Werror $(pkg-config --cflags libpng freetype2 fontconfig) graphics-common.c \
    $(pkg-config --libs libpng freetype2 fontconfig) -o graphics-common
./graphics-common
python3 - <<'PY'
import ssl, sqlite3
assert ssl.OPENSSL_VERSION
with sqlite3.connect(':memory:') as db:
    assert db.execute('select 6 * 7').fetchone() == (42,)
print('GRAPHICS_COMMON_PASS')
PY

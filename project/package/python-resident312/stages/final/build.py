# Draft source-only candidate. Commands execute ONLY in an independently selected isolated rootfs.
# Data is loaded via ast.literal_eval; none of these commands ran in source CI.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ntest -s /usr/include/openssl/ssl.h\ntest -s /usr/include/sqlite3.h\ntest -e /usr/lib/libssl.so\ntest -e /usr/lib/libcrypto.so\ntest -e /usr/lib/libsqlite3.so\ntest -x /usr/bin/pkg-config\n/usr/bin/pkg-config --modversion openssl sqlite3\ncd upstream/Python-3.12.16\n./configure --prefix=/usr --libdir=lib --with-platlibdir=lib --enable-shared --without-ensurepip --with-openssl=/usr --with-openssl-rpath=no --with-system-expat --enable-loadable-sqlite-extensions\ngrep -Eq '^MODULE__SSL_STATE=yes$' Makefile\ngrep -Eq '^MODULE__SQLITE3_STATE=yes$' Makefile\ngrep -Eq '^MODULE__HASHLIB_STATE=yes$' Makefile\n"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/Python-3.12.16; make -j8"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/Python-3.12.16\nLD_LIBRARY_PATH=\"$PWD\" ./python -I -S - <<'ZOG_NATIVE_MODULES'\nimport sys,sysconfig,ssl,sqlite3,_ssl,_sqlite3,_hashlib\nassert sys.version_info[:3] == (3,12,16)\nassert sysconfig.get_config_var('SOABI') == 'cpython-312-x86_64-linux-gnu'\nassert 'OpenSSL' in ssl.OPENSSL_VERSION\nassert sqlite3.sqlite_version_info >= (3,35,0)\ndb=sqlite3.connect(':memory:')\nassert db.execute('select 1').fetchone() == (1,)\nprint('ZOG_PYTHON312_BUILD_SSL_SQLITE_PASS')\nZOG_NATIVE_MODULES\n"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ntest -n \"${DESTDIR:-}\"\ncd upstream/Python-3.12.16\nmake DESTDIR=\"$DESTDIR\" altinstall\ntest -x \"$DESTDIR/usr/bin/python3.12\"\ntest -e \"$DESTDIR/usr/lib/libpython3.12.so.1.0\"\ntest -e \"$DESTDIR/usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so\"\ntest -e \"$DESTDIR/usr/lib/python3.12/lib-dynload/_sqlite3.cpython-312-x86_64-linux-gnu.so\"\ntest -e \"$DESTDIR/usr/lib/python3.12/lib-dynload/_hashlib.cpython-312-x86_64-linux-gnu.so\"\n# Do not create /usr/bin/python3 or replace the separately pinned 3.15 producer.\n"
    ]
  ],
  "environment": {
    "PYTHONNOUSERSITE": "1",
    "PYTHONSAFEPATH": "1",
    "PKG_CONFIG_LIBDIR": "/usr/lib/pkgconfig:/usr/share/pkgconfig",
    "PKG_CONFIG_SYSROOT_DIR": "/",
    "PIP_NO_INDEX": "1"
  }
}

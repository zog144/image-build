# Data only; parsed with ast.literal_eval.
{'prepare': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              "python3 - <<'PYCHECK'\n"
              'import elftools\n'
              "assert elftools.__version__ == '0.33', elftools.__version__\n"
              'from elftools.elf.elffile import ELFFile\n'
              'import sys\n'
              'with open(sys.executable, "rb") as stream:\n'
              ' assert ELFFile(stream).num_sections() > 0\n'
              "print('ZOG_SYSTEMD_PYELFTOOLS_INPUT_PASS')\n"
              'PYCHECK']],
 'configure': [['/bin/bash',
                '-eu',
                '-o',
                'pipefail',
                '-c',
                'cd upstream/systemd-261.2\n'
                'meson setup build --prefix=/usr --libdir=lib --sysconfdir=/etc '
                '--localstatedir=/var --buildtype=release --wrap-mode=nodownload '
                '--auto-features=disabled -Dmode=release -Dsplit-bin=false -Dtests=true '
                '-Dinstall-tests=false -Dlibmount=enabled -Dblkid=enabled -Dacl=enabled '
                '-Dseccomp=enabled -Dlibcrypt=enabled -Dkmod=enabled -Dlz4=enabled -Dpcre2=enabled -Dopenssl=enabled '
                '-Dxz=enabled -Dzstd=enabled -Dzlib=enabled -Dnetworkd=true -Dresolve=true '
                '-Dtimesyncd=true -Dsysusers=true -Dtmpfiles=true -Dhwdb=true -Dfirstboot=false '
                '-Dldconfig=false -Drpmmacrosdir=no -Dpamconfdir=no -Ddev-kvm-mode=0660 '
                '-Ddefault-dnssec=no -Ddefault-mdns=no -Ddefault-llmnr=no -Ddns-over-tls=openssl '
                '-Dhomed=disabled -Dlogind=false -Duserdb=false -Dnss-systemd=false '
                '-Dmachined=false -Dportabled=false -Dnspawn=disabled -Dsysext=false '
                '-Dmountfsd=false -Dnsresourced=false -Dvmspawn=disabled -Dsysinstall=false '
                '-Dstoragetm=false -Drepart=disabled -Dsysupdate=disabled -Dimds=disabled '
                '-Dbpf-framework=disabled -Defi=true -Dbootloader=enabled -Dukify=disabled '
                '-Dsbat-distro=zog -Dsbat-distro-generation=1 '
                "-Dsbat-distro-summary='Zog Project' -Dsbat-distro-pkgname=systemd "
                '-Dsbat-distro-version=261.2 '
                '-Dsbat-distro-url=https://github.com/zog144/image-build '
                '-Dman=disabled -Dhtml=disabled -Dtranslations=false']],
 'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            'cd upstream/systemd-261.2\n'
            'meson compile -C build -j8\n'
            '# Meson test dependencies are not default build targets.\n'
            'ninja -C build -j8 test/fuzz/directives.automount test/fuzz/directives.mount '
            'test/fuzz/directives.path test/fuzz/directives.scope test/fuzz/directives.service '
            'test/fuzz/directives.slice test/fuzz/directives.socket test/fuzz/directives.swap '
            'test/fuzz/directives.timer test/fuzz/directives.link test/fuzz/directives.netdev '
            'test/fuzz/directives.network']],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           'cd upstream/systemd-261.2\n'
           'export LANG=C.UTF-8 LC_ALL=C.UTF-8\n'
           '# Fiber guard probe covers 64 MiB; compilation retains its larger limit.\n'
           'ulimit -S -s 8192\n'
           'meson test -C build --no-rebuild --print-errorlogs -j4\n'
           '# Verify the emitted EFI SBAT row, not merely Meson option presence.\n'
           'sbat=$(mktemp)\n'
           "trap 'rm -f \"$sbat\"' EXIT\n"
           'objcopy --dump-section .sbat="$sbat" build/src/boot/systemd-bootx64.efi\n'
           "python3 - \"$sbat\" <<'PYSBAT'\n"
           'from pathlib import Path\n'
           'import sys\n'
           'data = Path(sys.argv[1]).read_bytes().rstrip(b"\\0").decode("utf-8")\n'
           'lines = data.splitlines()\n'
           "expected = 'systemd-boot.zog,1,Zog Project,systemd,261.2,https://github.com/zog144/image-build'\n"
           'assert expected in lines, lines\n'
           "assert not any('.auto,' in line for line in lines), lines\n"
           "print('ZOG_SYSTEMD_SBAT_SECTION_PASS')\n"
           'PYSBAT']],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'cd upstream/systemd-261.2\n'
              'DESTDIR="$DESTDIR" SYSTEMD_OFFLINE=1 meson install -C build --no-rebuild\n'
              '# Zog resident HOST mountpoints are empty fail-closed integration layout.\n'
              'install -d -m 0000 "$DESTDIR/state" "$DESTDIR/applications"\n'
              'install -d "$DESTDIR/usr/share/licenses/systemd"\n'
              'cp -a LICENSE.GPL2 LICENSE.LGPL2.1 LICENSES '
              '"$DESTDIR/usr/share/licenses/systemd/"']]}

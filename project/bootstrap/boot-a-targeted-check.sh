set -eu
test -x /usr/lib/systemd/systemd
test -x /usr/sbin/agetty
test -x /usr/bin/login
test -f /usr/lib/systemd/system/getty@.service
test -f /usr/lib/systemd/system/serial-getty@.service
test -f /usr/lib/systemd/boot/efi/systemd-bootx64.efi
test "$(stat -c '%a' /state)" = 0
test "$(stat -c '%a' /applications)" = 0
! readelf -d /usr/bin/login | grep -q 'libpam'
readelf -d /usr/bin/login | grep -q 'libcrypt'
systemd-analyze verify --man=no /usr/lib/systemd/system/getty@.service /usr/lib/systemd/system/serial-getty@.service
printf '%s\n' ZOG_BOOT_A_TARGETED_INSTALLED_PASS

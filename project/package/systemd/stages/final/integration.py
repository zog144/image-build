# Data only; parsed with ast.literal_eval.
{'project': 'systemd',
 'stage_id': 'final',
 'base_contract': 'Accepted native-systemd prerequisite generation supplies GCC, Meson/Ninja, '
                  'Gperf, Python/Jinja2, libmount/blkid, ACL, libxcrypt, Kmod, LZ4, PCRE2, '
                  'OpenSSL, zlib, xz and zstd. Exact inherited outputs bound by base-components. '
                  'No external libcap dependency in v261.2.',
 'sbat': {
  'contract': 'image-build-systemd-sbat-v1',
  'distro': 'zog',
  'generation': 1,
  'summary': 'Zog Project',
  'pkgname': 'systemd',
  'version': '261.2',
  'url': 'https://github.com/zog144/image-build',
  'generation_policy': 'Generation 1 is the first Zog SBAT generation. Increment only for an '
                       'explicit reviewed Zog SBAT revocation or compatibility boundary; ordinary '
                       'image-build source revisions do not change it.'}}

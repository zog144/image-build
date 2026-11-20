# Data-only reviewed source lock for the first executable Fonts stage sequence.
# Independent of the original retained compiler/monthly receipt; never overwrites it.
# Exact candidate releases, URLs and SHA-256 must match each selected stage's sources.py.
{'schema': 1,
 'date': '2026-11-01',
 'packages': {
  'libpng': {'recipes': {'libpng/stages/final': [
      {'url': 'https://downloads.sourceforge.net/libpng/libpng-1.6.58.tar.xz',
       'sha256': '28eb403f51f0f7405249132cecfe82ea5c0ef97f1b32c5a65828814ae0d34775',
       'destination': 'upstream', 'archive': True}
  ]}},
  'freetype': {'recipes': {'freetype/stages/final': [
      {'url': 'https://downloads.sourceforge.net/freetype/freetype-2.14.3.tar.xz',
       'sha256': '36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f',
       'destination': 'upstream', 'archive': True}
  ]}},
  'fontconfig': {'recipes': {'fontconfig/stages/final': [
      {'url': 'https://gitlab.freedesktop.org/api/v4/projects/890/packages/generic/fontconfig/2.18.3/fontconfig-2.18.3.tar.xz',
       'sha256': '4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3',
       'destination': 'upstream', 'archive': True}
  ]}},
 }}

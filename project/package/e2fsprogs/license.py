# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'e2fsprogs',
 'version': '1.47.4',
 'source': {'url': 'https://www.kernel.org/pub/linux/kernel/people/tytso/e2fsprogs/v1.47.4/e2fsprogs-1.47.4.tar.gz',
            'sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'},
 'status': 'declared',
 'expression': 'LicenseRef-e2fsprogs-upstream-terms',
 'scope': 'Exact release notices; component exceptions require per-file review before public '
          'redistribution.',
 'evidence': [{'path': 'e2fsprogs-1.47.4/NOTICE',
               'sha256': '5da5ef153e559c1d990d4c3eedbedd4442db892d37eae1f35fff069de8ec9020',
               'source_sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'},
              {'path': 'e2fsprogs-1.47.4/lib/uuid/COPYING',
               'sha256': '9b718a9460fed5952466421235bc79eb49d4e9eacc920d7a9dd6285ab8fd6c6d',
               'source_sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'},
              {'path': 'e2fsprogs-1.47.4/lib/et/error_message.c',
               'sha256': 'bf0589587982ca7db1172a26181d44e18bdc4bbbde966aa69370b83f548c1bf6',
               'source_sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'},
              {'path': 'e2fsprogs-1.47.4/lib/ss/listen.c',
               'sha256': '843ff6ada7212be79fc292bfe9b5105ce6e83abb847a1014a7147fe730a3b59c',
               'source_sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'},
              {'path': 'e2fsprogs-1.47.4/lib/ext2fs/tdb/patches/copyright',
               'sha256': 'a86f7fb0aee4945307d0989ddc5254191daa8632ea90aebf27ad68fe85bd7dfa',
               'source_sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'},
              {'path': 'e2fsprogs-1.47.4/util/ucd/README',
               'sha256': 'aabae6ed295e9b6ec80ee6af1c2821f21ecd2a06ea24836419ac344fea826f4e',
               'source_sha256': 'da274408bebbfd13a5a2fc3cfc66e3ffff17c48534673aa67f88d49b99123b96'}],
 'components': [{'scope': 'Other source, documentation and bundled components',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Top-level terms are not a blanket grant; retain all upstream source '
                          'notices.'},
                {'scope': 'utilities described by NOTICE',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'NOTICE identifies GPL version 2; exact per-file only/or-later '
                          'declarations remain unresolved. Actual packaged-output inclusion and '
                          'complete component review are pending.'},
                {'scope': 'lib/ext2fs; lib/e2p described by NOTICE',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'NOTICE identifies LGPL version 2; exact per-file only/or-later '
                          'declarations remain unresolved. Actual packaged-output inclusion and '
                          'complete component review are pending.'},
                {'scope': 'lib/uuid covered by lib/uuid/COPYING',
                 'expression': 'LicenseRef-e2fsprogs-uuid',
                 'status': 'declared',
                 'notes': 'Retain source/binary notice preservation and non-endorsement terms; '
                          'per-file scope still open. Actual packaged-output inclusion and '
                          'complete component review are pending.'},
                {'scope': 'lib/et/error_message.c; lib/ss/listen.c',
                 'expression': 'LicenseRef-e2fsprogs-MIT-SIPB',
                 'status': 'declared',
                 'notes': 'Custom permission includes name/publicity restriction; not a '
                          'canonical MIT equivalence claim. Actual packaged-output inclusion and '
                          'complete component review are pending.'},
                {'scope': 'lib/ext2fs/tdb/patches/copyright',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Bundled TDB patch notice has copyright adjustments and LGPL context; '
                          'complete version and shipping scope unresolved. Actual '
                          'packaged-output inclusion and complete component review are pending.'},
                {'scope': 'util/ucd Unicode data and generated utf8data.h',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'util/ucd/README identifies Unicode 11.0.0 inputs; applicable data '
                          'notice and generated-output inclusion remain unresolved. Actual '
                          'packaged-output inclusion and complete component review are '
                          'pending.'}],
 'patches': [],
 'notes': ['Exact release and listed notices inspected 2026-10-09. No upstream source patches. '
           'No public-release audit claimed.',
           '2026-10-15 private Work targeted archive/notice review: 6 observations, 5 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Map utility GPL, library LGPL, UUID and et/ss terms '
           'separately with exact version declarations.',
           'Open per-file/component review: Resolve Unicode-data and bundled TDB component '
           'notices and shipping scope.',
           'Open per-file/component review: Inspect Debian/ext2ed notices and all remaining '
           'per-file exceptions before approval.']}

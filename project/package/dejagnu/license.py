# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'dejagnu',
 'version': '1.6.3',
 'source': {'url': 'https://ftp.gnu.org/gnu/dejagnu/dejagnu-1.6.3.tar.gz',
            'sha256': '87daefacd7958b4a69f88c6856dbd1634261963c414079d0c371f589cd66a2e3'},
 'status': 'declared',
 'expression': 'LicenseRef-dejagnu-upstream-terms',
 'scope': 'Primary upstream declaration or retained top-level terms only; see component scopes '
          'and unresolved review notes.',
 'evidence': [{'path': 'dejagnu-1.6.3/COPYING',
               'sha256': '8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903',
               'source_sha256': '87daefacd7958b4a69f88c6856dbd1634261963c414079d0c371f589cd66a2e3'},
              {'path': 'dejagnu-1.6.3/README',
               'sha256': '0ba4a2560ac83bbf99fd34bbcf2ff0e4812b574a035da3318d19c480f38554bb',
               'source_sha256': '87daefacd7958b4a69f88c6856dbd1634261963c414079d0c371f589cd66a2e3'},
              {'path': 'dejagnu-1.6.3/runtest.exp',
               'sha256': 'f3a48b4e84b36b4a12d52ea389a072f5cbc9f9005d671669f6f5af7513a7a46e',
               'source_sha256': '87daefacd7958b4a69f88c6856dbd1634261963c414079d0c371f589cd66a2e3'},
              {'path': 'dejagnu-1.6.3/doc/dejagnu.texi',
               'sha256': '4ba75d75e9dcb000dcbf4c971e0c4ee1171957bbaa98e25de3525b9165936155',
               'source_sha256': '87daefacd7958b4a69f88c6856dbd1634261963c414079d0c371f589cd66a2e3'}],
 'components': [{'scope': 'Other included files, documentation, generated code and bundled '
                          'subprojects',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Complete per-file/stage scope review remains required; primary '
                          'declaration is not a blanket grant.'},
                {'scope': 'runtest.exp',
                 'expression': 'GPL-3.0-or-later',
                 'status': 'declared',
                 'notes': 'Exact runner declaration; primary generic expression remains '
                          'unchanged. Actual packaged-output inclusion and complete component '
                          'review are pending.'},
                {'scope': 'doc/dejagnu.texi',
                 'expression': 'GFDL-1.3-or-later',
                 'status': 'declared',
                 'notes': 'No invariant sections or cover texts declared. Actual packaged-output '
                          'inclusion and complete component review are pending.'}],
 'patches': [],
 'notes': ['Inspected exact release archive on 2026-09-27; source and evidence hashes are bound '
           'to this version.',
           'Declared is not release-reviewed. Per-component notices, exceptions and '
           'corresponding-source obligations require final review.',
           'LicenseRef denotes the retained upstream terms without claiming SPDX equivalence; it '
           'never denotes Zog first-party licensing.',
           '2026-10-15 private Work targeted archive/notice review: 3 observations, 2 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add manual component and evidence; retain '
           'generated/helper notices.',
           'Open per-file/component review: Narrow generic LicenseRef only where exact source '
           'declarations support it.']}

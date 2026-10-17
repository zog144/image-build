# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'bison',
 'version': '3.8.2',
 'source': {'url': 'https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.xz',
            'sha256': '9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'},
 'status': 'declared',
 'expression': 'GPL-3.0-or-later',
 'scope': 'Primary upstream declaration or retained top-level terms only; see component scopes '
          'and unresolved review notes.',
 'evidence': [{'path': 'bison-3.8.2/README',
               'sha256': '19a802ad381694b73268cde2453f6ee8d6d7ca4eed72bc515be3c4255c022f4d',
               'source_sha256': '9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'},
              {'path': 'bison-3.8.2/COPYING',
               'sha256': '3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986',
               'source_sha256': '9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'},
              {'path': 'bison-3.8.2/src/main.c',
               'sha256': 'f9059707d20e0f115192b6bf1ebd6bae8c19c0c1c6a5b5a9ea2cf67653555a94',
               'source_sha256': '9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'},
              {'path': 'bison-3.8.2/data/skeletons/yacc.c',
               'sha256': '998d3a462761d5e6b9c408b6744b8741dc5b59eb7df47e9057055de45ee799df',
               'source_sha256': '9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'},
              {'path': 'bison-3.8.2/data/skeletons/bison.m4',
               'sha256': 'a3056074b9d6da3866e4dff3d8fba2b9d81d1ca2ca74920718586822d60df767',
               'source_sha256': '9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'}],
 'components': [{'scope': 'Generated parsers from exception-bearing skeletons',
                 'expression': 'GPL-3.0-or-later WITH Bison-exception-2.2',
                 'status': 'unresolved',
                 'notes': 'Review the installed skeleton and its exception text; this does not '
                          'change the license of the Bison executable.'},
                {'scope': 'Other included files, documentation, generated code and bundled '
                          'subprojects',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Complete per-file/stage scope review remains required; primary '
                          'declaration is not a blanket grant.'},
                {'scope': 'src/main.c',
                 'expression': 'GPL-3.0-or-later',
                 'status': 'declared',
                 'notes': 'Generator declaration recorded in targeted findings. Actual '
                          'packaged-output inclusion and complete component review are pending.'},
                {'scope': 'data/skeletons/bison.m4; data/skeletons/yacc.c',
                 'expression': 'GPL-3.0-or-later WITH Bison-exception-2.2',
                 'status': 'declared',
                 'notes': 'Complete exception is in bison.m4: parser-generator exclusion and '
                          'optional exception removal must remain explicit; no blanket approval '
                          'of generated outputs. Actual packaged-output inclusion and complete '
                          'component review are pending.'},
                {'scope': 'documentation declared in README',
                 'expression': 'GFDL-1.3-or-later',
                 'status': 'declared',
                 'notes': 'No invariant sections or cover texts declared; document-specific '
                          'inclusion inventory remains open. Actual packaged-output inclusion '
                          'and complete component review are pending.'}],
 'patches': [],
 'notes': ['Inspected exact release archive on 2026-09-27; source and evidence hashes are bound '
           'to this version.',
           'Declared is not release-reviewed. Per-component notices, exceptions and '
           'corresponding-source obligations require final review.',
           'LicenseRef denotes the retained upstream terms without claiming SPDX equivalence; it '
           'never denotes Zog first-party licensing.',
           '2026-10-15 private Work targeted archive/notice review: 5 observations, 1 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add bison.m4 as exact notice evidence; keep '
           'generator licensing separate from parser output exception.',
           'Open per-file/component review: Map documentation and generated/build helpers '
           'separately.']}

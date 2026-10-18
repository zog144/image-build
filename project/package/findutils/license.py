# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'findutils',
 'version': '4.11.0',
 'source': {'url': 'https://ftp.gnu.org/gnu/findutils/findutils-4.11.0.tar.xz',
            'sha256': 'bfd19cb06cc71f3352d567e90284d8cdac02ac89774bbeadf0b533b0c11432fd'},
 'status': 'declared',
 'expression': 'LicenseRef-findutils-upstream-terms',
 'scope': 'Primary upstream declaration or retained top-level terms only; see component scopes '
          'and unresolved review notes.',
 'evidence': [{'path': 'findutils-4.11.0/COPYING',
               'sha256': '3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986',
               'source_sha256': 'bfd19cb06cc71f3352d567e90284d8cdac02ac89774bbeadf0b533b0c11432fd'},
              {'path': 'findutils-4.11.0/README',
               'sha256': 'b735d5e5875483854e62a6e4b608155451aa75c39628e40d5b501cd0f464f527',
               'source_sha256': 'bfd19cb06cc71f3352d567e90284d8cdac02ac89774bbeadf0b533b0c11432fd'},
              {'path': 'findutils-4.11.0/find/defs.h',
               'sha256': '4d411ef34bf670d54f469c6b94ccc97123f166832dfba3e9ac3b60a1e041d9d9',
               'source_sha256': 'bfd19cb06cc71f3352d567e90284d8cdac02ac89774bbeadf0b533b0c11432fd'},
              {'path': 'findutils-4.11.0/doc/find.texi',
               'sha256': 'b7771cfc1fd681462f937842ef066c3affe34d0cec3d89084cdcb99556c7efbe',
               'source_sha256': 'bfd19cb06cc71f3352d567e90284d8cdac02ac89774bbeadf0b533b0c11432fd'}],
 'components': [{'scope': 'Other included files, documentation, generated code and bundled '
                          'subprojects',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Complete per-file/stage scope review remains required; primary '
                          'declaration is not a blanket grant.'},
                {'scope': 'find/defs.h',
                 'expression': 'GPL-3.0-or-later',
                 'status': 'declared',
                 'notes': 'Exact program header declaration. Actual packaged-output inclusion '
                          'and complete component review are pending.'},
                {'scope': 'doc/find.texi',
                 'expression': 'GFDL-1.3-or-later',
                 'status': 'declared',
                 'notes': 'No invariant sections or cover texts declared. Historical '
                          'public-domain locate ancestry is not a current blanket grant. Actual '
                          'packaged-output inclusion and complete component review are '
                          'pending.'}],
 'patches': [],
 'notes': ['Inspected exact release archive on 2026-09-27; source and evidence hashes are bound '
           'to this version.',
           'Declared is not release-reviewed. Per-component notices, exceptions and '
           'corresponding-source obligations require final review.',
           'LicenseRef denotes the retained upstream terms without claiming SPDX equivalence; it '
           'never denotes Zog first-party licensing.',
           '2026-10-15 private Work targeted archive/notice review: 4 observations, 2 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add manual component and exact evidence.',
           'Open per-file/component review: Close gnulib, generated helper and exception scopes '
           'separately.']}

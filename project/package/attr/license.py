# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'attr',
 'version': '2.6.0',
 'source': {'url': 'https://download.savannah.gnu.org/releases/attr/attr-2.6.0.tar.gz',
            'sha256': 'd42fa374513180bb48cb11a46696f488240e5124ff1e6ad88b0abff706985612'},
 'status': 'declared',
 'expression': 'GPL-2.0-or-later AND LGPL-2.1-or-later',
 'scope': 'Primary project/library/tool terms; component detail remains subject to release '
          'review.',
 'evidence': [{'path': 'attr-2.6.0/doc/COPYING',
               'sha256': '98f318493be6b08bff3cd295791cde06c54e17882a3c74a1ed245eaa02533d52',
               'source_sha256': 'd42fa374513180bb48cb11a46696f488240e5124ff1e6ad88b0abff706985612'},
              {'path': 'attr-2.6.0/doc/COPYING.LGPL',
               'sha256': '5decad7e58d90d44335bf2f45ce27563bd911065c6a1a02dfa7647c4efee75c8',
               'source_sha256': 'd42fa374513180bb48cb11a46696f488240e5124ff1e6ad88b0abff706985612'},
              {'path': 'attr-2.6.0/tools/getfattr.c',
               'sha256': 'ea1de68e40eaeb0224824e200f47b7fe8c7ec36c61ca15a3178c88731f5f8564',
               'source_sha256': 'd42fa374513180bb48cb11a46696f488240e5124ff1e6ad88b0abff706985612'},
              {'path': 'attr-2.6.0/libattr/attr_copy_file.c',
               'sha256': '20a81b02d6d78ecd972a4ccf1fe42dd294db2b203834430722e311b81a633d2b',
               'source_sha256': 'd42fa374513180bb48cb11a46696f488240e5124ff1e6ad88b0abff706985612'}],
 'components': [{'scope': 'Auxiliary files, bundled tests and licensing exceptions',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Remaining attr-specific utilities, library helpers, generated build '
                          'inputs, tests and documentation require a complete per-file and '
                          'shipped-artifact review. getfattr.c and attr_copy_file.c are '
                          'separately recorded as source-bound GPL and LGPL scope evidence.'},
                {'scope': 'tools/getfattr.c',
                 'expression': 'GPL-2.0-or-later',
                 'status': 'declared',
                 'notes': 'Utility header; remaining utility inventory is unresolved. Actual '
                          'packaged-output inclusion and complete component review are pending.'},
                {'scope': 'libattr/attr_copy_file.c',
                 'expression': 'LGPL-2.1-or-later',
                 'status': 'declared',
                 'notes': 'Library header; remaining library inventory is unresolved. Actual '
                          'packaged-output inclusion and complete component review are '
                          'pending.'}],
 'patches': [],
 'notes': ['No source patch; exact release archive and notices inspected 2026-10-07.',
           '2026-10-15 private Work targeted archive/notice review: 4 observations, 2 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Replace the unrelated libxcrypt/PCRE2 wording in the '
           'unresolved component note with an attr-specific inventory.',
           'Open per-file/component review: Map library, utility, generated build helpers and '
           'documentation separately.']}

# Data only; parsed with ast.literal_eval.
{'schema': 1,
 'package': 'libffi',
 'version': '3.8.0',
 'source': {'url': 'https://github.com/libffi/libffi/releases/download/v3.8.0/libffi-3.8.0.tar.gz',
            'sha256': '7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4'},
 'status': 'declared',
 'expression': 'MIT',
 'scope': 'Top-level upstream declaration only; explicitly separate components and unresolved '
          'source scopes below.',
 'evidence': [{'path': 'libffi-3.8.0/LICENSE',
               'sha256': '17b64dc60f3b6897a60f971e288b973f655c2edcdf08b25f3c3dd5549857881c',
               'source_sha256': '7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4'},
              {'path': 'libffi-3.8.0/msvcc.sh',
               'sha256': 'c7f4c452edbb40a8ee264b5ffe8a9563cf7e215c2217fc8a297f376c00a6a4c1',
               'source_sha256': '7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4'},
              {'path': 'libffi-3.8.0/LICENSE-BUILDTOOLS',
               'sha256': 'e67978cd18816c0cb7d29aaaacde7b7447402c2fb321a051698890a8eaedda94',
               'source_sha256': '7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4'},
              {'path': 'libffi-3.8.0/make_sunver.pl',
               'sha256': 'ca40d3458893e03a90807be87d720a59e921ee6bf678c6696779d635004a261f',
               'source_sha256': '7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4'}],
 'components': [{'scope': 'Bundled components, generated files and documentation',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Full per-component release review required.'},
                {'scope': 'msvcc.sh compiler wrapper',
                 'expression': 'MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later',
                 'status': 'unresolved',
                 'notes': 'Canonical file declaration: MPL-1.1 OR GPL-2.0-or-later OR '
                          'LGPL-2.1-or-later. Frozen parser cannot represent this identifier; '
                          'preserve it here without narrowing alternatives or inventing '
                          'LicenseRef. Explicit file alternatives; preserve full header. Rerun '
                          '2026-10-16: a4e3870 adds this exact identifier; canonical expression '
                          'restored with review status unchanged.'},
                {'scope': 'testsuite/libffi.bhaible',
                 'expression': 'GPL-2.0-only',
                 'status': 'declared',
                 'notes': 'LICENSE-BUILDTOOLS explicitly assigns GPL version2 to this test '
                          'subtree.'},
                {'scope': 'make_sunver.pl tooling',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Named in LICENSE-BUILDTOOLS but specific grant not established; resolve '
                          'provenance.'}],
 'patches': [],
 'notes': ['Exact source and license evidence inspected 2026-10-03; no downstream patches applied.',
           '2026-10-16 private source-scope review; source identity and historical pins preserved. '
           'This record is not output redistribution approval.']}

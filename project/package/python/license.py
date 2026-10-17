# Data only; parsed with ast.literal_eval.
{'schema': 1,
 'package': 'python',
 'version': '3.14.7',
 'source': {'url': 'https://www.python.org/ftp/python/3.14.7/Python-3.14.7.tar.xz',
            'sha256': '3b48dac8fb59f62eaa67ac83c1eb12bda1b7a08406dd286e252c11a66be27f81'},
 'status': 'declared',
 'expression': 'Python-2.0',
 'scope': 'Primary upstream declaration or retained top-level terms only; see component scopes and '
          'unresolved review notes.',
 'evidence': [{'path': 'Python-3.14.7/LICENSE',
               'sha256': 'b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231',
               'source_sha256': '3b48dac8fb59f62eaa67ac83c1eb12bda1b7a08406dd286e252c11a66be27f81'},
              {'path': 'Python-3.15.0rc2/LICENSE',
               'sha256': 'b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231',
               'source_sha256': '8d93af5eaaaea5adfd41bd786a7ba3f03f2ad1ab57c6a65e0b963deab91d5ad7'}],
 'components': [{'scope': 'Other included files, documentation, generated code and bundled '
                          'subprojects',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Complete per-file/stage scope review remains required; primary '
                          'declaration is not a blanket grant.'},
                {'scope': 'Stage archive Python-3.15.0rc2.tar.xz',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Exact stage SHA256 '
                          '8d93af5eaaaea5adfd41bd786a7ba3f03f2ad1ab57c6a65e0b963deab91d5ad7; '
                          'top-level terms retained separately from primary metadata version. Full '
                          'per-file scopes and output notice delivery remain open.'}],
 'patches': [],
 'notes': ['Inspected exact release archive on 2026-09-27; source and evidence hashes are bound to '
           'this version.',
           'Declared is not release-reviewed. Per-component notices, exceptions and '
           'corresponding-source obligations require final review.',
           'LicenseRef denotes the retained upstream terms without claiming SPDX equivalence; it '
           'never denotes Zog first-party licensing.']}

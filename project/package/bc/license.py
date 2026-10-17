# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'bc',
 'version': '7.0.3',
 'source': {'url': 'https://github.com/gavinhoward/bc/releases/download/7.0.3/bc-7.0.3.tar.xz',
            'sha256': '91eb74caed0ee6655b669711a4f350c25579778694df248e28363318e03c7fc4'},
 'status': 'declared',
 'expression': 'BSD-2-Clause',
 'scope': 'Primary declaration; LICENSE.md also records component terms.',
 'evidence': [{'path': 'bc-7.0.3/LICENSE.md',
               'sha256': '375aa5547dd474d9068587d5feadcccd18467bf371e8f504c8c1d399073a1162',
               'source_sha256': '91eb74caed0ee6655b669711a4f350c25579778694df248e28363318e03c7fc4'},
              {'path': 'bc-7.0.3/NOTICE.md',
               'sha256': '3f7d9c313f74c49ee5409aad10e05bbc7790b3d10fcebccc733b18b1ce5433b7',
               'source_sha256': '91eb74caed0ee6655b669711a4f350c25579778694df248e28363318e03c7fc4'}],
 'components': [{'scope': 'Bundled history and other components',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Terms retained in LICENSE.md; complete component scope review '
                          'pending.'},
                {'scope': 'src/history.c; include/history.h',
                 'expression': 'BSD-2-Clause',
                 'status': 'declared',
                 'notes': 'LICENSE.md names separate history contributors; preserve their '
                          'attributions. Actual packaged-output inclusion and complete component '
                          'review are pending.'},
                {'scope': 'src/rand.c; include/rand.h',
                 'expression': 'MIT',
                 'status': 'declared',
                 'notes': 'LICENSE.md identifies PCG/Melissa O’Neill and Gavin Howard terms. '
                          'Actual packaged-output inclusion and complete component review are '
                          'pending.'},
                {'scope': 'scripts/safe-install.sh',
                 'expression': 'MIT',
                 'status': 'declared',
                 'notes': 'LICENSE.md identifies Rich Felker attribution. Actual packaged-output '
                          'inclusion and complete component review are pending.'},
                {'scope': 'scripts/ministat.c',
                 'expression': 'LicenseRef-bc-Beerware-42',
                 'status': 'declared',
                 'notes': 'LICENSE.md retains Poul-Henning Kamp Beerware revision 42; preserve '
                          'verbatim terms. Actual packaged-output inclusion and complete '
                          'component review are pending.'}],
 'patches': [],
 'notes': ['Exact release license inspected; not public-release reviewed.',
           '2026-10-15 private Work targeted archive/notice review: 2 observations, 1 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add component records for src/history.c, '
           'include/history.h, src/rand.c, include/rand.h, scripts/safe-install.sh and '
           'scripts/ministat.c.',
           'Open per-file/component review: Bind notices and inclusion decisions to actual '
           'packaged outputs; do not collapse the entire source archive to BSD-2-Clause.']}

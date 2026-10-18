# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'check',
 'version': '0.15.2',
 'source': {'url': 'https://github.com/libcheck/check/releases/download/0.15.2/check-0.15.2.tar.gz',
            'sha256': 'a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a'},
 'status': 'declared',
 'expression': 'LGPL-2.1-or-later',
 'scope': 'Listed exact-release notices only; LicenseRef identifiers denote the preserved '
          'upstream terms, not Zog terms.',
 'evidence': [{'path': 'check-0.15.2/COPYING.LESSER',
               'sha256': 'a9bdde5616ecdd1e980b44f360600ee8783b1f99b8cc83a2beb163a0a390e861',
               'source_sha256': 'a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a'},
              {'path': 'check-0.15.2/lib/strsignal.c',
               'sha256': 'f33b1e370355cfec57382f2691a024ac2bcbde9a162052509d00ddfe3a08ce8a',
               'source_sha256': 'a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a'},
              {'path': 'check-0.15.2/checkmk/checkmk.in',
               'sha256': '05f2c384a0dfeaf1ade50dbcb4973a7db80d4122cdb59d5c47ae064429b7a491',
               'source_sha256': 'a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a'},
              {'path': 'check-0.15.2/doc/example/cmake/COPYING-CMAKE-SCRIPTS.txt',
               'sha256': 'c666ec2313dba24523ccad88f4c04ea4b24fad6545263a35b1d4ab2b08efe50a',
               'source_sha256': 'a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a'},
              {'path': 'check-0.15.2/doc/check.texi',
               'sha256': '32951090e91750bc3563609c3933bfb4270868157803baf7e385d16569733a3f',
               'source_sha256': 'a8de4e0bacfb4d76dd1c618ded263523b53b85d92a146d8835eb1a52932fa20a'}],
 'components': [{'scope': 'Other source files, generated build support, documentation and '
                          'bundled components',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Per-file public-distribution review remains required; preserve '
                          'corresponding source and all notices.'},
                {'scope': 'lib/strsignal.c',
                 'expression': 'LGPL-2.1-or-later',
                 'status': 'declared',
                 'notes': 'Exact header declaration. Actual packaged-output inclusion and '
                          'complete component review are pending.'},
                {'scope': 'checkmk/checkmk.in',
                 'expression': 'LicenseRef-check-checkmk',
                 'status': 'declared',
                 'notes': 'Micah Cowan permissive source-attribution notice; retain custom text. '
                          'Actual packaged-output inclusion and complete component review are '
                          'pending.'},
                {'scope': 'doc/example/cmake scripts covered by COPYING-CMAKE-SCRIPTS.txt',
                 'expression': 'LicenseRef-check-CMakeScripts',
                 'status': 'declared',
                 'notes': 'Separate three-condition BSD-style notice; exact membership and '
                          'output inclusion remain open. Actual packaged-output inclusion and '
                          'complete component review are pending.'},
                {'scope': 'doc/check.texi',
                 'expression': 'GFDL-1.2-or-later',
                 'status': 'declared',
                 'notes': 'No invariant sections or cover texts declared. Actual packaged-output '
                          'inclusion and complete component review are pending.'}],
 'patches': [],
 'notes': ['Exact source and notice hashes inspected 2026-10-10. No upstream patches. No '
           'public-release clearance.',
           '2026-10-15 private Work targeted archive/notice review: 5 observations, 4 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add exact component/evidence records for checkmk, '
           'CMake example scripts and GFDL-1.2-or-later manual.',
           'Open per-file/component review: Finish generated helper and example output inclusion '
           'review.']}

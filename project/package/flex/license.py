# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'flex',
 'version': '2.6.4',
 'source': {'url': 'https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz',
            'sha256': 'e87aae032bf07c26f85ac0ed3250998c37621d95f8bd748b31f15b33c45ee995'},
 'status': 'declared',
 'expression': 'LicenseRef-flex-upstream-terms',
 'scope': 'Primary upstream declaration or retained top-level terms only; see component scopes '
          'and unresolved review notes.',
 'evidence': [{'path': 'flex-2.6.4/COPYING',
               'sha256': '97fd685958d93be7f8dab939bb8161dbd6afb0718c63bfc337c24321aea44273',
               'source_sha256': 'e87aae032bf07c26f85ac0ed3250998c37621d95f8bd748b31f15b33c45ee995'},
              {'path': 'flex-2.6.4/README.md',
               'sha256': '9269b1fe4e79b8504bf9be7d9319ff794f50c6677ee8477a770212ce93134379',
               'source_sha256': 'e87aae032bf07c26f85ac0ed3250998c37621d95f8bd748b31f15b33c45ee995'}],
 'components': [{'scope': 'Other included files, documentation, generated code and bundled '
                          'subprojects',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Complete per-file/stage scope review remains required; primary '
                          'declaration is not a blanket grant.'},
                {'scope': 'generator and flex.skl distinction in COPYING',
                 'expression': 'LicenseRef-flex',
                 'status': 'declared',
                 'notes': 'Retain Flex Project/UC Regents notices and DOE contract rights. '
                          'COPYING distinguishes generated scanners from generator licensing; '
                          'this does not establish rights for arbitrary input grammars or other '
                          'bundled components. Actual packaged-output inclusion and complete '
                          'component review are pending.'}],
 'patches': [],
 'notes': ['Inspected exact release archive on 2026-09-27; source and evidence hashes are bound '
           'to this version.',
           'Declared is not release-reviewed. Per-component notices, exceptions and '
           'corresponding-source obligations require final review.',
           'LicenseRef denotes the retained upstream terms without claiming SPDX equivalence; it '
           'never denotes Zog first-party licensing.',
           'Retained text contains wording variations; SPDX equivalence is deliberately '
           'unresolved rather than inferred from a license family.',
           '2026-10-15 private Work targeted archive/notice review: 1 observations, 0 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Retain the complete custom notice and accurately '
           'scope the generated-scanner statement.',
           'Open per-file/component review: Finish documentation, generated helpers and '
           'skeleton/output inclusion inventory.']}

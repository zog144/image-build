# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'file',
 'version': '5.48',
 'source': {'url': 'https://astron.com/pub/file/file-5.48.tar.gz',
            'sha256': 'ed14656883b23a364b4057c05595d93252da9bc473d30106519519d0da141283'},
 'status': 'declared',
 'expression': 'LicenseRef-file-upstream-terms',
 'scope': 'Primary upstream declaration or retained top-level terms only; see component scopes '
          'and unresolved review notes.',
 'evidence': [{'path': 'file-5.48/COPYING',
               'sha256': '0bfa856a9930bddadbef95d1be1cf4e163c0be618e76ea3275caaf255283e274',
               'source_sha256': 'ed14656883b23a364b4057c05595d93252da9bc473d30106519519d0da141283'},
              {'path': 'file-5.48/python/LICENSE',
               'sha256': '9d402e401ecfd65d9c600cf84ecb317aba1c5c6fcb788dd79af94fd1fdc527a8',
               'source_sha256': 'ed14656883b23a364b4057c05595d93252da9bc473d30106519519d0da141283'}],
 'components': [{'scope': 'Other included files, documentation, generated code and bundled '
                          'subprojects',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Complete per-file/stage scope review remains required; primary '
                          'declaration is not a blanket grant.'},
                {'scope': 'python binding covered by python/LICENSE',
                 'expression': 'LicenseRef-file-python',
                 'status': 'declared',
                 'notes': 'Preserve separate copyright and exact custom permission text, '
                          'including placement requirements. Magic database per-file authorship '
                          'remains unresolved. Actual packaged-output inclusion and complete '
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
           '2026-10-15 private Work targeted archive/notice review: 2 observations, 1 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add Python binding evidence and map binding scope.',
           'Open per-file/component review: Review per-file magic database authorship and '
           'bundled sources; do not replace custom terms with approximate SPDX equivalence.']}

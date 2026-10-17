# Private, source-bound evidence candidate; no release approval.
{'schema': 1,
 'package': 'dbus',
 'version': '1.16.2',
 'source': {'url': 'https://dbus.freedesktop.org/releases/dbus/dbus-1.16.2.tar.xz',
            'sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
 'status': 'declared',
 'expression': 'LicenseRef-dbus-upstream-terms',
 'scope': 'Exact release notices; component exceptions require per-file review before public '
          'redistribution.',
 'evidence': [{'path': 'dbus-1.16.2/COPYING',
               'sha256': '150e5d08e1cb5e62b65967d7931acad2c42d98ec1bbb584bebb01921cbc853c2',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/LICENSES/AFL-2.1.txt',
               'sha256': '93bb4f7417aa775bab9026cc3d0af28aeb64451fc5a8ec651876785edd8eaf9b',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/LICENSES/GPL-2.0-or-later.txt',
               'sha256': 'aaf135472f81c5b4a0dca9367e5bb5e9750032b5bebe5442b36e4c0a47430df3',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/LICENSES/MIT.txt',
               'sha256': 'b85dcd3e453d05982552c52b5fc9e0bdd6d23c6f8e844b984a88af32570b0cc0',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/tools/dbus-cleanup-sockets.c',
               'sha256': 'c5f7551dd897e715b0a17fdff7b84a29dc740db14a82dea20cf5ff8dd9c745ef',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/LICENSES/LicenseRef-CMakeScripts.txt',
               'sha256': 'a4c1387064fda4c22bfca364b606eb4e0421efa37cad27c040a3d7ca7186d522',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/LICENSES/LicenseRef-GAP.txt',
               'sha256': 'cf4bc4c56dd0837f3d53b8c1467e0d7dbb95223de8bcfe83a4981c318a738ae3',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'},
              {'path': 'dbus-1.16.2/LICENSES/LicenseRef-pycrypto-orig.txt',
               'sha256': '2cb8f4f410f0ffc5dcfbadd188e20c859fdbb161e616cf2f3d34dfbf8c740547',
               'source_sha256': '0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2'}],
 'components': [{'scope': 'Other source, documentation and bundled components',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'Top-level terms are not a blanket grant; retain all upstream source '
                          'notices.'},
                {'scope': 'tools/dbus-cleanup-sockets.c',
                 'expression': 'GPL-2.0-or-later',
                 'status': 'declared',
                 'notes': 'Explicitly not under AFL; other tools and test helpers require '
                          'separate scope review. Actual packaged-output inclusion and complete '
                          'component review are pending.'},
                {'scope': 'cmake/modules/FindGLIB2.cmake',
                 'expression': 'LicenseRef-CMakeScripts',
                 'status': 'declared',
                 'notes': 'Per-file SPDX mapping to LICENSES/LicenseRef-CMakeScripts.txt. Actual '
                          'packaged-output inclusion and complete component review are pending.'},
                {'scope': 'dbus/versioninfo.rc.in',
                 'expression': 'LicenseRef-GAP',
                 'status': 'declared',
                 'notes': 'Per-file SPDX mapping to LICENSES/LicenseRef-GAP.txt. Actual '
                          'packaged-output inclusion and complete component review are pending.'},
                {'scope': 'dbus/dbus-sha.c',
                 'expression': None,
                 'status': 'unresolved',
                 'notes': 'SPDX declares (AFL-2.1 OR GPL-2.0-or-later) AND '
                          'LicenseRef-pycrypto-orig. Preserve this full compound declaration; '
                          'the current validator does not support AFL-2.1. Mapping only the '
                          'custom conjunct would be incomplete. Actual packaged-output inclusion '
                          'and complete component review are pending.'}],
 'patches': [],
 'notes': ['Exact release and listed notices inspected 2026-10-09. No upstream source patches. '
           'No public-release audit claimed.',
           '2026-10-15 private Work targeted archive/notice review: 5 observations, 4 newly '
           'retained source-bound evidence paths. Exact source SHA256 and recorded notice bytes '
           'were verified; complete component-scope review and redistribution NOT approved.',
           'Open per-file/component review: Add the three omitted LicenseRef texts as evidence '
           'and bind each to the actual per-file SPDX scope.',
           'Open per-file/component review: Map GPL-only tools and test helpers separately from '
           'the dual-licensed main code.']}

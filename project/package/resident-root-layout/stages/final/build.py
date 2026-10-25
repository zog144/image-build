# Data only; parsed with ast.literal_eval.
{'build': [['/bin/bash',
            '-eu',
            '-o',
            'pipefail',
            '-c',
            "grep -Fx '/state 0000 root:root' inputs/layout-v1.txt\n"
            "grep -Fx '/applications 0000 root:root' inputs/layout-v1.txt"]],
 'test': [['/bin/bash',
           '-eu',
           '-o',
           'pipefail',
           '-c',
           "test \"$(sha256sum inputs/layout-v1.txt | cut -d' ' -f1)\" = "
           "'623e1054fbcc5738fc8ee2f557cb76b410b2b455a66ccb1e8cdf2aa84d51ebe9'"]],
 'install': [['/bin/bash',
              '-eu',
              '-o',
              'pipefail',
              '-c',
              'install -d -m 0000 "$DESTDIR/state" "$DESTDIR/applications"']]}

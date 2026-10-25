# Data only; read with ast.literal_eval, never import.
{'schema': 1,
 'status': 'resident-b-deferred',
 'stages': ['future-resident-b'],
 'build_dependencies': None,
 'runtime_dependencies': None,
 'test_dependencies': None,
 'prepare': None,
 'configure': None,
 'build': None,
 'test': None,
 'install': None,
 'outputs': None,
 'reference': 'https://www.linuxfromscratch.org/lfs/view/13.1-systemd/appendices/dependencies.html',
 'notes': 'Not a Boot A login provider. The additive util-linux login stage owns /usr/bin/login. '
          'Shadow remains catalogue-only and must receive an exact Resident B account-policy scope, '
          'reviewed source recipe and output manifest before execution.'}

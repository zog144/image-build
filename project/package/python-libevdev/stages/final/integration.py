# Data only; parsed with ast.literal_eval.
{'project': 'python-libevdev',
 'stage_id': 'final',
 'base_contract': 'Accepted CPython 3.15 runtime. Native libevdev is an explicit runtime dependency.',
 'python_distribution': 'libevdev',
 'version': '0.13.1',
 'build_system': {'requires': ['hatchling'], 'build-backend': 'hatchling.build'},
 'zog_install_policy': 'Direct pure-Python package-directory install: upstream wheel configuration names only the libevdev package and defines no generated payload. This avoids adding hatchling as an execution dependency solely for xorgproto test support.',
 'runtime_requirements': ['libevdev shared library', "typing_extensions>=4.0 only for Python < 3.11"],
 'test_scope': 'Device-independent import and event-code constants required by xorgproto. Upstream pytest suite was reviewed and contains root-only /dev/input and uinput tests; those are not silently treated as passed.',
 'external_test_prerequisite': 'Full upstream device tests require real input/uinput device access and root in several cases; they require separate explicit host authorization.',
 'patches': [],
 'patches_complete': True}

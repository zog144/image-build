# Data only; parsed with ast.literal_eval.
{'project': 'libevdev',
 'stage_id': 'final',
 'base_contract': 'Accepted refreshed self-hosted graphics base supplies GCC, Python, pkgconf and Meson/Ninja; Check is an explicit batch dependency.',
 'version': '1.14.0',
 'features': {'tools': False, 'documentation': False, 'coverity': False, 'tests': True},
 'test_scope': 'Upstream Meson tests are built, but the suite tagged needs-uinput is excluded because it opens /dev/uinput and creates kernel input devices. Zog grants no extra device/root privilege for package tests. Any remaining non-device upstream tests must pass.',
 'external_test_prerequisite': 'Full needs-uinput coverage requires a separately authorized host/device test with /dev/uinput and must not be represented as completed by this recipe.',
 'patches': [],
 'patches_complete': True}

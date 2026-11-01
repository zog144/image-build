# Data only; parsed with ast.literal_eval.
{
  "environment": {
    "PIP_NO_INDEX": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTHONPATH": ""
  },
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"; python3 tools/verify_mesa_toolchain.py --attestation \"$ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION\"\ncd upstream/mako-1.4.3\npython3 - <<'PYBUILD'\nimport pathlib,tomllib,importlib\nfrom importlib.metadata import version\np=tomllib.loads(pathlib.Path('pyproject.toml').read_text())\nassert p['build-system']=={'requires':['setuptools>=77.0.0'],'build-backend':'setuptools.build_meta'}\nassert p['project']['dependencies']==['MarkupSafe >= 2.0']\nassert int(version('setuptools').split('.')[0])>=77\nassert int(version('MarkupSafe').split('.')[0])>=2\nbackend=importlib.import_module('setuptools.build_meta')\nassert backend.get_requires_for_build_wheel({})==[]\npathlib.Path('dist').mkdir(exist_ok=True)\nprint(backend.build_wheel(str(pathlib.Path('dist').resolve()),{}))\nPYBUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test \"$(find upstream/mako-1.4.3/dist -name '*.whl' | wc -l)\" -eq 1"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; cd upstream/mako-1.4.3; python3 -m installer --destdir=\"$DESTDIR\" dist/*.whl; install -Dm644 LICENSE \"$DESTDIR/usr/share/licenses/mako/LICENSE\""
    ]
  ]
}

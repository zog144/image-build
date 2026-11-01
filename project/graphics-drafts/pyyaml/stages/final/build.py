# Data only; parsed with ast.literal_eval.
{
  "environment": {
    "PIP_NO_INDEX": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTHONPATH": "",
    "PYYAML_FORCE_LIBYAML": "0",
    "PYYAML_FORCE_CYTHON": "0"
  },
  "prepare": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/pyyaml-6.0.3\npython3 - <<'PYTRANSFORM'\nimport pathlib,tomllib,json,hashlib\np=pathlib.Path('pyproject.toml'); raw=p.read_text(); orig=tomllib.loads(raw)\nassert orig['build-system']=={'requires':['setuptools',\"Cython; python_version < '3.13'\",\"Cython>=3.0; python_version >= '3.13'\"],'backend-path':['packaging'],'build-backend':'_pyyaml_pep517'}\na=raw.index('requires = ['); b=raw.index(']',a)+1\nrevised=raw[:a]+\"requires = ['setuptools']\"+raw[b:]\nassert tomllib.loads(revised)['build-system']=={'requires':['setuptools'],'backend-path':['packaging'],'build-backend':'_pyyaml_pep517'}\np.write_text(revised)\npathlib.Path('zog-pure-python-transform.json').write_text(json.dumps({'original_sha256':hashlib.sha256(raw.encode()).hexdigest(),'revised_sha256':hashlib.sha256(revised.encode()).hexdigest(),'feature':'pure-python-only'},sort_keys=True)+'\\n')\nPYTRANSFORM"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION:-}\"; python3 tools/verify_mesa_toolchain.py --attestation \"$ZOG_GRAPHICS_TOOLCHAIN_ATTESTATION\" --phase pyyaml\ncd upstream/pyyaml-6.0.3\npython3 - <<'PYBUILD'\nimport pathlib,tomllib,importlib,sys,os\np=tomllib.loads(pathlib.Path('pyproject.toml').read_text())['build-system']\nassert p=={'requires':['setuptools'],'backend-path':['packaging'],'build-backend':'_pyyaml_pep517'}\nassert os.environ['PYYAML_FORCE_LIBYAML']=='0' and os.environ['PYYAML_FORCE_CYTHON']=='0'\nsys.path.insert(0,str(pathlib.Path('packaging').resolve()))\nbackend=importlib.import_module('_pyyaml_pep517')\nfrom packaging.requirements import Requirement\nfrom importlib.metadata import version\nfor text in backend.get_requires_for_build_wheel({}):\n req=Requirement(text)\n assert req.name.lower().replace('_','-') in ('wheel','setuptools','packaging'),text\n assert req.specifier.contains(version(req.name),prereleases=True),text\npathlib.Path('dist').mkdir(exist_ok=True)\nprint(backend.build_wheel(str(pathlib.Path('dist').resolve()),{}))\nPYBUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test \"$(find upstream/pyyaml-6.0.3/dist -name \"*none-any.whl\" | wc -l)\" -eq 1"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; cd upstream/pyyaml-6.0.3; python3 -m installer --destdir=\"$DESTDIR\" dist/*.whl; install -Dm644 LICENSE \"$DESTDIR/usr/share/licenses/pyyaml/LICENSE\""
    ]
  ]
}

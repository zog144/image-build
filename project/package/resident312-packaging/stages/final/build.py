# Held Resident B CPython 3.12 source stage; original-source metadata checked, native build not executed.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/packaging-26.3\ntest -x /usr/bin/python3.12\n/usr/bin/python3.12 -I - <<'ZOG_SELECTED_SOURCE'\nimport importlib.metadata,importlib.util,os,pathlib,sys,tomllib\nassert sys.version_info[:3]==(3,12,16) and sys.flags.isolated\nassert sys.executable=='/usr/bin/python3.12'\nassert not os.environ.get('PYTHONPATH') and not os.environ.get('PYTHONHOME')\nassert not any(p.startswith(('/usr/local/','/home/','/opt/host/')) for p in sys.path)\nroot=pathlib.Path.cwd(); p=tomllib.loads((root/'pyproject.toml').read_text())\nassert p['project']['name'].replace('_','-').lower()=='packaging'\nfrom email.parser import BytesParser\ninfo=BytesParser().parsebytes((root/'PKG-INFO').read_bytes())\nassert info['Version']=='26.3'\nassert info['Name'].replace('_','-').lower()==p['project']['name'].replace('_','-').lower()\nrequired=[{\"dist\":\"flit_core\",\"version\":\"3.12.0\",\"module\":\"flit_core\"},{\"dist\":\"installer\",\"version\":\"1.0.1\",\"module\":\"installer\"}]\nfor x in required:\n assert importlib.metadata.version(x['dist'])==x['version'], ('wrong selected tool',x)\n spec=importlib.util.find_spec(x['module'])\n assert spec and spec.origin and spec.origin.startswith('/usr/lib/python3.12/site-packages/'), ('Host module fallback',x)\nprint('ZOG_RESIDENT312_SELECTED_TOOLS_CONSISTENT')\nZOG_SELECTED_SOURCE"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/packaging-26.3\n/usr/bin/python3.12 -I - <<'ZOG_PINNED_WHEEL_BUILD'\nimport importlib,importlib.util,pathlib,sys,tomllib\nroot=pathlib.Path.cwd(); info=tomllib.loads((root/'pyproject.toml').read_text())\nfor x in info['build-system'].get('backend-path',[]):\n loc=(root/x).resolve()\n assert loc.is_relative_to(root)\n sys.path.insert(0,str(loc))\nbackend=importlib.import_module(info['build-system']['build-backend'])\nassert backend.__name__=='flit_core.buildapi'\nif info['build-system']['build-backend'].startswith('flit_core') and 'packaging'=='flit-core':\n assert pathlib.Path(backend.__file__).resolve().is_relative_to(root)\nextra=getattr(backend,'get_requires_for_build_wheel',lambda *args: [])({})\nassert not extra,('unreviewed dynamic build requirements',extra)\n(root/'dist').mkdir(exist_ok=True)\nout=backend.build_wheel(str((root/'dist').resolve()),{})\nassert out.endswith('.whl') and len(list((root/'dist').glob('*.whl')))==1\nZOG_PINNED_WHEEL_BUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/packaging-26.3\n/usr/bin/python3.12 -I - <<'ZOG_WHEEL_VERIFY'\nimport email,pathlib,zipfile\nwheels=list(pathlib.Path('dist').glob('*.whl'))\nassert len(wheels)==1\nwith zipfile.ZipFile(wheels[0]) as f:\n assert f.testzip() is None\n names=f.namelist()\n assert names and all(not p.startswith('/') and '..' not in pathlib.PurePosixPath(p).parts for p in names)\n metadata=[n for n in names if n.endswith('.dist-info/METADATA')]\n record=[n for n in names if n.endswith('.dist-info/RECORD')]\n assert len(metadata)==len(record)==1\n m=email.message_from_bytes(f.read(metadata[0]))\n assert m['Name'].lower().replace('_','-')=='packaging' and m['Version']=='26.3'\n assert 'packaging/__init__.py' in names\n print('ZOG_RESIDENT312_EXACT_WHEEL_METADATA',m['Name'],m['Version'])\nZOG_WHEEL_VERIFY"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ntest -n \"${DESTDIR:-}\"\ncd upstream/packaging-26.3\n/usr/bin/python3.12 -I -m installer --destdir=\"$DESTDIR\" dist/*.whl\ntest -s \"$DESTDIR/usr/lib/python3.12/site-packages/packaging-26.3.dist-info/METADATA\"\ntest -s \"$DESTDIR/usr/lib/python3.12/site-packages/packaging-26.3.dist-info/RECORD\"\ntest -s \"$DESTDIR/usr/lib/python3.12/site-packages/packaging/__init__.py\"\n"
    ]
  ],
  "environment": {
    "PATH": "/usr/bin:/bin",
    "PYTHONNOUSERSITE": "1",
    "PYTHONSAFEPATH": "1",
    "PIP_NO_INDEX": "1",
    "PKG_CONFIG_LIBDIR": "/usr/lib/pkgconfig:/usr/share/pkgconfig",
    "PKG_CONFIG_SYSROOT_DIR": "/"
  }
}

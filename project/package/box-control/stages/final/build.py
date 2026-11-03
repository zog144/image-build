# Immutable source only; compile/install requires independently accepted runtime/build toolchain.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/zog144-box-control-b513a9b/box-control\npython3.12 -I - <<'ZOG_CONTROLLER_PIN'\nimport hashlib,pathlib,sys,tomllib\nfrom importlib.metadata import version\np=pathlib.Path(\".\")\nassert sys.version_info[:2]==(3,12)\ndef digest(name): return hashlib.sha256((p/name).read_bytes()).hexdigest()\nassert p.name==\"box-control\"\nassert digest(\"pyproject.toml\")==\"a099487955e9b42e90aed4103cb32e76f7dae0535692534c25b7be2f09a4eb47\"\nassert digest(\"LICENSE\")==\"aaf3d5919ea7f2720b7649d4f1e4fd28a54c58425a45dfd736d040a56480578f\"\nassert digest(\"THIRD-PARTY-NOTICES.md\")==\"b6636714adafd8c7c8e9ab1db2d07e3c7efe3b312fa10268bc393b83e1db7036\"\nmeta=tomllib.loads((p/\"pyproject.toml\").read_text())\nassert meta[\"project\"][\"name\"]==\"box-control\"\nassert meta[\"project\"][\"version\"]==\"0.1.0\"\nassert meta[\"project\"][\"scripts\"][\"box-control\"]==\"zog.box_control.cli:main\"\nassert version(\"setuptools\")>=\"80\"\nfor name in (\"packaging\",\"installer\",\"wheel\"): assert version(name)\nprint(\"ZOG_CONTROLLER_ORIGINAL_SOURCE_CHECK_PASS\")\nZOG_CONTROLLER_PIN"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/zog144-box-control-b513a9b/box-control\npython3.12 -I - <<'ZOG_CONTROLLER_BUILD'\nimport pathlib,setuptools.build_meta as backend\npathlib.Path(\"dist\").mkdir(exist_ok=True)\nout=backend.build_wheel(str(pathlib.Path(\"dist\").resolve()),{})\nassert out.endswith(\".whl\")\nassert len(list(pathlib.Path(\"dist\").glob(\"*.whl\")))==1\nZOG_CONTROLLER_BUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/zog144-box-control-b513a9b/box-control\npython3.12 -I - <<'ZOG_CONTROLLER_TEST'\nimport email,pathlib,zipfile\nfiles=list(pathlib.Path(\"dist\").glob(\"*.whl\"))\nassert len(files)==1\nwith zipfile.ZipFile(files[0]) as archive:\n assert archive.testzip() is None\n names=archive.namelist()\n assert \"zog/box_control/__init__.py\" in names\n assert any(x.endswith(\".dist-info/entry_points.txt\") for x in names)\n entry=next(x for x in names if x.endswith(\".dist-info/entry_points.txt\"))\n assert \"box-control\" in archive.read(entry).decode()\n assert any(x.startswith('zog/box_control/') for x in names)\nprint(\"ZOG_CONTROLLER_WHEEL_SOURCE_TEST_PASS\")\nZOG_CONTROLLER_TEST"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ntest -n \"${DESTDIR:-}\"\ncd upstream/zog144-box-control-b513a9b/box-control\npython3.12 -I -m installer --destdir=\"$DESTDIR\" dist/*.whl\ntest -x \"$DESTDIR/usr/bin/box-control\"\ntest -s \"$DESTDIR/usr/lib/python3.12/site-packages/zog/box_control/__init__.py\"\ninstall -Dm644 LICENSE \"$DESTDIR/usr/share/licenses/box-control/LICENSE\"\ninstall -Dm644 THIRD-PARTY-NOTICES.md \"$DESTDIR/usr/share/licenses/box-control/THIRD-PARTY-NOTICES.md\"\n"
    ]
  ],
  "environment": {
    "PYTHONNOUSERSITE": "1",
    "PYTHONSAFEPATH": "1",
    "PIP_NO_INDEX": "1",
    "PKG_CONFIG_LIBDIR": "/usr/lib/pkgconfig:/usr/share/pkgconfig"
  }
}

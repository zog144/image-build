# Immutable source only; compile/install requires independently accepted runtime/build toolchain.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/zog144-root-control-0c21718\npython3.12 -I - <<'ZOG_CONTROLLER_PIN'\nimport hashlib,pathlib,sys,tomllib\nfrom importlib.metadata import version\np=pathlib.Path(\".\")\nassert sys.version_info[:2]==(3,12)\ndef digest(name): return hashlib.sha256((p/name).read_bytes()).hexdigest()\nassert p.name==\"zog144-root-control-0c21718\"\nassert digest(\"pyproject.toml\")==\"f42d1b9458536b4b20aef183d438267b0790bb8fc9238afcc10b9a1bc62b1c96\"\nassert digest(\"LICENSE\")==\"421a457ded4d2bf4b853c5ce211f74797292b2ef2f82bc7245304956fb7cf68f\"\nassert digest(\"THIRD-PARTY-NOTICES.md\")==\"b3aa6c652c70db0faecdd42d35723c62bc61282dc53d73f637f26e\"\nmeta=tomllib.loads((p/\"pyproject.toml\").read_text())\nassert meta[\"project\"][\"name\"]==\"root-control\"\nassert meta[\"project\"][\"version\"]==\"0.1.0\"\nassert meta[\"project\"][\"scripts\"][\"root-control\"]==\"zog.root_control.daemon:main\"\nassert version(\"setuptools\")>=\"80\"\nfor name in (\"packaging\",\"installer\",\"wheel\"): assert version(name)\nprint(\"ZOG_CONTROLLER_ORIGINAL_SOURCE_CHECK_PASS\")\nZOG_CONTROLLER_PIN"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/zog144-root-control-0c21718\npython3.12 -I - <<'ZOG_CONTROLLER_BUILD'\nimport pathlib,setuptools.build_meta as backend\npathlib.Path(\"dist\").mkdir(exist_ok=True)\nout=backend.build_wheel(str(pathlib.Path(\"dist\").resolve()),{})\nassert out.endswith(\".whl\")\nassert len(list(pathlib.Path(\"dist\").glob(\"*.whl\")))==1\nZOG_CONTROLLER_BUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ncd upstream/zog144-root-control-0c21718\npython3.12 -I - <<'ZOG_CONTROLLER_TEST'\nimport email,pathlib,zipfile\nfiles=list(pathlib.Path(\"dist\").glob(\"*.whl\"))\nassert len(files)==1\nwith zipfile.ZipFile(files[0]) as archive:\n assert archive.testzip() is None\n names=archive.namelist()\n assert \"zog/root_control/__init__.py\" in names\n assert any(x.endswith(\".dist-info/entry_points.txt\") for x in names)\n entry=next(x for x in names if x.endswith(\".dist-info/entry_points.txt\"))\n assert \"root-control\" in archive.read(entry).decode()\n assert \"zog/root_control/native/journal-wait.c\" in names\nprint(\"ZOG_CONTROLLER_WHEEL_SOURCE_TEST_PASS\")\nZOG_CONTROLLER_TEST"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "set -eu\ntest -n \"${DESTDIR:-}\"\ncd upstream/zog144-root-control-0c21718\npython3.12 -I -m installer --destdir=\"$DESTDIR\" dist/*.whl\ntest -x \"$DESTDIR/usr/bin/root-control\"\ntest -s \"$DESTDIR/usr/lib/python3.12/site-packages/zog/root_control/__init__.py\"\ninstall -Dm644 LICENSE \"$DESTDIR/usr/share/licenses/root-control/LICENSE\"\ninstall -Dm644 THIRD-PARTY-NOTICES.md \"$DESTDIR/usr/share/licenses/root-control/THIRD-PARTY-NOTICES.md\"\ntest -s \"$DESTDIR/usr/lib/python3.12/site-packages/zog/root_control/native/journal-wait.c\"\ninstall -d -m 0755 \"$DESTDIR/usr/lib/systemd/system\"\ncat > \"$DESTDIR/usr/lib/systemd/system/zog-root-control.service\" <<'ZOG_ROOT_CONTROL_UNIT'\n[Unit]\nDescription=Zog root-control privileged daemon (separately authorized)\nAfter=systemd-journald.socket\nRequiresMountsFor=/state\nConditionPathIsMountPoint=/state\n\n[Service]\nType=exec\nUser=root\nGroup=root\nWorkingDirectory=/\nExecStart=/usr/bin/root-control\nRuntimeDirectory=zog\nRuntimeDirectoryMode=0755\nUMask=0007\nRestart=no\nEnvironment=ROOT_CONTROL_JOURNAL_BARRIER=0\n\n# Deliberately no [Install] section: source publication does not enable privilege.\nZOG_ROOT_CONTROL_UNIT\n"
    ]
  ],
  "environment": {
    "PYTHONNOUSERSITE": "1",
    "PYTHONSAFEPATH": "1",
    "PIP_NO_INDEX": "1",
    "PKG_CONFIG_LIBDIR": "/usr/lib/pkgconfig:/usr/share/pkgconfig"
  }
}

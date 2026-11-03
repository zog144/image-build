# Source candidate data; evaluated with ast.literal_eval. Not native approval.
{
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/zog144-root-control-0c21718\npython3.12 - <<'ZOG_BUILD'\nimport importlib,importlib.metadata,pathlib,sys,sysconfig,tomllib\nassert sys.version_info[:2]==(3,12)\nassert sysconfig.get_config_var(\"SOABI\")==\"cpython-312-x86_64-linux-gnu\"\ndata=tomllib.loads(pathlib.Path(\"pyproject.toml\").read_text())\nassert data[\"project\"][\"name\"]==\"root-control\"\nassert data[\"project\"][\"version\"]==\"0.1.0\"\nassert data[\"project\"][\"scripts\"][\"root-control\"]==\"zog.root_control.daemon:main\"\nassert data[\"project\"][\"dependencies\"]==[\"box-control==0.1.0\",\"image-build==0.2.0.dev5\",\"dbus-next==0.2.3\"]\nassert data[\"build-system\"][\"build-backend\"]==\"setuptools.build_meta\"\nfrom packaging.requirements import Requirement\nfrom importlib.metadata import version\nfor text in data[\"build-system\"][\"requires\"]:\n req=Requirement(text)\n assert version(req.name) in req.specifier,(\"missing selected build prerequisite\",text)\nbackend=importlib.import_module(\"setuptools.build_meta\")\npathlib.Path(\"dist\").mkdir(exist_ok=True)\nprint(\"ZOG_SOURCE_WHEEL\",backend.build_wheel(\"dist\",{}),flush=True)\nZOG_BUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/zog144-root-control-0c21718\npython3.12 - <<'ZOG_TEST'\nimport email,pathlib,sys,sysconfig,zipfile\nassert sys.version_info[:2]==(3,12)\nassert sysconfig.get_config_var(\"SOABI\")==\"cpython-312-x86_64-linux-gnu\"\nwheels=list(pathlib.Path(\"dist\").glob(\"*.whl\"))\nassert len(wheels)==1\nwith zipfile.ZipFile(wheels[0]) as wheel:\n assert wheel.testzip() is None\n members=wheel.namelist()\n assert all(not name.startswith(\"/\") and \"..\" not in pathlib.PurePosixPath(name).parts for name in members)\n prefix=\"root_control-0.1.0.dist-info/\"\n meta=email.message_from_bytes(wheel.read(prefix+\"METADATA\"))\n assert meta[\"Name\"].replace(\"_\",\"-\").lower()==\"root-control\"\n assert meta[\"Version\"]==\"0.1.0\"\n for dep in [\"box-control==0.1.0\",\"image-build==0.2.0.dev5\",\"dbus-next==0.2.3\"]:\n  assert dep in (meta.get_all(\"Requires-Dist\") or []),(dep,meta.get_all(\"Requires-Dist\"))\n assert \"root-control = zog.root_control.daemon:main\" in wheel.read(prefix+\"entry_points.txt\").decode()\n assert \"zog/root_control/__init__.py\" in members\n assert \"zog/root_control/native/journal-wait.c\" in members\nprint(\"ZOG_RESIDENT_CONTROLLER_WHEEL_METADATA_PASS\")\nZOG_TEST"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/zog144-root-control-0c21718\npython3.12 -m installer --destdir=\"$DESTDIR\" dist/*.whl\ntest -x \"$DESTDIR/usr/bin/root-control\"\ninstall -d -m 0755 \"$DESTDIR/usr/lib/systemd/system\"\ncat > \"$DESTDIR/usr/lib/systemd/system/zog-root-control.service\" <<'ZOG_ROOT_UNIT'\n[Unit]\nDescription=Zog privileged root controller (protected installer activation only)\nAfter=systemd-journald.service dbus.service\nRequiresMountsFor=/state\nConditionPathIsMountPoint=/state\nConditionPathExists=/state/zog/root-control/controller.env\n\n[Service]\nType=exec\nUser=root\nGroup=root\nUMask=0077\nEnvironmentFile=/state/zog/root-control/controller.env\nExecStart=/usr/bin/root-control\nRestart=no\nRuntimeDirectory=zog\nRuntimeDirectoryMode=0750\n# No enable target; activation and trusted GID/STATE are external.\nZOG_ROOT_UNIT\nchmod 0644 \"$DESTDIR/usr/lib/systemd/system/zog-root-control.service\"\ntest ! -e \"$DESTDIR/etc/systemd/system/multi-user.target.wants/zog-root-control.service\""
    ]
  ],
  "environment": {
    "PIP_NO_INDEX": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTHONSAFEPATH": "1"
  }
}

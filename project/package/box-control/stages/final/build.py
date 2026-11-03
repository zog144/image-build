# Source candidate data; evaluated with ast.literal_eval. Not native approval.
{
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/zog144-box-control-b513a9b/box-control\npython3.12 - <<'ZOG_BUILD'\nimport importlib,importlib.metadata,pathlib,sys,sysconfig,tomllib\nassert sys.version_info[:2]==(3,12)\nassert sysconfig.get_config_var(\"SOABI\")==\"cpython-312-x86_64-linux-gnu\"\ndata=tomllib.loads(pathlib.Path(\"pyproject.toml\").read_text())\nassert data[\"project\"][\"name\"]==\"box-control\"\nassert data[\"project\"][\"version\"]==\"0.1.0\"\nassert data[\"project\"][\"scripts\"][\"box-control\"]==\"zog.box_control.cli:main\"\nassert data[\"project\"][\"dependencies\"]==[\"image-build==0.2.0.dev5\",\"dbus-next==0.2.3\"]\nassert data[\"build-system\"][\"build-backend\"]==\"setuptools.build_meta\"\nfrom packaging.requirements import Requirement\nfrom importlib.metadata import version\nfor text in data[\"build-system\"][\"requires\"]:\n req=Requirement(text)\n assert version(req.name) in req.specifier,(\"missing selected build prerequisite\",text)\nbackend=importlib.import_module(\"setuptools.build_meta\")\npathlib.Path(\"dist\").mkdir(exist_ok=True)\nprint(\"ZOG_SOURCE_WHEEL\",backend.build_wheel(\"dist\",{}),flush=True)\nZOG_BUILD"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/zog144-box-control-b513a9b/box-control\npython3.12 - <<'ZOG_TEST'\nimport email,pathlib,sys,sysconfig,zipfile\nassert sys.version_info[:2]==(3,12)\nassert sysconfig.get_config_var(\"SOABI\")==\"cpython-312-x86_64-linux-gnu\"\nwheels=list(pathlib.Path(\"dist\").glob(\"*.whl\"))\nassert len(wheels)==1\nwith zipfile.ZipFile(wheels[0]) as wheel:\n assert wheel.testzip() is None\n members=wheel.namelist()\n assert all(not name.startswith(\"/\") and \"..\" not in pathlib.PurePosixPath(name).parts for name in members)\n prefix=\"box_control-0.1.0.dist-info/\"\n meta=email.message_from_bytes(wheel.read(prefix+\"METADATA\"))\n assert meta[\"Name\"].replace(\"_\",\"-\").lower()==\"box-control\"\n assert meta[\"Version\"]==\"0.1.0\"\n for dep in [\"image-build==0.2.0.dev5\",\"dbus-next==0.2.3\"]:\n  assert dep in (meta.get_all(\"Requires-Dist\") or []),(dep,meta.get_all(\"Requires-Dist\"))\n assert \"box-control = zog.box_control.cli:main\" in wheel.read(prefix+\"entry_points.txt\").decode()\n assert \"zog/box_control/__init__.py\" in members\n assert any(m.startswith('zog/box_control/') for m in members)\nprint(\"ZOG_RESIDENT_CONTROLLER_WHEEL_METADATA_PASS\")\nZOG_TEST"
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cd upstream/zog144-box-control-b513a9b/box-control\npython3.12 -m installer --destdir=\"$DESTDIR\" dist/*.whl\ntest -x \"$DESTDIR/usr/bin/box-control\""
    ]
  ],
  "environment": {
    "PIP_NO_INDEX": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTHONSAFEPATH": "1"
  }
}

# Unselected native and service acceptance contract.
{
  "schema": 1,
  "status": "SOURCE_DEFINED_NATIVE_NOT_ACCEPTED",
  "source_revision": "0c217182d25f05b9cc0f7528ee614bb5669370d3",
  "installed_entrypoint": "usr/bin/root-control",
  "source_pyproject": "pyproject.toml",
  "runtime_python": "python-resident312-final",
  "service_mode": "privileged systemd daemon",
  "unit_installed": true,
  "unit_path": "usr/lib/systemd/system/zog-root-control.service",
  "unit_auto_enabled": false,
  "runtime_uid": "root",
  "runtime_gid": "root",
  "socket_path": "/run/zog/root-control.sock",
  "socket_group": "installer-selected protected numeric GID; absent by default",
  "state": "STATE mount required before privileged daemon; no installation keys in image",
  "native_requirements": [
    "root-control==0.1.0 and box-control==0.1.0 precise companion package",
    "image-build==0.2.0.dev5 API and dbus-next==0.2.3",
    "selected static journal-wait helper at usr/libexec/zog/journal-wait if barrier enabled",
    "signed installer-authorized service/group/STATE admission",
    "compiled wheel RECORD and root-service installed bytes",
    "native systemd journal and separate nonroot caller tests"
  ],
  "source_grant": false,
  "native_accepted": false,
  "rights_approved": false,
  "auto_enable": false
}

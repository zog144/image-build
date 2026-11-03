# Unselected native and service acceptance contract.
{
  "schema": 1,
  "status": "SOURCE_DEFINED_NATIVE_NOT_ACCEPTED",
  "source_revision": "b513a9bde79135c7569adc7cadb4d45a163c7841",
  "installed_entrypoint": "usr/bin/box-control",
  "source_pyproject": "box-control/pyproject.toml",
  "runtime_python": "python-resident312-final",
  "service_mode": "one-shot-project-evaluator",
  "unit_installed": false,
  "runtime_uid": "selected non-root project owner, authorized by host-install",
  "working_directory": "operator-selected owned project under that UID HOME; no shared /state fallback",
  "root_control_socket": "/run/zog/root-control.sock",
  "socket_access": "protected group membership selected by installer, never copied from image",
  "native_requirements": [
    "registered exact companion image-build==0.2.0.dev5 API and dbus-next==0.2.3",
    "compiled wheel RECORD and executable shebang",
    "native Python extension/rootfs loader provenance",
    "no production Host private state in image",
    "independently authorized project state and workspace source"
  ],
  "source_grant": false,
  "native_accepted": false,
  "rights_approved": false,
  "auto_enable": false
}

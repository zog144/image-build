# Resident B cp312 dependency chain. Exactly sourced but no accepted generation.
{
  "build": [
    "python-resident312-final",
    "resident312-setuptools-final",
    "resident312-packaging-final",
    "resident312-installer-final",
    "resident312-wheel-final",
    "box-control-final"
  ],
  "runtime": [
    "python-resident312-final",
    "resident312-image-build-final",
    "resident312-dbus-next-final",
    "box-control-final",
    "systemd-final"
  ]
}

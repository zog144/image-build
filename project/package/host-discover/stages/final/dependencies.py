# Resident B dual-ABI closure: Host utilities use /usr/bin/python3 -> Python 3.15.
# Source selection is not installed interpreter or package receipt acceptance.
{
  'build': [
    'host-identify-final',
    'host-install-final',
    'python-final'
  ],
  'runtime': [
    'host-identify-final',
    'host-install-final',
    'python-final'
  ]
}

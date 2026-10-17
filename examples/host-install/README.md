# Synthetic host-install fixtures

These fixtures contain no upstream executable or bootable rootfs. The readable
implementation is `src/zog/image_build/host_fixture.py`; expected metadata is
retained under `fixtures/`, and exact archive hashes are in `payload-hashes.json`.

Generate all four bundles outside the source checkout:

```sh
PYTHONPATH=src python -m zog.image_build.host_fixture /tmp/image-build-host-fixtures
```

The destination must not exist. The generator creates the valid, deliberately
corrupted, unsafe-path and false-readiness cases. Tests verify archive bytes,
metadata, reproducibility and expected rejection behavior. Do not commit the
generated archives. This is a synthetic contract test, not installation acceptance.

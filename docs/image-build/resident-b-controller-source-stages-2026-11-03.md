# Resident B controller source stages (held) — 2026-11-03

Two authored **catalogue-only** stages for `box-control-final` and `root-control-final`, stacked on Resident B PR #12; Boot A and previously accepted rootfs remain unchanged. Exact public commits and independently measured source archive SHA-256s:

- box-control `b513a9bde79135c7569adc7cadb4d45a163c7841`, SHA-256 `60b95ae7842dd1a81f0e5891858e4a9035c629dbbc59c06f7793d4d1499bcf05`
- root-control `0c217182d25f05b9cc0f7528ee614bb5669370d3`, SHA-256 `ecd2e33416b56c8e1124db4604af4128e77bee36175c49ebfd6671bbbb488d0f`

Archives measured with source-only GitHub Actions #41690797951; no compilation. Both upstream `pyproject.toml` files declare version 0.1.0, CPython >=3.11, setuptools >=80,<83, and exact console scripts. The recipes deliberately target `cpython-312-x86_64-linux-gnu`, require 3.12 wheel metadata and install console scripts under `usr/bin`; root-control also requires its native journal helper source and disabled `usr/lib/systemd/system/zog-root-control.service`.

**Dependency HOLD:** upstream Requires-Dist: box-control requires `image-build==0.2.0.dev5` and `dbus-next==0.2.3`; root-control requires those plus `box-control==0.1.0`. The graph explicitly names **un-authored** `image-build-python-final` and `python-dbus-next-final`. Existing setuptools, installer, packaging, wheel and cryptography sources are not demonstrated rebuilt for CPython 3.12. No false accepted inherited generation, wheel RECORD, ELF/ABI proof, native install or license approval is claimed.

**Service / authority:** box-control is a one-shot non-root CLI, not a daemon, and gets no invented service file. Root-control's systemd unit is root-owned, Type=exec and **not enableable by preset** (no Install section). It requires mounted `/state` and an **externally installed protected** `/state/zog/root-control/controller.env`, binding the numeric socket GID. Image-build may not supply this file, host identity, keys, STATE, or automatic root authority. Actual root socket ownership, persistent install, boot and privileged service activation require separate operator authorization and host-install native acceptance.

**Rights HOLD:** first-party licenses are declared BSD-3-Clause OR GPL-3.0-only; archive-internal LICENSE and THIRD-PARTY-NOTICES independent rights and SHA-256 review not yet complete. Source stages are not selectable and must never be treated as an accepted native generation. No Certbot or credential activation.

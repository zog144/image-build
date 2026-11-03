# Resident B corrective source contracts — November 3, 2026

**Scope:** candidate-only changes stacked on image-build PR #12. Neither Boot A, the existing `python-final` 3.15.0rc2 source nor any accepted rootfs generation is replaced. No native compilation, SSM, AWS, selected-program launch or credential/authority installation.

## Python 3.12.16 separate candidate

The independently sourced Python.org 2026-10-25 security release is `3.12.16`. Official XZ: `https://www.python.org/ftp/python/3.12.16/Python-3.12.16.tar.xz`; SHA-256 `b5796915dc45ff745cfb4e990a7e7c93d6f546328a102ce31448d69ebc37575c`. The `project/package/python-resident312` source candidate is `catalogue-only`, explicitly unselected, and not an accepted package for existing native generations.

The candidate installs `/usr/bin/python3.12` using `make altinstall`, not `/usr/bin/python3`: a choice of interpreter/default entry point and a collision-free, selected resident software view must be authorized separately. It expects `usr/lib/libpython3.12.so.1.0` and exact `cpython-312-x86_64-linux-gnu` `_ssl`, `_sqlite3`, `_hashlib` extensions. The candidate's build-stage tests specify `sys.version_info == 3.12.16`, `sysconfig.SOABI`, module imports and a SQLite in-memory query. The installed native evidence must additionally verify SQLite WAL and CA-trust HTTPS behavior in a sealed rootfs.

The build-stage dependency graph now names `openssl-final`, `sqlite-final`, `pkgconf-final`, `libffi-final`, `expat-final` and `gdbm-final`. OpenSSL/SQLite are also runtime predecessors. The configure script probes selected `/usr/include`, `/usr/lib`, and pkg-config paths, requires CPython `MODULE__SSL_STATE=yes` and `MODULE__SQLITE3_STATE=yes`, and suppresses undeclared site packages and default pkg-config path expansion. This **does not** itself prove no Host fallback: native witness must attest pivot-root isolation, actual selected inputs, extension ELF `DT_NEEDED` and SONAMEs, loader origins, build-tool provenance and exact installed bytes.

**Compatibility HOLD:** the existing system's OpenSSL source was intentionally selected for newer OpenSSL compatibility with Python 3.15. Python 3.12.16 + selected OpenSSL must pass real native ABI and import tests; do not infer OpenSSL 4 compatibility from successful source/configuration checks. The original Python 3.12 archive's LICENSE and other included/generated components still require rights and notice inspection before redistribution approval.

## Networking and controller source manifests

- systemd's existing `-Dnetworkd=true -Dresolve=true -Dtimesyncd=true` source stage now requires `usr/bin/networkctl` and `usr/bin/resolvectl` alongside its daemons.
- The selected `host-install@f82576c4...` wheel's `[project.scripts]` declares `host-install = zog.host_install.cli:main`. The wheel stage's required-output contract now includes `usr/bin/host-install`.
- The selected `host-discover@b6119746...` wheel declares `host-discover`, `host-discover-recovery` and `host-discover-supervisor` entry points. They are all now required stage outputs.
- `project/host/resident-b-controller-stage-contracts-v1.json` separately describes the future `box-control-final` and `root-control-final` source/packaging, Python, systemd service, UID/STATE and executable requirements. They are deliberately **not** fabricated authored final stages: exact protected source revision, rights, service/UID and native install obligations are unfulfilled.

The original PR #12 Resident B audit record now distinguishes source CLI-output declarations from genuinely native-verified executables. The source review still reports unverified Resident B and leaves the already-reviewed Boot A audit untouched.

## Required negative tests and next owner

The source CI rejects incorrect Python source/version hash, absent `_ssl`/`_sqlite3` or wrong `cp312` SOABI, missing OpenSSL/SQLite predecessors, Host pkg-config fallback, forged accepted-generation evidence, absent CLI paths, and controller contracts falsely represented as installed.

**Decision:** tighter source contracts, **native Resident B still NO-GO**. The next authorized compiler job must independently pin exact source generations and toolchain; prove Python + OpenSSL/SQLite ABI, CA trust, services, controller package and immutable installed output closure. A genuine rootfs generation and protected host-install evaluation are separate, later operations.

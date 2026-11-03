# Separate Resident B rootfs source-prerequisite audit — 2026-11-03

**Boundary:** A read-only source review of `image-build@1f07e83dbd80dacb9bed0d6494c697375f0e26cd`, cross-referenced to [host-install #4](https://github.com/zog144/host-install/issues/4) and its exact reviewed bootable-image contract `08f007cb14598d22debb2efc20eb3f00c2d8f2dd`. This audit does **not** reopen image-build PR #10's Boot A gate, select a new native generation, claim installed rootfs bytes, modify devices, activate services or require certificates.

Machine-readable source observations: `project/host/resident-b-source-prerequisite-audit.json`. The verifier `tools/verify_resident_b_source_prerequisites.py` rereads the **actual** package stage files and refuses altered source facts, forged generation IDs, invented outputs or premature readiness. It deliberately returns the listed missing requirements rather than a readiness PASS.

## Component evidence and explicit gaps

| Component | Source stage and declared outputs | Outstanding work before Resident B native acceptance |
| --- | --- | --- |
| Python | `python/stages/final` sources **Python 3.15.0rc2**, requires `usr/bin/python3`, `usr/bin/python3.15`, `usr/lib/libpython3.15.so.1.0`; package metadata still `catalogue-only` | **Requested Python 3.12 mismatch.** Decide and authorize exact runtime version independently; do not repin silently. Make SSL/SQLite extension outputs explicit and prove actual import/probe, module ABI, native ELF linkage |
| Python predecessor provenance | Python configure checks `MODULE__SSL_STATE=yes`, `MODULE__SQLITE3_STATE=yes` and reads OpenSSL/SQLite headers and pkg-config. Its actual stage `dependencies.py` lists `pkgconf`, `libffi`, `expat` and `gdbm`, **not** OpenSSL or SQLite | Add explicit reviewed build/runtime source-stage edges or a protected, exact inherited-generation binding; fail closed on Host header/library/pkg-config fallback |
| OpenSSL | `openssl/stages/final` requires `usr/lib/libssl.so`, `usr/lib/libcrypto.so`, `usr/bin/openssl`, SSL header and `etc/ssl/openssl.cnf` | Selected native generation, installed ELF/version, Python linkage and HTTPS trust probe not observed |
| SQLite | `sqlite/stages/final` requires library, header and `usr/bin/sqlite3` | Python `_sqlite3` actual module and library linkage, schema support, installed version not observed |
| CA trust | `ca-certificates/stages/final` declares `etc/ssl/cert.pem` and `etc/ssl/certs/ca-certificates.crt` | Verify trust-store source/update policy, installed bytes, effective Python/OpenSSL trust, independent acceptance |
| systemd | `systemd/stages/final` enables `networkd=true`, `resolve=true`, `timesyncd=true` and `seccomp=enabled` in source. Manifest requires three daemons | `usr/bin/networkctl` and `usr/bin/resolvectl` are **not** required by the stage manifest. Native services, seccomp behavior and network configuration not proven |
| D-Bus | `dbus/stages/final` declares `dbus-daemon`, `dbus-run-session`, library and `dbus.service`; build uses `-Dsystemd=enabled` and deliberately excludes machine identity from the reusable image | Verify system bus activation, identity handling, service dependency and account provenance |
| iproute2 and ext4 | `iproute2/stages/final` declares `ip`, `ss`, `tc`; `e2fsprogs/stages/final` declares `mkfs.ext4`, `e2fsck`, `fsck.ext4` | Actual selected installed outputs and kernel interactions remain unverified. Reuse Boot A ext4 source; do not reopen Boot A |
| Zog host controllers | `host-install`, `host-discover`, `host-identify` source stages each require a Python 3.15 `__init__.py` path | Manifest does not assert `usr/bin/host-install` or `usr/bin/host-discover`; no complete executable/service/CLI evidence. `box-control` and `root-control` lack selected `stages/final` directories at this reviewed source |
| STATE and APPLICATIONS | Host-install source contract requires verified persistent mounts and STATE-before-private-material | Native installation/STATE authorization/identity preservation remains outside source-review acceptance |

### Exact negative-readiness findings

The source manifests currently leave **six host-install Resident B requested executable paths without a required output contract:** `usr/bin/networkctl`, `usr/bin/resolvectl`, `usr/bin/host-install`, `usr/bin/host-discover`, `usr/bin/box-control`, `usr/bin/root-control`. This is an *absence from reviewed required manifests*, not proof those files could never be produced by a future build.

Offline CI regressions reject fabricated accepted-generation identities, invented installed source evidence, changed Python source/version targets, falsely added SSL extension outputs, disappearance of real DBus/CA/systemd outputs, dropped host-install requirements, hidden source blockers, certificate dependencies and any attempt to imply Boot A acceptance.

**Disposition: Resident B source prereqs NOT READY.** The review ledger and tests are ready for independent review. Resolve the Python version policy, explicit predecessor and output contracts, controller stage/launcher contracts and host-install native-generation evidence separately. Nothing here submits a compiler job or authorizes Resident B installation.

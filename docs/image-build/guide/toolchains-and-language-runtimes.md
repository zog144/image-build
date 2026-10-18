# Toolchains and language runtimes

## One accepted base, several explicit dependency closures

A later language/runtime stage consumes an **exact accepted immutable generation**, selected recipe inputs, and a pinned dependency graph. It must not accept an arbitrary host RPM as a substitute for a missing target library. Successful compilation does not imply that optional features, redistributed third-party notices or the full upstream test suites were accepted.

The documented progression is: a source-built C/C++ toolchain; target OpenSSL, SQLite and other native prerequisites; a Python runtime and its packaging backends; Rust/Cargo; Maturin; and the Python cryptography dependency. These stages intentionally use different verification profiles, not one universal "toolchain ready" flag.

## OpenSSL, SQLite and Python

The [native-library foundation](../python-libraries.md) binds target OpenSSL, SQLite, readline and their dependent tools to a selected toolchain. Source archives and developer snapshots are exact hash-pinned inputs. The document distinguishes disabled legacy protocols, TLS and SQLite functionality from claims of platform-wide cryptographic certification or full optional test coverage.

The [Python runtime](../python-runtime.md) stages Expat, GDBM, libffi and pkgconf before Python. It records explicit decisions about Python/OpenSSL API compatibility, configured extension modules, original upstream source, installed tests and unresolved redistribution/license issues. Python source version exceptions belong in the reviewed monthly set; they are not inferred by tracking upstream master.

The [enrollment dependency plan](../python-enrollment.md) builds the packaging backend and Python distribution closure from pinned publisher sdists. Wheels are created **within build storage** using installed source-built backends. The build frontend does not run pip network dependency resolution inside isolated jobs. Checks cover wheel structure and selected installed imports/probes, not blanket upstream suite completion. Default CA behavior and consumer-selected trust stores remain separately documented.

## Rust, Cargo and native Python wheels

The [Rust bootstrap](../rust-bootstrap.md) explicitly permits only the upstream-hash-bound foreign stage-0 compiler/std/Cargo seeds needed to produce a target stage-2 compiler. These are build inputs rather than published target binaries. Vendored crates, frozen lockfiles and offline execution prevent Cargo from resolving or fetching an unreviewed dependency at build time. Tests check selected standard-library and installed compiler/Cargo cases; missing optional ecosystem features are not silently presumed.

[Maturin](../maturin-bootstrap.md) is bootstrapped from the publisher source with an exact dependency closure. Its executable first builds its own wheel; installed Python tooling then consumes the wheel. Native Linux wheel generation without portability repair does **not** establish manylinux portability.

The [cryptography stage](../cryptography-bootstrap.md) uses that Rust/Maturin/Python stack and links the explicitly selected target OpenSSL rather than embedding an unreviewed vendored OpenSSL copy. This is not a FIPS certification or permission to infer complete license coverage from a package's top-level license metadata.

## Host-boot and graphics prerequisites remain separate

Native [systemd prerequisites](../systemd-native.md), [boot build tools](../boot-build-tools.md), and [graphics foundation](../graphics-foundation.md) have separate source closure and acceptance. Source-recipe CI, installed basic tool probes, privileged kernel tests, a booted host, and a working TurboVNC graphics seat are distinct gates. A complete Python dependency closure is also not permission to put station-access Django packages into the base rootfs: the application store publishes them under a separate immutable view compatible with the selected base.

## Status and evidence checks

Before composing a generation, inspect: the exact pin file/digest, installed base inventory, declared build/runtime dependency edges, license/notices evidence, tested feature set, output acceptance, and immutable generation identity. Preserve omissions and skips as gaps in the canonical record. Do not rewrite previously frozen source or job histories when a later recipe gains additional validation.

## Detailed technical references

- [Native libraries](../python-libraries.md), [Python](../python-runtime.md), [Python dependencies](../python-enrollment.md)
- [Rust](../rust-bootstrap.md), [Maturin](../maturin-bootstrap.md), [cryptography](../cryptography-bootstrap.md)
- [Systemd native prerequisites](../systemd-native.md), [boot tools](../boot-build-tools.md), [graphics foundation](../graphics-foundation.md)
- [Monthly pins and provenance](sources-and-monthly-pins.md)

The linked documents contain revision-specific versions and commands. Verify exact active build capability before presenting historical status as current live acceptance.

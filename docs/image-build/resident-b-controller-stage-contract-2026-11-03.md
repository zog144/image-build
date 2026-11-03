# Resident B controller stage contract — source design (2026-11-03)

This is a **source-only, unselected contract**, not an authored controller final recipe, build, native installed receipt, authority installation or change to Boot A. Companion: Resident B prerequisite audit in image-build PR #12 and host-install #4. Preserve the existing pinned Python 3.15.0rc2 graph; independently reviewed Python 3.12 candidate must be selected explicitly before changing ABI paths.

## Required stage and installed-byte obligations

| Stage | Source and executable contract | Runtime closure and admissibility |
|---|---|---|
| `systemd-final` | `usr/bin/networkctl`, `usr/bin/resolvectl` plus `systemd-networkd`, `systemd-resolved`, units, `systemctl` | Verify ELF interpreter, SONAME and inherited library provenance, config and service readiness; no configuration or native run is authorized here |
| `host-install-final` | `usr/bin/host-install`, versioned `zog.host_install` module and wheel `RECORD` | Validate launcher shebang/interpreter and wheel metadata entrypoint; refuse absent launcher, wrong interpreter, stale wheel pin, path escape or missing dependency |
| `host-discover-final` | `usr/bin/host-discover`, `usr/bin/host-discover-recovery`, `usr/bin/host-discover-supervisor`, versioned `zog.host_discover` module and wheel `RECORD` | Ensure all three script names match pinned wheel `entry_points.txt`; exact `host-identify` and `host-install` dependencies and crypto/HTTP closure; do not install or enable services implicitly |
| `box-control-final` (not authored) | A separately source-pinned package with declared build/install/test phases, Python entrypoints selected from its actual metadata, wheel `RECORD`, package files and required execution assets | Bind exact Python ABI, `root-control` runtime interface and cgroup/mount/systemd dependencies. Validate non-root and root privilege boundaries in synthetic tests |
| `root-control-final` (not authored) | Source-pinned package and protected daemon/service entrypoint selected from actual metadata, native helper binaries/libraries if required, wheel `RECORD`, systemd unit/socket/config outputs | Requires `box-control-final`, `dbus-next`, and any real `image-build` runtime code; no assumption that existing stage graph ships these. Must verify imported modules and no host-library fallback, exact service user, root-only mutable paths, credentials and non-root selected-program boundary |

## Controller-stage implementation gate

1. Inspect **exact pinned source** for box-control and root-control, including `pyproject.toml`, entrypoints, native helpers, service units and actual distribution dependencies. Their current default branches are not valid immutable installation selections.
2. Create `project/package/{box-control,root-control}/stages/final/` with `sources.py`, `source-provenance.py`, `dependencies.py`, `build.py`, `integration.py`, `produce-manifest.py` using the existing data-only stage grammar. Build and install only from verified source digests. Never infer entrypoints or unit names.
3. Require `usr/bin` launchers and `usr/lib/pythonX.Y/site-packages` modules as appropriate, wheel `RECORD` entries with bytes/digests, and packaged services only if actually authored. Reject missing/misplaced executables, `/usr/local` escape, wrong shebang, missing C helper, missing library, wrong ELF loader, unpinned dependency, missing D-Bus identity, or enabled privileged service absent explicit Host selection.
4. Use native receipt generation for file ownership/mode, linker and Python import closure, service startup/stop and authoritative Host/STATE identity. This cannot be proved by source manifests, unit paths or source CI.
5. Keep principal boot gates separate: Boot A can boot without these Resident B services; Resident B requires explicit selected generation, verified STATE/APPLICATIONS mounts, inert installation first and separately authorized activation.

## Source negative tests

The prerequisite verifier now rejects dropping `networkctl`, `resolvectl`, `host-install` or any required host-discover launcher. Its existing tests reject unreviewed runtime edges, controller stages falsely claimed as present, a substituted Python ABI, and premature native acceptance. The **missing controller stages remain negative gates**; tests must move to full stage validation only after exact source and transitive dependencies are reviewed.

**Disposition: output manifest source closure improved; controller source stages and native installed-byte evidence remain NO-GO.**

# Resident B Python 3.12 transitive source-stage closure — 2026-11-03

**Scope:** source definitions on image-build PR #14 stacked on PR #12. **No native build**, accepted generation, installation, certificate dependency, new production package pin or operator authorization. This is a prepared, source-only graph; PR #12's Python 3.12.16 candidate and incumbent Python 3.15.0rc2 remain separately selected. Existing Python 3.15 setuptools 84.0.0 stages are untouched.

## Exact original-source candidates

These are seven separate `catalogue-only` packages under `project/package/resident312-*/stages/final/`. Each has `package.py`, `sources.py`, `dependencies.py`, `build.py`, `produce-manifest.py`, `license.py` and `integration.py`. All archived source bytes were checked in [read-only GitHub Actions #41698385299](https://github.com/zog144/image-build/actions/runs/41698385299).

| Stage | Version | Original archive SHA-256 | Build predecessors beyond exact Python 3.12 |
| --- | --- | --- | --- |
| resident312-flit-core-final | flit_core 3.12.0 | `18f63100d6f94385c6ed57a72073443e1a71a4acb4339491615d0f16d6ff01b2` | Source in-tree bootstrapping only |
| resident312-installer-final | installer 1.0.1 | `052c7fc3721d54c696e2dea019be67539d7b144e924f559f54beb3121831c364` | flit-core |
| resident312-packaging-final | packaging 26.3 | `94edc256424af38762eb31306eed28beb9f0efc50a8837492c9d6fd6004aed79` | flit-core, installer |
| resident312-wheel-final | wheel 0.48.0 | `94800765601e9171bf5d58d066e640662842bcedcbab982b2c90787a2c987322` | flit-core, installer, packaging |
| resident312-setuptools-final | setuptools 82.0.1 | `7d872682c5d01cfde07da7bccc7b65469d3dca203318515ada1de5eda35efbf9` | packaging, installer, wheel |
| resident312-dbus-next-final | dbus-next 0.2.3 | `f4eae26909332ada528c0a3549dda8d4f088f9b365153952a408e28023a626a5` | setuptools, wheel, installer, packaging |
| resident312-image-build-final | image-build 0.2.0.dev5 | `74ca7fe804e08eb6102ca7ce2e227476aa8f448872cec08b6d6b1fab60b4f376` | setuptools, wheel, installer, packaging |

The `image-build` interface source is the *immutable public commit* `1f07e83dbd80dacb9bed0d6494c697375f0e26cd`, **not** the moving PR #12 or PR #14 head. Its original project, LICENSE and notice source members were separately inspected with their hashes. Runtime API compatibility with the controller commits remains a distinct native/interop hold.

## Original archive review findings

- **Dynamic-version originals:** flit-core, installer, packaging and wheel declare dynamic source versions. Their source-stage configure phases now read source `PKG-INFO` rather than assuming `pyproject.toml.project.version`.
- **Legacy dbus-next:** the 0.2.3 original sdist has no `pyproject.toml`. Its source stage explicitly checks original `PKG-INFO` and `setup.py` and uses the selected setuptools **legacy** PEP 517 backend; no fabricated upstream `pyproject.toml` was introduced.
- **Compatible setuptools:** `setuptools>=80,<83` in both original controller `pyproject.toml` files excludes the existing Python 3.15 recipe's **84.0.0**. This separate source stage pins **82.0.1** instead. Original setuptools source contains vendored dependencies (including `packaging` and `wheel`), whose included files and redistributed notices require later exact component attribution. Original flit-core also includes vendored material.
- **Source rights:** original LICENSE/NOTICE member presence was inspected without a copyright-holder redistribution decision. Each candidate `license.py` remains unresolved and the installed/transitive notice map remains a hold.

## Updated controller selection contracts

`box-control-final` and `root-control-final` now select **only** `resident312-setuptools-final`, `resident312-packaging-final`, `resident312-installer-final`, `resident312-wheel-final` for building, and `resident312-image-build-final`, `resident312-dbus-next-final` for runtime. `root-control-final` additionally retains its exact `box-control-final` and `systemd-final` requirements. No unqualified `setuptools-final`, `dbus-next-final`, `wheel-final`, or Host package source is an accepted substitute.

The source recipes require an explicit `/usr/bin/python3.12 -I`, a constrained `PATH`, no `PYTHONPATH`/user-site/PIP fallback, selected-root `/usr/lib/python3.12/site-packages` module resolution with version checks, strict upstream source roots, and wheel Name/Version/`METADATA`/`RECORD` outputs. These are **intended runtime checks**, not evidence that they executed on the native Host.

`tools/verify_resident312_transitive_sources.py` reads all seven actual package-stage files and controller references, cross-checking exact source hashes, versions, predecessor edges, isolated interpreter paths, manifest paths, unapproved rights and no-genuine-generation controls. `tests/test_resident312_transitive_source_closure.py` rejects missing edges, altered SHA-256, stale setuptools 84, legacy-backend substitution, missing `PKG-INFO` for dynamic versions, wrong `RECORD`, Host fallback and fabricated receipt/admission. The controller source verifier delegates to this independent graph gate. [Exact-source CI #41698459065](https://github.com/zog144/image-build/actions/runs/41698459065) passed with Python 3.12/3.13 synthetic test lanes; the final commit must be rechecked if this document changes the head.

## Native and security HOLD

**Source candidate graph defined does not mean native build-ready.** Before a compiler request, independently authenticate accepted immutable predecessor generations for all seven sources and CPython 3.12; verify actual source/archive and patch inputs and selected GCC/Python provenance, sealed rootfs PATH and header/library origins, build backend dynamic requirements, wheel `RECORD` and installed-module byte maps, native `dbus-next` API plus image-build interface compatibility, and per-file vendor notice delivery.

The source review has **no signed native generation receipt**, no installed runtime source-to-ELF closure, no permission to enable root-control service or grant its socket GID, no private STATE identity, and no rights approval. Boot A, Python 3.15 and certificate installation are unchanged.

**Disposition:** all seven missing transitive source-stage definitions are **authored and source-verified**; native stage production, compatibility and protected controller installation remain **NO-GO**.

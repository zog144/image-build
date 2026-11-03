# Independent Python 3.12 and exact pinned controller stage review — 2026-11-03

**Source-only review.** Original image-build PR #12 `python-final` (3.15.0rc2) is unchanged. The separate `python-resident312` 3.12.16 source candidate remains `catalogue-only`; this report does not select a compiler, installed interpreter or Host authority.

## Python candidate

The source pin is Python.org `Python-3.12.16.tar.xz` with original published SHA-256 `b5796915dc45ff745cfb4e990a7e7c93d6f546328a102ce31448d69ebc37575c`. Exact expected ABI: `cpython-312-x86_64-linux-gnu`. Required outputs include `python3.12`, `libpython3.12.so.1.0`, and `_ssl`, `_sqlite3`, `_hashlib` with that SOABI.

Selected build/runtime source dependencies require `openssl-final` and `sqlite-final`; configure checks original root-relative headers, pkg-config, `MODULE__SSL_STATE=yes` and `MODULE__SQLITE3_STATE=yes`. The negative suite checks exact version, archive hash, ABI and extension paths, source fallback strings and any attempted native status change.

**Unverified native conditions:** `LD_LIBRARY_PATH="$PWD" ./python` is an *in-tree build test*, not installed-byte evidence. The string checks, `PKG_CONFIG_LIBDIR`, `PKG_CONFIG_SYSROOT_DIR=/` and a declared pivot-root requirement cannot prove no Host headers, libraries, developer modules or ELF interpreter were used. Only a trusted native worker/manifest with selected-tool inputs, ELF `DT_NEEDED`/SONAME/loader closure and installed interpreter SSL/SQLite/CA and WAL tests can establish that. Python 3.12 compatibility with Zog's actual OpenSSL build remains untested. Original archive license/member and generated-code rights remain HOLD.

## Original controller source inspection

The original pinned GitHub tarballs were independently downloaded in read-only [Actions run 41690378955](https://github.com/zog144/image-build/actions/runs/41690378955); no protected Host, AWS or compilation involved.

| Component | Public source commit | Original archive SHA-256 | Pinned source package |
| --- | --- | --- | --- |
| box-control 0.1.0 | `b513a9bde79135c7569adc7cadb4d45a163c7841` | `60b95ae7842dd1a81f0e5891858e4a9035c629dbbc59c06f7793d4d1499bcf05` | `project/package/box-control/stages/final` |
| root-control 0.1.0 | `0c217182d25f05b9cc0f7528ee614bb5669370d3` | `ecd2e33416b56c8e1124db4604af4128e77bee36175c49ebfd6671bbbb488d0f` | `project/package/root-control/stages/final` |

Both source stages include source/notice hashes, exact `pyproject.toml` and LICENSE/THIRD-PARTY-NOTICES checks, wheel packaging via the pinned CPython 3.12 interpreter, required `/usr/bin` console entry points, `zog.*` Python module outputs, and installed original notices.

**box-control:** source `box-control/pyproject.toml` declares `box-control = zog.box_control.cli:main`. The program is a one-shot evaluator that discovers an authorized project within the caller's HOME. No global box-control daemon or automatic systemd unit is authored; a future workspace-specific launch needs an explicitly selected non-root project user, owned directory and root-control socket grant.

**root-control:** source `pyproject.toml` declares `root-control = zog.root_control.daemon:main`. A draft root-owned `zog-root-control.service` source output is authored with `ConditionPathIsMountPoint=/state`, `RequiresMountsFor=/state`, `Type=exec`, `ExecStart=/usr/bin/root-control`, and no [Install] activation section. The root-owned default socket cannot grant box-control access until host-install separately selects the protected numeric GID and service/STATE/authority. Journal barrier is disabled by default; its separately static-compiled `/usr/libexec/zog/journal-wait` helper remains a later native prerequisite if enabled. The wheel retains its C source only.

**Unresolved transitive source-stage producers:** `setuptools-final`, `packaging-final`, `installer-final`, `wheel-final`, `image-build-python-final` and `dbus-next-final` are named obligations but are not accepted selected package stages. Their actual source revisions, built bytes, Python import/ABI and source rights are not inferred from either controller archive. Root-control specifically requires pinned box-control 0.1.0 and image-build 0.2.0.dev5 interfaces.

The machine contract `project/host/resident-b-controller-stage-contracts-v1.json` and `tools/verify_resident_b_controller_source_stages.py` preserve these holds; negative tests reject fabricated source SHAs, missing executable/notice outputs, changes to root service security clauses, automatic service enablement and premature package admission.

**Disposition:** independently reviewed source-stage definitions, **Resident B native generation NOT READY**. No compiler submission, root service activation, protected key/identity installation or redistribution clearance.

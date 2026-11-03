# Resident B final combined source reconciliation — November 3, 2026

**Scope:** source-only image-build PR #15 stacked on PR #14 and PR #12. No compiler, rootfs publication, package admission, credential/STATE installation, protected group grant, root-control service activation or boot.

## Immutable integration, without replacing either review

- **PR #14 selected source inputs:** `e64e682f2fb2df8f590737683b99188c16fc51c0`. Seven CPython 3.12 candidates with independently verified archive hashes and a separate compatible setuptools 82.0.1; production Python 3.15.0rc2 and its setuptools 84.0.0 remain unchanged.
- **PR #15 reviewed installation inputs:** `bc5a93b18fd8ce39f3e72cd67d05dc0534f98b88`. Exact upstream root-control/box-control daemon/CLI and source systemd service checks.
- **Integration:** non-destructive two-parent merge `6f553ba6e0ec56d6b84fa553fdae643b434d1cfc` (parents PR #15 source and PR #14 source), using exactly PR #14's source tree plus all four PR #15 review files. No forced branch rewrite or silently substituted source pin.
- **New source join:** `project/host/resident-b-pr14-pr15-combined-source-review.json`, `tools/verify_resident_b_combined_source.py`, `tests/test_resident_b_combined_source_reconciliation.py`. The combined source workflow requires **both** original immutable histories to be ancestors and runs the original installer review together with the CPython 3.12 graph verifier, negative tests, and preexisting Boot A audits.

## Source package and installation obligations

`python-resident312-final` remains unselected. For wheel builds, both controller stages require `resident312-setuptools-final` (82.0.1), `resident312-packaging-final`, `resident312-installer-final` and `resident312-wheel-final`. Runtime edges name `resident312-image-build-final` at original immutable commit `1f07e83dbd80dacb9bed0d6494c697375f0e26cd` and `resident312-dbus-next-final` at 0.2.3. The exact transitive Python 3.12 tool chain also includes flit-core. `root-control` additionally depends on `box-control-final` and `systemd-final`. Old `setuptools-final`, `dbus-next-final`, host wheel modules, or a forged accepted generation cannot be substituted.

The held `box-control` stage has exact `usr/bin/box-control`, `zog/box_control/__init__.py`, `box_control-0.1.0.dist-info/METADATA`, `RECORD`, and original LICENSE/THIRD-PARTY-NOTICES outputs. Its one-shot CLI requires a separately selected non-root user and owned per-user HOME project; it **does not** install a global daemon service.

The held `root-control` stage has exact `usr/bin/root-control`, its Python package plus `root_control-0.1.0.dist-info/METADATA` and `RECORD`, original notices, journal barrier *C source*, and a root-owned `usr/lib/systemd/system/zog-root-control.service`. The service requires the STATE mount, runs as root with `Type=exec`, and has no `[Install]` activation section. A mounted `/state` is **not** authenticated STATE identity. The protected socket `/run/zog/root-control.sock` and numeric group cannot be provisioned from the image or granted by the source stage; selection belongs to host-install.

The combined verifier checks exact expected outputs (including wheel `RECORD`, V1 script/module/notice paths), the root service and non-root ownership boundary, exact dependencies and remaining no-native-grant flags. Negative tests remove edges or installed outputs, alter the service mount condition, invent native receipts, reselect stale source SHA, or claim rights.

## Remaining independent native and rights holds

No accepted selected predecessor generation for Python 3.12 or these tool/runtime stages; no actual sealed-root module/ELF loader origin or wheel `RECORD` byte attestation; no native Python SSL/SQLite/CA and root-control import/IPC proof; no protected STATE/UID/GID/service installation; no approved redistribution rights, including vendored Python build tools. Source CI may use a GitHub Actions Python for its **tests**, never as evidence that a Host compiler or package installer selected that Python. The previously rejected Boot A image is untouched.

**Disposition: combined exact-source readiness review PASS, Resident B native installation and boot still NO-GO.**

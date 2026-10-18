# Loader-cache correction verification — 2026-09-25

Live box-control verification job `6491c0251f77ff3f1a678aa893bd5e7f` completed with exit 0.
It ran the two original loader scripts unchanged and three direct fseek confirmations.
The independent isolation probe `116a2da4e3aaf0c7a47985f26ba3b4ab` also passed.
Six earlier direct fseek runs passed across tmpfs and XFS; the intermittent timestamp
failure's cause is not yet established. These targeted runs are not full-suite acceptance.

The new literal fixture metadata parses with ast.literal_eval, and the worker compiles.
Core image-build modules and box-control were unchanged in this pass; the previous local
127-test result is historical, not a new test run. No blanket failure exemptions were added.

---

# Latest correction verification — 2026-09-25

From the image-build source root, with the corrected box-control source on PYTHONPATH:

```sh
python -m pytest -q tests /path/to/box-control/tests/test_build_backend.py /path/to/box-control/tests/test_build_jobs.py
```

**127 passed in 4.83 seconds**, Python 3.12. Focused ownership tests verify that a new
node inherited with GID 993 is normalized, while an existing incorrectly owned node is
rejected without changes. This does not substitute for the live isolation probe.

The old probe was reconciled and released using supported controller API calls. The
corrected backend was deployed only after checksum verification and confirmation that
all old finite jobs had completed cleanup. A detached supervisor was launched. Latest
observed live progress is in CURRENT-STATUS.md; no test success is claimed.

---

# Publication verification — 2026-09-25

Executed locally by the implementation assistant against this assembled source tree:

```sh
PYTHONPATH=/path/to/glibc-device-correction-pass2/box-control python -m pytest -q
```

Result: **89 passed in 4.58 seconds**, Python 3.12. The box-control dependency is the
separately supplied device-correction source, not a published compatibility pin.
These are local unit/integration simulations and do not establish live systemd isolation
or successful Glibc tests. An initial command from the parent workspace collected unrelated
historical copies and failed collection; the command above was rerun from this source root.

Read-only AWS inspection confirmed the supervisor failure and device ownership described
in CURRENT-STATUS.md. No compilation or retry was started in this publication pass.

The first final Glibc compilation previously succeeded, but its upstream test suite failed.
The latest private-null probe has not executed. No final self-hosting acceptance is claimed.

Source assembly checks confirmed that the two adapter/configuration files are the only
Python implementation differences between the latest two image-build snapshots. The final
Glibc stage and plan from the newer recipe snapshot are preserved. Credentials and generated
Python caches are excluded. Historical test evidence in handoffs is labeled by its pass.

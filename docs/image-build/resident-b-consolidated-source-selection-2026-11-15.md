# Resident B consolidated source selection — 15 November 2026

**Scope: source-only.** This is the single follow-on to the previously combined
source graph from image-build PRs #12, #14, #15 and #16, not a new rootfs or a
second implementation of Python, systemd or controllers.

The frozen machine-readable candidate is
`project/host/resident-b-consolidated-source-selection-v1.json`, verified by
`tools/verify_resident_b_consolidated_source.py` and its negative tests.
Controller package stages remain the existing
`project/package/{box-control,root-control}/stages/final`, **catalogue-only**.
Their original source tarball pins, path prefixes and rights member records are
updated to the measured successor archives; no other dependency stages are
duplicated.

## Reused source graph

| Segment | Selected stages/outputs | Boundary |
| --- | --- | --- |
| Python for controllers | `python-resident312-final` = CPython 3.12.16; `_ssl`, `_sqlite3`, `_hashlib`, shared libpython | Exact OpenSSL, SQLite, libffi, expat, gdbm and pkgconf source dependencies; no Host fallback or replacement of Python 3.15 |
| Python wheel tools | `resident312-flit-core`, installer, packaging, wheel, setuptools, dbus-next, image-build `-final` | Exact earlier pinned wheel/metadata source graph, still requiring native closure |
| Resident networking | `systemd-final` | `systemd-networkd`, `systemd-resolved`, `networkctl`, `resolvectl` already required in output manifest |
| Existing Host utilities | `host-install-final`, `host-discover-final` | `host-install`, `host-discover`, `host-discover-recovery`, `host-discover-supervisor` already declared |
| Controllers | `box-control-final`, `root-control-final` | Exact source, cp312 wheel metadata, entry point, RECORD and notices; disabled root-control service remains source-only |

**Important ABI distinction:** existing host-install / host-discover package
manifests still name `usr/lib/python3.15/site-packages`, while the reviewed
Resident B controller wheels use `usr/lib/python3.12/site-packages`. Both
Python source lines must be independently verified in the real resident root.
No source step was taken to relabel or rewrite the existing host utilities as
Python 3.12 modules.

## Reconciled newer controller source

The November 3 Resident B stage recipes pinned older controller revisions
which predated inherited-user finite build and combined Certbot issuer/Task C
corrections. We now select:

| Package | Exact source commit | Measured upstream archive SHA-256 |
| --- | --- | --- |
| box-control | `c886e7a90bb4ea74e771a6c5dcefaa2069539ec7` (PR #21) | `2a2749f9c223fb947695634008c5e37cafc49248c19f84262f60e23c7575a121` |
| root-control | `d9dfd6c02a5a96750f1213bf663cdceab72f1efd` (PR #51) | `8be83a4d9e50f7165ea08f70b8443cad4553b079fa058d29c3544766ebca5de1` |

The upstream `pyproject.toml`, LICENSE and controller entry-point metadata
were measured and compared with the original stage contract. Both projects
continue to declare version `0.1.0` and compatible
`image-build==0.2.0.dev5` / `dbus-next==0.2.3` metadata. Root-control also
requires `box-control==0.1.0`. The source has the combined issuer,
trusted-Host Task C and inherited-build modules, and box-control supplies
issuer functionality with no per-request UID/GID selector. These statements
describe **reviewed source**, not native runtime acceptance.

The earlier root-control notice hash in the draft was truncated. The newly
downloaded tarball proves its full SHA-256 is
`b3aa6c652c70db0faecdd42d35723c62bc61282dc53a2c1d19d53d73f637f26e`.
The source stage, original-rights evidence and independent source verifier
now use this entire digest. No permission or distribution decision was inferred
from that source-hash correction.

## Native release boundary

The existing independent installed-generation evidence verifier now pins the
same source revisions, while retaining its original negative constraints:
`accepted_generation=null`, no compiler permission, no service activation.
Its synthetic observations and disposable signatures are not a real resident
rootfs receipt.

The real installation still needs: accepted input generation and package
predecessors; compilation of both Python runtime roots/SSL/SQLite
extensions; trusted installed wheel/RECORD/ELF/readback; actual root-control
issuer/Task C/inherited-user checks with the selected box-control companion;
verified STATE and socket access; and an independent source notices/rights
decision. No new users, dedicated compiler worker, S3 approval infrastructure,
or hardware GPU requirement is introduced.

No package compilation, EC2 change, Task C admission, SSM/SQS dispatch,
rootfs publication, Resident B boot, or service enablement occurred during this
source consolidation.

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


## Intended native input generation and complete package-source closure

**Source-selected input:** the already published and targeted-verified immutable
Boot A successor `273de2a04a8a0b8d4db3005bca078639f3c2fdcd6f9e24a9619d2b0ca6947aab`,
producer `68d6397ca20c4651df8f13c8a840dc8f77d55034`, retained
parent `45a81ec3ea473bfa397e546b5c0ec1ae306bf00cb864eaa9a86d94c13c623f2e`.
It is the *same* exact generation selected in
[host-install PR #39](https://github.com/zog144/host-install/pull/39)
at reviewed commit `c783ccbaa2768efd6d9e3c4c5d2c3e1215180b5a`.
Its source handoff reports a 40,974-entry inventory and 27 provenance records.
The failed predecessor `5af34ec67cbfdcd1e7936bf70e3cf2f5c6945c7e3de5f95993918325f6e29c44`
and its failed native switch-root result remain untouched.

**Important evidence boundary:** selecting the corrected Boot A `kind=image`
generation as Resident B's *intended native build predecessor* neither
verifies the actual package contents of that generation nor proves a successful
resident boot. Its exact canonical archive SHA-256 and installed package
receipt are not available in this source handoff, so those slots stay `null`
in the selection. The image-build Work owner must read back exact retained
generation/archive/installed contents before using it. No new acceptance
certificate, installation source or authority mechanism was invented.

**Package graph:** the same selection now fixes 21 top-level package roots,
covering the separate Python 3.12 controller stack and incumbent Python 3.15
utilities, OpenSSL/SQLite, controller source/wheels, CA certificates, D-Bus,
systemd networking and iproute2. Existing
`project/package/*/stages/final/dependencies.py` are recursively evaluated,
including the real build-only `systemd-test-environment` and
`pyelftools-build` definitions. This resolves to **29 distinct source
stages**, pinned by
`sha256:4b99171aadafa0e094115045736c75e2e0642c46b85f40f9f9d813e2fe85f236`.

The 29 source stage names, in canonical sorted order, are:
`box-control-final`, `ca-certificates-final`, `dbus-final`,
`expat-final`, `gdbm-final`, `host-discover-final`,
`host-identify-final`, `host-install-final`, `iproute2-final`,
`libffi-final`, `openssl-final`, `pkgconf-final`,
`pyelftools-build`, `python-cryptography-final`, `python-final`,
`python-resident312-final`, `readline-final`,
`resident312-dbus-next-final`, `resident312-flit-core-final`,
`resident312-image-build-final`, `resident312-installer-final`,
`resident312-packaging-final`, `resident312-setuptools-final`,
`resident312-wheel-final`, `root-control-final`, `sqlite-final`,
`systemd-final`, `systemd-test-environment`, `tzdata-final`.

**This is a source dependency closure, not a fabricated native package
closure.** The native owner must compare the actual predecessor generation's
installed package records and exact bytes against this graph, decide which
outputs are already present and which source stages require new builds, and
check installed ELF/wheel/CA/STATE/identity closure. There is no basis in
the source-only record to mark an edge as an accepted inherited package.
Both `predecessor_package_receipts_verified` and
`package_binary_closure_verified` remain false; no native build or
activation is authorized.

`tools/verify_resident_b_native_input_closure.py` is read-only and checks
the exact source generation, upstream host-install plan (when supplied),
complete graph and its digest; `tests/test_resident_b_native_input_closure.py`
denies substituted generations, dishonest receipt claims, omitted package
stages, a missing predecessor and cycles. The source-selection CI checks the
exact host-install PR #39 checkout alongside the original Resident B packages.

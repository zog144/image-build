# Non-resident Certbot: verified combined controller + host-install attestor aggregate

**Scope:** image-build Regular's reproducible, nonpublished `zog` aggregate used
by host-install Work to perform real installed-byte attestation. Resident boot,
new Host identity, Cloudflare credentials and certificate issuance are not
prerequisites for this package build.

## Why the November 16 package needed a distinct successor

The old `zog-0.1.1.dev20261116` wheel contained reviewed box-control PR #21
and root-control PR #51, but inherited the original `zog` base's older
`zog.host_install`. That CLI did **not** contain
`certify-manage-controller-attest-installed`. Controller import and RECORD
checks therefore did not prove that the native host-install attestor could
be invoked. Never replace/relabel the old wheel or silently splice one new
Python file into a previously installed aggregate.

The new original source tuple is:
- Public `zog` aggregate base commit
  `d47d86b363824c718d9c165124cb55bbed12e0f9` (14 component identities,
  existing release metadata; other eleven components retained from this base).
- Complete box-control PR #21 commit
  `c886e7a90bb4ea74e771a6c5dcefaa2069539ec7`
  (52 reviewed original runtime files).
- Complete root-control PR #51 commit
  `d9dfd6c02a5a96750f1213bf663cdceab72f1efd`
  (26 original runtime files).
- Complete host-install selected importer commit
  `9ad4e951ef0a14cc6a735af47ffb31734d854816`
  (74 original files, including the new `cli.py`,
  `certify_manage_profile.py` and nested protected systemd unit templates).

The producer replaces all three **whole source directories** before
building, changes their exact in-wheel manifest revisions (including
host-install component version `0.14.9`), and selects the separate
development version `zog==0.1.1.dev20261117`. Its pinned original
source trees are `project/host/resident-b-aggregate-installed-source-pins-v1.json`
and `project/host/nonresident-certbot-host-install-source-pins-v1.json`.
The nonresident selection is
`project/host/nonresident-certbot-aggregate-build-v1.json`.
The old `zog==0.1.0` public release and November 16 candidate remain
unchanged. No PyPI upload.

## Actual built wheel and installed-byte evidence (disposable GitHub runner)

[Actions #44090347882](https://github.com/zog144/image-build/actions/runs/44090347882)
**PASS** at producer commit
`6d3fdcd8bd211aa554919f378545cc4f15bc3c0a`.
The build uses Python 3.12 and the same reviewed pinned packaging inputs as
before. Two independent builds produced bit-for-bit identical wheel archives
and installed RECORD checksums. This is an **actual built and installed
wheel**, not a hand-written fixture.

- **Wheel:** `zog-0.1.1.dev20261117-py3-none-any.whl`
- **SHA-256 wheel:** `bf8560e3ee228dc6390f708bb9282472bbc7e14b154b5841c7ba912901b204c8`
- **SHA-256 installed RECORD:** `b4aea0184dcd267f1070bcc6b72e8ab3d85d714b5d2031e2eabe12463108d8a3`
- **Selected target:** `/usr/bin/python3.12`,
  `/usr/lib/python3.12/site-packages`,
  `zog-0.1.1.dev20261117.dist-info/RECORD`.
- **Retained archive:** GitHub Actions artifact
  `nonresident-certbot-zog-development-wheel-unaccepted`, ID
  `14331262525`, expires **December 1, 2026**. It contains the
  real wheel, original byte-evidence report, independent controller readback,
  and complete host-install attestor byte readback.
- **Readback:** `verify_resident_b_aggregate_installed.py` reopened
  *every* installed RECORD member and each selected original controller
  Git blob. `verify_nonresident_certbot_host_install.py` independently
  verified all 74 actual installed host-install source files/modes against
  their pinned original Git blobs and the same RECORD. Missing nested
  `systemd/root-backed` resources initially caused an explicit failed
  check; the producer now includes the selected nested resource files
  in the actual wheel and verifies them. The failure history is preserved.
- **Import smoke:** the actual wheel was clean-installed in an isolated
  Python 3.12 virtual environment. It loaded the box-control,
  root-control and host-install console entry points, plus eleven selected
  issuer, Task C, build and attestor modules, and `pip check` passed.
  `/tmp/zog-certbot-import/bin/python -I -m zog.host_install --help`
  explicitly exposed `certify-manage-controller-attest-installed`.
  23 source/tampering/selection checks passed.

The separately recorded **source candidate** is
`project/host/nonresident-certbot-built-wheel-disposable-evidence-2026-11-17.json`.
It never claims native installed acceptance, controller readiness, issuer
authority or station permission.

## Required image-build Work / host-install Work native sequence

1. Reopen [the selected successful workflow](https://github.com/zog144/image-build/actions/runs/44090347882)
   and its actual wheel artifact. Verify the complete wheel SHA-256 and
   original four source commits. Never reuse the previous November 16
   wheel hash as if it contained the new host-install CLI. If artifact
   retention has expired, independently reproduce a **new** receipt.
2. On the **same non-resident Host and installation**, inspect the actual
   `/usr/bin/python3.12`, installed Python version, root-owned executable
   mode, real `sysconfig` site path, and existing installed `zog`
   distributions. Do not replace or relabel unrelated Python 3.15 Host
   utilities or silently mix versions.
3. Through a separately approved installer operation, install the exact
   candidate into the chosen immutable application view/ordinary
   nonresident installation. Bind the actual Host/installation identity,
   concrete install root, package/revision, immutable generation,
   canonical wheel hash, **actual final installed RECORD**, complete byte
   inventory, installer result, and preparation/provenance receipts.
   Unlike the GitHub runner fixture, this stage must prove real Host
   file ownership (root), import paths, and immutability. Do not copy
   the CI receipt into a fabricated native acceptance.
4. Independently run the image-build complete installed-record checker
   against the newly installed root with root ownership checks,
   plus the host-install importer source check. The final
   `RECORD` may differ if generated launcher installation conditions
   differ; independently hash the **actual bytes** and check against
   installation provenance rather than merely requiring the CI staged
   digest to match without considering source selection.
5. **host-install Work** invokes the exact original handoff command as
   root and without Python path overrides:

   ```sh
   env -u PYTHONPATH -u PYTHONHOME /usr/bin/python3.12 -I \
     -m zog.host_install certify-manage-controller-attest-installed \
     --python-executable /usr/bin/python3.12
   ```

   The selected host-install importer independently checks all fifteen
   issuer-critical box/root modules, their Git hashes, imported origins,
   installed RECORD hashes/byte sizes, secure ancestry and exact Python
   3.12 distribution layout. The result is a **read-only attestation**;
   success is not by itself a controller restart, issuer preparation or
   certificate readiness.
6. Preserve the original installation/STATE/Host identities and prior
   failed/uncertain operation records. The original station approval for
   the **same** Host/installation/hostname/DNS-01 zone/staging policy and
   the protected HTTPS/anonymous-FD Cloudflare credential delivery are
   **separate authority operations**, required before any authenticated
   selected preparation and `inspect`/`observe`. Avoid changing
   credentials, issuing certificates, DNS writes, or starting production
   issuer services during installed-byte attestation.

## Operational design

The source of **software authority** is the pinned reviewed Git commit
and exact wheel/installed byte receipts, not the fact that a module can
be imported. The source of **runtime interpretation** is the actual
selected root-owned `/usr/bin/python3.12`, not the ambient
`/usr/bin/python3` (which may be 3.15). The source of **certificate
authority** is the separately signed station assignment and protected
Host policy, not a successful package verification. These independent
gates keep the existing Host useful and its credential/STATE lineage
intact when coordination services are offline.

**Status:** source and disposable *real package* acceptance PASS; original
nonresident Host installed-byte attestation NOT RUN; station assignment
NOT RUN; protected credential delivery NOT RUN; selected native issuer
`prepare`/`inspect` NOT RUN. Resident Zog boot is not required.

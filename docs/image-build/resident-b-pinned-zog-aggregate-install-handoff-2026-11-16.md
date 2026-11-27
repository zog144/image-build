# Resident B pinned aggregate and installed-byte/RECORD gate — November 16, 2026

## Purpose and exact boundary

Host-install issuer installation's native `certify_manage_profile.attest_installed_controller()`
expects **one installed Python distribution called `zog`**, not separate
`box-control` and `root-control` distributions. It imports selected modules
through the active interpreter, checks their original Git blob content against
exact pins and checks the installed aggregate wheel `RECORD` hashes. This
must remain independent of the issuer's hostname/DNS-01 assignment and
protected Cloudflare credential-delivery authority.

Image-build PR #24's current Resident B source stages instead describe two
distinct controller wheels:
`box_control-0.1.0.dist-info/RECORD` and
`root_control-0.1.0.dist-info/RECORD`. Those source manifests and the existing
read-only verifier are useful for separately installed components but
**do not prove the single `zog` aggregate**. The current
`SOURCE_CANDIDATE_PINNED_NATIVE_HOLD` and `catalogue-only` state are correct.
Do not re-label individual component-wheel output as an installed aggregate.

## Accepted source selection, not installed acceptance

Source selection remains:
- box-control PR #21 at commit
  `c886e7a90bb4ea74e771a6c5dcefaa2069539ec7`, original tarball
  SHA-256 `2a2749f9c223fb947695634008c5e37cafc49248c19f84262f60e23c7575a121`;
- root-control PR #51 at commit
  `d9dfd6c02a5a96750f1213bf663cdceab72f1efd`, original tarball
  SHA-256 `8be83a4d9e50f7165ea08f70b8443cad4553b079fa058d29c3544766ebca5de1`.

`project/host/resident-b-aggregate-installed-source-pins-v1.json`
records the exact original Git blobs and modes of **all 52**
`zog.box_control` source files and **all 26** `zog.root_control` source
files (including `native/journal-wait.c`). The source identity and
corresponding installed runtime bytes must remain identical; tests reject
changed commit, missing/extra tracked modules and altered source content.

The new read-only `tools/verify_resident_b_aggregate_installed.py`:
1. Reopens the two original Git checkouts at their exact reviewed commits,
   checks clean tracked state and verifies every selected runtime source blob.
2. Given an independently built/unpacked **actual** aggregate rootfs, verifies
   the installed `zog-0.1.0.dist-info` METADATA, WHEEL, console script
   mappings and the entire installed `RECORD`, rehashing all listed bytes,
   lengths and file identities.
3. Independently checks every selected box/root module's installed bytes
   against its original pinned Git blob and mode. RECORD rehashing alone
   cannot authorize substituted controller source.
4. Can demand root ownership of all RECORD members for native rootfs
   readback (`--require-root-ownership`). Returns a **nonsecret, unsigned,
   unaccepted** observation. It cannot install a wheel, sign the observation,
   grant issuer rights, select a Host or authorize service activation.

CI tests generate a deliberately synthetic, *non-publishable* aggregate
layout from the genuine source checkouts to test byte substitution,
rehashed malicious RECORD, symlinks, an absent RECORD, source pins and
authorization refusal. This is **not** a build of the actual aggregate,
nor a native package or installed artifact.

## Remaining producer / native output gate

**Target: image-build Work, coordinated with image-build Regular and
the release owner of the single `zog` distribution.** Before building:
- Select the reviewed source revision and exact archive/digest for the
  *aggregate's remaining components*, not only the two controllers.
  Review the complete aggregate source closure, metadata, licenses and
  entry points. Preserve source-only/public redistribution holds; do
  not silently repack an old PyPI `zog==0.1.0` wheel with new bytes or
  publish a replacement at the same version.
- Resolve the interpreter/installed-path contract: PR #24's controller
  stages use CPython 3.12 and
  `usr/lib/python3.12/site-packages`; current host-install issuer
  attestation defaults to `/usr/bin/python3`, and the existing Host
  utility stages still target Python 3.15. Verify the actual selected
  interpreter/ABI and align *one* supported installed aggregate, not
  assume the two paths are interchangeable.
- Obtain the separately approved compiler/predecessor source admission,
  perform the actual permitted build in a distinct native attempt, and
  retain exact aggregate wheel SHA-256, full wheel RECORD and member
  inventory, verified final install root contents, selected generation,
  canonical receipt and build-tool/parent provenance. Do not substitute
  the synthetic CI fixture or the historical `273de2a0…` Boot A
  selection for the corrected successor.
- Install only into the immutable selected rootfs under the reviewed
  preparation/publishing process; then run
  `verify_resident_b_aggregate_installed.py --box-source ... --root-source
  ... --rootfs ... --require-root-ownership --output ...`.
  The output must be independently checked against the original source
  pins, actual original wheel, installer and generation receipts, and
  physical installation source. This script does not mint an authority.
- Once the actual installed aggregate is selected, have host-install Regular
  reconcile its **older** module-source selection and attest the same new
  compatible controller pair. Existing source-pins in host-install's
  `certify_manage_profile.py` are based on earlier
  box-control `73d64fb8…` and root-control `8bb9a563…`, not the
  selected PR #21/#51. In the currently inspected host-install PR #42
  source, four of the 15 specifically pinned imported modules have
  different Git blobs: `zog.box_control.issuer_lifecycle_broker`,
  `zog.box_control.issuer_lifecycle_client`,
  `zog.root_control.daemon`, and `zog.root_control.systemd`.
  The other selected modules still require native readback.

## Separate station / host-install authority gate

**Target: original station authority / station-access Work.** A new managed
DNS-01 assignment must be approved by the original station signing
authority, explicitly preserving the same independently verified Host ID,
installation ID, approved hostname, DNS-01 zone and ACME staging policy,
with the genuine policy and credential revision. A source pin or test
assignment cannot grant this. Do not fabricate/re-sign from image-build.

**Target: host-install Regular and Work, with root-control/box-control.**
After source/installed identity reconciliation and the genuine fresh
assignment, use the supported authenticated HTTPS purpose-scoped,
protected anonymous-FD issuer credential delivery; never put the
Cloudflare token in source, argv, SSM output, environment, logs or public
evidence. Reconcile the existing uncertain/failed installation attempt
against its durable ledger and source/assignment revisions, preserving
valid Host identity, grant/storage, STATE and certificate lineage, rather
than resetting or silently repeating mutation. Only then perform
controller-selected preparation and authenticated `inspect`/`observe`,
with installed program, real systemd InvocationID, durable ledger and
reboot readback. DNS-01 issuance and production deployment remain separately
authorized operations.

**Current status:** Controller pins and synthetic aggregate installed-byte
verifier are source-tested; **no actual pinned aggregate wheel, installed
RECORD, original station approval, private credential delivery, native
preparation, selected inspection or boot is claimed here.**

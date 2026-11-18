# Non-resident Certbot: stage dependency scripts privately, preserve Amazon Linux jp.py

**Date:** 2026-11-18. **Owner:** image-build Regular (source); native Host installation belongs to image-build Work. No existing package, command, credential or acceptance receipt was modified in this source work.

## Existing accepted installation

The original Amazon Linux 2023 Host already has the reviewed
`zog==0.1.1.dev20261117` wheel installed under
`/usr/lib/python3.12/site-packages`. The retained native report confirms:
- All 509 original zog RECORD entries have passed installed-byte verification.
- All 16 original zog launchers use `/usr/bin/python3.12`.
- The exact accepted installed zog RECORD has SHA-256
  `8a4428184d096a1f24e68b394b6dcd26a23cf345fe59d7e74ce18c57493e6d30`.
- Ten direct runtime distributions were missing; only 13/15 checked controller imports passed, with `dbus_next` absent from root-control daemon/systemd.

The next installation must add **only** the existing reviewed 24 dependency wheels without invoking pip against the live `/usr` prefix, replacing zog or changing any RPM-owned executable. The prior November 17 handoff's direct `pip --prefix /usr` command is **superseded**: ordinary pip would install `jmespath`'s `jp.py` under `/usr/bin` and could collide with the existing Amazon Linux RPM.

## Exact unchanged dependencies and separate staging tool

The 24 runtime wheel bytes/versions are still selected by
`project/host/nonresident-certbot-python312-dependencies.lock`.
Their PyPI archives and all SHA-256 identities are unchanged.
They must be verified with
`tools/verify_nonresident_certbot_dependency_wheelhouse.py`
before use. The staging helper uses PyPA `installer==1.0.1` from a
**separate** `project/host/nonresident-certbot-python312-stage-installer.lock`.
Its only reviewed wheel, `installer-1.0.1-py3-none-any.whl`, is pinned
to SHA-256 `011d045df8b954ced7dde3a7e42ae4418da40ecda7990f2d11d5ed7c146fd98b`.
It is an ephemeral **build/install tool**, never the 25th runtime
distribution in the live Python 3.12 environment.

The actual private-script producer is
`tools/install_nonresident_certbot_dependencies_staged.py`.
It uses `installer`'s supported `SchemeDictionaryDestination` with:
- `purelib` and `platlib`: `/usr/lib/python3.12/site-packages`;
- `scripts`: `/usr/libexec/zog/python3.12/bin`;
- script interpreter: `/usr/bin/python3.12`;
- no bytecode generation, no overwrite, no wheel alteration and no PATH update.

**Both script formats are covered:** original files in a wheel's
`*.data/scripts/` directory, and launchers synthesized from
`console_scripts` or `gui_scripts` entry points. The official installer
automatically regenerates each distribution's **installed** `RECORD`
with the correct relative final script path, actual generated/shebang-
adjusted byte hash, and size. The private `jp.py` RECORD path is
`../../../libexec/zog/python3.12/bin/jp.py` relative to site-packages;
it does **not** claim the RPM-owned `/usr/bin/jp.py`.

The 24 real wheels produced **seven** actual private scripts in CI:
`cffi-gen-src`, `django-admin`, `idna`, `jp.py`, `normalizer`,
`sqlformat`, and `waitress-serve`. The staged layout has zero dependency
scripts under `/usr/bin`. Both the complete wheel payload and generated
scripts are independently included in verified final RECORD memberships.

## Complete preflight before any live write

The installer first creates a **new private 0700 temporary workspace**,
verifies all 24 original wheel hashes, checks each original wheel RECORD,
stages *every* wheel into a disposable filesystem root, and validates all
24 resulting installed distribution RECORDs. It rejects any installed
member that is not within the reviewed Python3.12 library or private-script
trees, any missing/duplicated/unhashed member, invalid file permissions,
symlinks, or a script RECORD whose destination/hash does not match the
private installed script.

Only after staging completes does `preflight()` inspect **every** live
target file, all directory ancestry, all script destinations, and any
cross-distribution ownership overlap. Existing files cause an unconditional
HOLD; an identical file's bytes are **not** an excuse for overwrite.

For an actual Host root (`--live-root /`), preflight additionally reads the
original accepted zog RECORD and hashes **all 509 original members and
all 16 launchers**, requiring the exact original RECORD digest,
`/usr/bin/python3.12` shebangs and unchanged contents. The same
readback is repeated after installation.

An explicit authorized `--apply` then redoes **the entire preflight**
before creating any live file. It retains a durable staging-local
`live-commit-preflight.json` intent before its first live write and uses
directory-FD `O_NOFOLLOW` plus exclusive `O_EXCL` creation for each
target, with postcopy byte/mode verification. It can never overwrite
`/usr/bin/jp.py` or the accepted zog launchers. An interrupted commit
may leave some new dependency files; the staging area and intent must be
retained for **explicit reconciliation**, not blindly retried or rolled
back. No compiler or remote command is invoked by this source work.

## Reviewed disposable CI evidence

[Exact-source image-build CI run #44311877069](https://github.com/zog144/image-build/actions/runs/44311877069)
passed 15 focused synthetic/negative tests and staged the original
24 hash-locked real wheels. It verified all **24 installed RECORDs**,
the seven actual private scripts and their relative RECORD destinations,
a byte-identical simulated RPM-owned `/usr/bin/jp.py`, and rejection of an
unexpected pre-existing private `jp.py` before any simulated live file
appeared. Negative tests also exercise library collisions, symlinked
ancestry, script/entrypoint collisions, RECORD tampering, and create-only
test-root commit preserving an original zog launcher/RECORD fixture.
The CI artifact `nonresident-python312-private-dependency-script-preflight`
(ID `14430836856`, retained through December 2, 2026) includes the
staged preflight with all original 24 wheel SHA-256 hashes, all 24
actual installed RECORD SHA-256 hashes, each relocated script's final
path/owner/hash/size, and the separately pinned staging tool wheel.
No original Host files were accessed.

## image-build Work: original Host dependency-only operation

1. Open the reviewed 24-wheelhouse evidence and exact dependency lock.
   Retrieve the separate hash-verified `installer-1.0.1` tool wheel into
   a temporary directory. Do not include `installer` in the live 24
   runtime package set.
2. Verify the same original Host's `/usr/bin/python3.12`, package owner,
   original 509-entry RECORD digest, all 16 launchers and the existing
   RPM-owned `/usr/bin/jp.py` before any writes. Check whether any
   direct/transitive package's files already exist; refuse conflicts.
3. In a disposable temporary Python 3.12 venv, install the **tool only**
   from its separately pinned wheel with `--no-index --require-hashes`.
   Then use that venv's interpreter to invoke the image-build script.
   The venv is only for wheel unpacking and RECORD generation; installed
   scripts still use the real `/usr/bin/python3.12` interpreter.
4. Generate and review a complete no-write preflight (using a **fresh**
   workspace path):

   ```sh
   /TEMP/installer-venv/bin/python \
     tools/install_nonresident_certbot_dependencies_staged.py \
     --wheelhouse /REVIEWED/24-wheels \
     --workspace /TEMP/dependencies-preflight-1 \
     --live-root / \
     --output /TEMP/dependencies-preflight-1.json
   ```

5. Only under a separately authorized root-owned native operation, rerun
   staging and preflight from the **same hash-locked wheels**, with a
   distinct fresh workspace and the explicit `--apply` switch:

   ```sh
   /TEMP/installer-venv/bin/python \
     tools/install_nonresident_certbot_dependencies_staged.py \
     --wheelhouse /REVIEWED/24-wheels \
     --workspace /TEMP/dependencies-accepted-attempt-1 \
     --live-root / --apply \
     --output /TEMP/dependencies-accepted-attempt-1.json
   ```

   The second call independently repeats exact wheel hashes, installed
   RECORD validation and **all** live collisions before the first
   create-only operation. On a collision it writes **nothing** live.
6. Verify the real final installed RECORD of **each** 24 distributions,
   real root ownership, exact private-script paths and shebangs,
   the RPM-owned original `/usr/bin/jp.py` hash, and unchanged original
   zog 509-member RECORD/16 launchers. Run `/usr/bin/python3.12 -I -B -m pip check`
   (if the selected pip supports the isolated invocation) and all
   15 exact imported controller modules under that interpreter. Do not
   add the private script path to PATH or change any existing service.
7. Retain Host/installation-scoped nonsecret original preflight,
   staged manifests, original wheel/tool hashes, original and final
   RECORD/launcher digests, 24 dependency versions, scripts and
   module import evidence, and the durable operation identity. Keep
   the previously accepted aggregate installation and old failed
   operation records intact.

Only then can host-install Work use the already reviewed root-owned
`certify-manage-controller-attest-installed` importer and continue its
separate station assignment, protected FD credential delivery, old-attempt
reconciliation and selected DNS-01 issuer preparation/inspection.

**State:** real-wheel staged/private-path and collision CI **PASS**;
existing nonresident Host installation **NOT RUN** here; accepted zog and
Amazon Linux files **NOT CHANGED** by Regular. Resident Zog boot is
not required.

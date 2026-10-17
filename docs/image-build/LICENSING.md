# Upstream package licensing

All 39 current catalogue projects have a literal `license.py`. These records bind
upstream name/version, release URL and archive SHA256 to paths and full-file hashes
of evidence inspected in that archive. They record primary terms, scoped component
exceptions and unresolved patch licensing separately from Zog's own licensing.

The initial records are **declared**, not completed public-release reviews. A
primary SPDX expression is not a blanket license for bundled files. LicenseRef
identifiers refer to retained upstream terms where a precise SPDX mapping has not
been established. Remaining component review is explicit for every project.
Six previously unpinned catalogue sources were downloaded for this review; their
license records bind the observed archive hashes without silently authorizing a
new build recipe or changing its upstream source-pin review status.

## Authoring and execution

Use the existing `license.py` files as the schema. Required fields are schema,
package, version, source (url/sha256), status, expression, scope, evidence,
components, patches and notes. Evidence records contain path, sha256 and
source_sha256. Components and patches contain scope, expression, status and notes.
Review states are declared, reviewed and unresolved. Expressions support AND, OR,
WITH and parentheses, a deliberately explicit SPDX identifier subset, and local
LicenseRef identifiers. Extend the supported subset when reviewing a new license.
Do not mark unresolved terms as reviewed merely to pass validation.

Catalogue validation requires a license record. Stage materialization snapshots
one canonical project record into each stage, unless an explicit stage override
exists. Its source digest must match a declared recipe input. Record changes alter
package fingerprints and cache input identities. Historical standalone recipes
without license metadata retain their old fingerprints for compatibility.

Before successful package cleanup, image-build verifies each required notice in
both the extracted source and the original checksum-verified archive. It retains
full notice bytes and a receipt under:

    /usr/share/licenses/zog-packages/<stage-name>/

For exclusively sysroot/ or tools/ outputs, the same directory is placed under
that prefix. Receipts contain the record identity, source inputs, reconstructable
recipe data and file ownership hashes. They enter normal output inventories,
composition collision checks and generation provenance. Source archives and raw
patch inputs are copied and synced separately to:

    <state>/image-build/release-inputs/<sha256>

This store has no automatic expiry. Normal extracted-source cleanup can continue;
source-cache/mirror expiry must not remove retained release inputs. The release
store is local retention infrastructure, not a public corresponding-source offer.

## Offline release readiness

    python -m zog.image_build.licensing GENERATION_DIRECTORY --state STATE_DIRECTORY

The JSON report contains eligibility, package records, issues and unresolved file
paths. Exit status is 1 when review/evidence/source retention or file coverage is
incomplete. A reviewed synthetic package passes the tests; the current catalogue
intentionally does not claim public readiness. Existing generations remain
readable and unreviewed. Inherited/seed files without matching ownership receipts
are listed explicitly rather than being relabelled source-built or reviewed.
Additional source/patch inputs currently require further review and block release.
Prefix-relocated staged receipts and composition-modified shared files can also
remain uncovered; the check fails conservatively until ownership transformations
are explicitly recorded. It does not infer a complete dependency licence audit
from an executable's primary SPDX declaration.

This implementation does not restart or rewrite ongoing build snapshots. New
materialized runs acquire the metadata after deploying this version. Station-access
and packaging still need separate coverage for pip/npm dependencies outside the
image-build package catalogue.

## License notice access across execution identities

For new source preparations, image-build verifies each declared license notice
against its frozen evidence digest and adds read bits (`mode | 0444`) to that
notice alone before controller registration. Existing write/execute bits, bytes,
and timestamps remain unchanged. Unrelated source files and installed output
modes are untouched. Symlink paths and shared hard links are rejected.
`license-readability.json` records the policy and changed paths/modes/hashes in
the package attempt. The original archive and its digest remain authoritative.

This is needed because box-control returns workspace directory ownership after
execution while regular files keep the build identity. Archive notices with
modes such as 0640 would otherwise become unreadable to the orchestrator.
Finalization still verifies extracted working content and original archive
notices; it never silently skips a notice or falls back to unverified content.
If a build subsequently removes access, finalization fails closed.

The policy applies only before preparing a new attempt. Resuming an existing
attempt does not silently normalize its frozen working tree. Administrative
recovery must independently establish completed cleanup, safe file ownership,
and unchanged evidence, and retain an explicit receipt.

## Supplementary upstream notices

A notice that is **not present in the original source archive** must not be recorded
as though it were archive evidence. A package may instead declare an optional
`supplementary_notices` list in its schema-1 `license.py`. Each entry uses the
contract `image-build-supplementary-notice-v1` and contains:

- a stable local notice identity;
- the exact independently retrieved upstream raw source specification
  (`https://` URL, SHA256, destination, and `archive=False`);
- either the upstream Git repository, exact 40-hex revision and source-tree notice path,
  or the narrow `image-build-canonical-web-notice-provenance-v1` binding described below;
- the delivered filename, which must match the raw-source destination basename and,
  for Git-bound notices, the upstream notice-path basename;
- an explicit scope and review note.

The exact raw source specification must also be present in the package's normal
`sources.py`, so existing hash-pinned acquisition/cache machinery retrieves it.
The notice source cannot be the package's primary source, cannot double as ordinary
license evidence, and cannot double as a patch input. Only an explicitly declared
supplementary-notice source is excluded from `unreviewed_sources`; arbitrary extra
recipe sources continue to block release readiness.

Delivery remains visibly separate:

- evidence extracted from an original archive is recorded with origin
  `original-source-archive` and remains under `texts/<source-sha>/<path>`;
- legacy/raw declared source evidence is recorded as `declared-raw-source`;
- independently retrieved supplementary notices are recorded as
  `independently-retrieved-upstream-notice` and installed under
  `supplementary/<notice-id>/<source-sha>/<filename>`.

A receipt containing supplementary notices uses receipt schema 2 and retains the
full supplementary declaration, source identity, selected provenance binding,
origin and installed path. The
offline release gate recomputes the delivered notice hash, requires the declaration
and delivery sets to agree exactly, verifies retained source bytes in
`release-inputs`, and fails if a supplementary delivery is missing, changed or
reclassified.

This mechanism supplies additional upstream notice/grant text; it does **not**
change the package's SPDX expression, review state, component scope, binary
incorporation finding, or the meaning of evidence already found inside the original
archive.

### Canonical web text incorporated by a declared source archive

The Git-revision provenance form is still preferred. The canonical-web form is a
narrow source-incorporation proof for cases such as linux-keyutils where the exact
packaged source incorporates a canonical license URL but the full text is not a
same-project Git file.

The original primary-source form remains valid unchanged:

```python
"incorporated_by": {
    "source_sha256": "<exact primary archive SHA256>",
    "path": "<exact archive member, e.g. README.md>",
    "sha256": "<exact member SHA256>",
}
```

A nested archive uses the same contract but replaces `source_sha256` with the
complete selected recipe source descriptor:

```python
"incorporated_by": {
    "source": {
        "url": "https://...",
        "sha256": "<exact nested archive SHA256>",
        "destination": "crates/example-1.0",
        "archive": True,
    },
    "path": "example-1.0/README.md",
    "sha256": "<exact member SHA256>",
}
```

Nested descriptors must match exactly one source in the selected package stage.
They cannot alias the primary source, reuse a supplementary raw notice, overlap a
patch input (including a same-hash alias), or name a non-archive source. A nested
archive may also supply ordinary evidence from other exact members; those evidence
members remain independently hash-checked and do not turn the archive into the
supplementary payload. The independently retrieved raw notice still cannot also be
ordinary evidence. The descriptor is used both during preservation against the hash-verified source cache
and during the offline release audit against
`release-inputs/<nested-source-sha256>`. The archive and bound member must be
regular files, both hashes must match, and the member bytes must contain the exact
reviewed canonical URL. Binding a nested source does not by itself clear broader
`unreviewed_sources` licensing status.

The supported mapping remains deliberately explicit:
`http://www.apache.org/licenses/LICENSE-2.0` maps to the hash-pinned full-text
retrieval `https://www.apache.org/licenses/LICENSE-2.0.txt`. No repository or Git
revision is invented, and unreviewed canonical-web URL mappings are rejected.

For Git-bound supplementary notices on supported immutable raw hosts,
`raw.githubusercontent.com` URLs are also parsed and required to encode exactly the
declared GitHub repository, 40-hex revision and source-tree path. Query strings,
fragments, percent-encoded paths, extra path separators, moving-head references and
other ambiguous or mismatched forms fail closed.

This is not a generic web-license shortcut. It requires an exact source-archive
incorporation chain and does not support moving or unbound web text.

Regression coverage includes the real python-maturin selected source list and exact
linux-keyutils 0.2.5 descriptor, preservation/offline audit of a nested archive,
source/member/receipt tampering, overlap rejection, primary-form compatibility and
GitHub raw URL repository/revision/path mismatch cases.


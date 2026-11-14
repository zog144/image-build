# Finite-build controller configuration: inherited identity

The controller configuration and image-build adapter no longer carry a selectable execution UID/GID. All finite compilation operations are submitted to box-control/root-control without identity-selection fields. A legacy controller.json containing either `execution_user_id` or `execution_group_id` is rejected by `configured_runner`, not silently accepted or rewritten. The running service process's existing effective identity applies; the privileged root-control backend does not switch into a fabricated build-owner/worker account. This is an intentional source-schema break and requires an explicit updated controller.json with a new digest from host-deploy.

Current root-control keeps finite-service cgroup limits and controlled filesystem mounts. Future normal application execution under box-control can supply application-level isolation instead of bespoke worker accounts. Do not treat source-only tests as native installed credential acceptance.

## First Fonts immutable source continuity and October pin hold

The new identity-free producer revision retains byte-exact `project/bootstrap/graphics-fonts.py` and all original libpng → FreeType → Fontconfig package definitions (source-checked by `tests/test_first_fonts_inherited_producer.py`). The historical source revision `1f07e83dbd80dacb9bed0d6494c697375f0e26cd` and accepted compiler receipt are not rewritten.

**Do not re-add `project/pins/2026-10-01/commit-pin.py` to this public source branch.** The existing `tools/public_candidate_preflight.py` deliberately prohibits that historical path. The retained October pin identity remains `sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`; provenance must be verified against the actual retained original material, not reconstructed from a new file. The present host-deploy remote source-selection contract expects the pin below its selected source root; the public successor alone cannot meet that contract. Native execution is **HOLD** pending a reviewed source/runtime binding that keeps the original pin evidence separate and allows the newly selected identity-free executable. No ad hoc pin file, schema bypass or edited historical record is permitted.


## November 14 — implemented retained-input separation (supersedes prior source HOLD)

The identity-free producer now supports a *separately retained original monthly
pin*. It does not require the old pin inside the selected executable checkout.
The supported remote CLI consumes:

- `--repository-root` and `--source-revision`: the immutable, clean **new**
  image-build executable source tree, with the original Fonts recipe definitions
  byte-identical to the reviewed historical source.
- `--provenance-pin`: the existing application-State content-addressed file
  `<state-dir>/image-build/build-record/artifacts/d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`.
- `--expected-pin-digest`: `sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`.
- `--retained-pin-source-revision`: the original source
  `1f07e83dbd80dacb9bed0d6494c697375f0e26cd`, distinct from the selected
  executable revision.
- `--retained-pin-repository-path`:
  `project/pins/2026-10-01/commit-pin.py`, the original provenance path,
  **not** a path expected inside the new checkout.

The producer validates exact artifact location, SHA-256, schema/month, symlink
exclusion, file type/mode and actual effective-process readability. It captures
the provenance record with the *original* source identity, checks the artifact
again after capture, and uses those same original bytes to construct the
content-addressed recipe snapshot while keeping execution source and output
identity on the *new* revision. No replacement pin data is generated. The
previous in-repository pin mode is retained for other already reviewed lanes.

The artifact must exist before this CLI is invoked; host-deploy owns the
source-reviewed one-time `fonts_pin_retention` operation that copies genuine
bytes from the original Git-verified historical checkout into the existing
application state after host-install's copied-project migration. No new Host
user/group, storage volume, privileged switch, network service or host-side
package dependency is requested. The existing State contains one additional
immutable content-addressed pin file (and its existing directories if absent).
The public-source preflight still prohibits `project/pins/2026-10-01`.

Source CI covers successful capture under the original commit identity,
digest/path/symlink tampering and recipe-snapshot construction with no October
pin in the executable checkout. **Native migration, exact producer installation,
Task C controller integration, catalogue rebinding and compiler admission remain
separate HOLDs.** The original accepted compiler-base receipt was not altered.

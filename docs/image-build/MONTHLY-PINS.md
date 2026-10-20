# Monthly source pins

Normal builds use a reviewed monthly source set, never a live master/main lookup.
The first set is `project/pins/2026-10-01/commit-pin.py`. Files contain Python
literals parsed with `ast.literal_eval`, not executable modules.
`project/pins/current.py` explicitly selects the default month. Dates name the
first day of a month; creating/correcting a set is a maintainer operation.

The initial set was recorded on October 2 for the October 1 cycle and was corrected
on October 20 after the public-source migration accidentally omitted `project/pins`.
The corrected set covers all 133 current catalogue projects and locks all 139
executable stage recipes to exact current source URLs and SHA256 hashes, including
patches, recipe-bundled inputs, supplementary notices and license materials. Seven
graphical catalogue-only source plans are source-pinned with empty `recipes`
mappings; no executable recipe is invented for them.

The corrected file byte digest is
`sha256:d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`.
Five stage source definitions changed relative to the retained pre-migration pin:
the systemd-test fixture, host-discover, host-identify, host-install and
python-maturin. Those five are rebound to the exact reviewed public recipe inputs;
the remaining 134 stage source-definition files retain their prior source bytes.
Historical materialized pin snapshots and already prepared operations are not
retargeted by this correction.

The set preserves reviewed recipe versions; it is not a verified October 1
upstream-master snapshot. Unknown upstream commit identities remain explicit where
the producer does not have an authenticated canonical revision. Final GCC retains
its explicit 15.3 fallback and exact upstream revision. Earlier GCC stages retain
their existing source versions. Non-buildable catalogue entries have provenance but
no invented executable recipe.

Stage materialization uses the current month, or explicit `pin_date="YYYY-MM-01"`
in `stage_recipes`. It saves a `commit-pin.py` snapshot in the materialized recipe
directory. Recipe sources must match the snapshot exactly; drift fails before
download or dispatch. New ImageBuild pipelines also require a lock for custom
recipe directories. The pipeline's `source_pins` digest and recipe inventory bind
the selected set. Resume checks that captured set, not today's default. Historical
pipelines without the new field keep their original recorded recipes. Existing
artifacts are not relabelled or rebuilt.

For the next month:

1. Copy the previous set into `project/pins/YYYY-MM-01/commit-pin.py`.
2. Review upstream revisions, recording exact commits when known, archive URLs,
   hashes, recipe/license changes and any fallback reason. Do not mark untested
   master snapshots as accepted.
3. Update `current.py`, validate the recipes, and run builds/tests.
4. Commit the reviewed set. Corrections within a month change its digest and Git
   commit; prepared operations continue using their original snapshots.

Each project has primary version/source provenance and a `recipes` mapping for
stages; stage-specific versions are explicit exceptions. New stages require new
pins. A source pin is not proof of test acceptance or licensing review.

For a custom materialized directory, create a literal `commit-pin.py` with
`schema: 1`, `date: YYYY-MM-01`, and `packages: {recipe_name: {sources: [...]}}`.
Each sources list must equal that recipe's sources.py, with valid URL, SHA256,
destination and archive fields. No automatic network fallback fills missing pins.

Recipe-bundled plain-text inputs use `recipe:relative/path`, with the same mandatory
SHA256 and pin-set binding as downloaded sources. The path resolves inside the
immutable recipe snapshot, not the process working directory. Missing, escaping,
symlinked or changed bundled files fail even when a cached copy exists. GCC 15's
test-only backports use this mechanism; no authenticated GitHub download is needed.

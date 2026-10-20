# October monthly pin restoration — 2026-10-20

Producer correction for image-build issue #1.

## Scope and historical boundary

The public-source migration omitted `project/pins` even though the producer still
required the October monthly lock. The retained private
`image-build-old/unstable` candidate used
`project/pins/2026-10-01/commit-pin.py` blob
`d24281945e670110c976cf37bf72038cd29f8282`.

That retained file already contained 126 project records and all 139 stage-recipe
keys present in the current public producer. It was therefore reviewed as a
candidate, not copied blindly.

Historical producer commits, materialized `commit-pin.py` snapshots, prepared
requests, lane bindings and the three retained compiler-workspace dispatches are
unchanged. This correction only defines the lock selected by **new execution from
the new producer revision**.

## Current-tree comparison

Comparing the retained old branch to the public producer found 139 shared stage
source-definition files. 134 are byte-identical. Five have legitimate current
source changes and are rebound in the corrected monthly set:

1. `build-environment/stages/systemd-test`: 2 → 4 recipe-bundled inputs. The
   COPYRIGHT digest changed and exact BSD-3-Clause/GPL-3.0-only license texts were
   added.
2. `host-discover/stages/final`: immutable public commit
   `b61197461f2fe19fd29203a1d148a66c6ce89f6d`, archive SHA256
   `6cff3197a8de39f38fa017d20d058acc477a111f7a91711a29b8a86e3dbc3f29`.
3. `host-identify/stages/final`: immutable public commit
   `1a5eac0b255c995022db6a3a4c0051efffa748cc`, archive SHA256
   `a373a43845bb89119aec50df8d3dd1b0aa2103c37106de14aab844f3a2973e9f`.
4. `host-install/stages/final`: immutable public commit
   `f82576c4f430398bc914b3e9d56b10c366ba0eac`, archive SHA256
   `1fcd0c86b57d0da441cdd101f85bceb834481e313ace01e3026fcee6ef5a0521`.
5. `python-maturin/stages/final`: 473 → 513 exact inputs. The authoritative
   maturin 1.15.0 sdist remains unchanged; the current recipe adds reviewed
   supplementary notice/license material and its exact digests.

Seven post-install graphical projects were added after the retained monthly file:
agreety, greetd, Xorg server, i3, Firefox ESR, TurboVNC and VirtualGL. Their exact
reviewed archives are represented as catalogue-only provenance with empty recipe
maps. Their existing license-scope blockers remain explicit; being source-pinned
does not make them build-ready or privileged-session-ready.

## Corrected producer lock

- selected month: `2026-10-01`
- catalogue projects: **133**
- executable stage recipes: **139**
- corrected pin byte SHA256:
  **`d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36`**
- active selector: `project/pins/current.py` → `2026-10-01`
- no external pin path, fallback or fabricated digest is used

`tests/test_monthly_pin_restoration.py` compares every current
`project/package/*/stages/**/sources.py` literal with the monthly lock, validates
all seven catalogue-only source records, freezes the pin byte digest, and
materializes the cross/temporary/native/final toolchain plans through the normal
`pins.snapshot` path. `tests/test_pins.py` is also restored to public CI.

## Consumer handoff

Host-deploy must bind only the final exact image-build producer revision containing
this correction and the SHA256 above. It must stage a new producer-bound lane/task
definition. Do not edit or reinterpret historical lane records, prepared requests,
old producer revision `857bb454e64102afa51a93ce0b9f8cce5924b67c`, or its
historical dispatches.

This correction authorizes no SSM/EC2/compiler mutation. Host-deploy Work still owns
the isolated clean-checkout/readiness rerun before any compiler submission.

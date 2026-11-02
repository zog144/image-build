# Source-only intersection of Workspace PR #9 and Mesa PR #8

PR #9 selects only a frozen read-only SHA of Mesa PR #8:
`9da9ee74b0bceeb5104fe079fd8b48a9e74ce2d4`.
The cross-branch GitHub Actions check loads the exact commit's
`project/graphics-drafts/admission-plan.json` and
`rights-admission-evidence.json`, not the moving branch or a locally
invented file. It rejects attempted rights, compiler or canonical-status
escalation in either source.

This is intentionally **not** a compilation test. It confirms that the
first Workspace graph and software-GLX graph stay separate and noncanonical
while both remain incomplete. There is no accepted fonts/XCB/X11 native
generation, no GLX runtime evidence, no actual independent scoped rights
grant, no signed compiler admission and no immutable package view.

A later reviewed integration must reconcile exact true package builds,
provenance and native selected source graph; PR #8 remains unmerged.
Do not change `project/pins/current.py`, promote a source-only package,
or claim a synthetic generation identifier. See
`project/graphics-first-workspace/closure.json` for missing i3/Xvnc
and xterm prerequisites.

## Reviewed later Mesa delta

The frozen pin advanced by exactly two commits from `ad35f53d...` to `9da9ee74...` on PR #8, **without changing** graphics sources, package definitions, original archive pins, the eight-sidecar native verifier or six production license records. The diff adds the selected-original-notice source tests, their workflow registration and the explanatory rights review. This cross-branch validator now requires exact immutable Git blob identities of those three review artifacts in addition to the original NO-GO rights/native contract. The updated selection does not certify any native/rights fact or merge either PR.

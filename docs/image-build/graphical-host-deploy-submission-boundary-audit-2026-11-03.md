# First-Workspace graphical submission readiness against host-deploy — 2026-11-03

**Reviewed immutable sources:** image-build PR #9 `54431ea8f5ed69fd120d5e862a2277c5d2a2c46d` is a source-only review snapshot; its handoff is `PREPARED_NOT_SUBMITTABLE`. Mesa PR #8 source `9cbd652226b863a7b4bb2d6d9539722e1a262508` remains a separate held candidate. host-deploy PR #8 source `a4ac7cdb4646e0fcd9a9cf49df9d367f2a108006` supplies the finite graphical chain, and stacked host-deploy PR #11 source `7d052b340a026497fd32afb82d0a290d1d6bc60e` supplies mandatory independent checkpoint/original-request security. All are source-only draft candidates, not installed Native Host authority.

## Actual host-deploy constraints

The reviewed `task_catalogue.REVIEWED_IMAGE_TASKS` and `graphics_generation_chain.TASKS` permit exactly three finite protected stages for automatic successor selection: `graphics-fonts-image-v1` → `graphics-xcb-core-image-v1` → `graphics-x11-core-image-v1`. These source tasks select the existing `image-build@1f07e83dbd80dacb9bed0d6494c697375f0e26cd` and monthly pin `2026-10-01`. The reviewed source explicitly limits the compiled task to 30 GiB work + 2 GiB external within 32 GiB dedicated storage and 21,600 seconds. The source policy has `compiler_authorized: false`; a prepared successor catalogue is **not** a compiler admission event. A real gateway build.submit requires the typed task, exact repository/revision/pin/lane binding, durable stage-once receipt, matching original admitted request and frozen dispatch, native owner/issuer/Host installation and no competing worker.

PR #11 also requires an independently signed **fresh online** monotonic checkpoint (different signing domain), a protected live Host export and original gateway-history grant; an offline signature, a syntactically valid generation ID or a copied ledger is not sufficient. Installation of those providers and independent native re-review remain separate.

**Scope mismatch:** this finite chain does not register Mesa, LLVM, Xvnc, i3, xterm or mesa-demos build tasks. The image-build PR #9 source is later than host-deploy's root-selected `1f07e83d...` and has a *different* source pin. Blindly assigning a new graphical task or swapping the source SHA would violate source and authority selection. No automatic chaining extends to Mesa.

## Source-only negative gate

- `project/graphics-first-workspace/host-deploy-submission-audit.json` freezes host-deploy PR8/PR11 source revisions, exact Git blob SHA-1 identities (which are Git object IDs, **not** rights/authentication signatures), finite task allowlist, source revision, Mesa pin and explicit protected obligations.
- `tools/verify_host_deploy_submission_audit.py` compares its source snapshot with image-build handoff and, in the read-only cross-branch CI lane, fetches the specified *immutable* PR11 host-deploy files, verifies their actual Git blob bytes, parses the finite source constants, checks the gateway's stage-once and fresh external checkpoint calls, and prints **compiler submission DENIED**. It never performs SSM, SQS, EC2, GitHub dispatch or native-signing actions.
- `tests/test_workspace_host_deploy_submission_boundary.py` supplies synthetic negative examples: X11 is missing/unaccepted, a fabricated accepted-looking predecessor receipt, wrong compiler source, stale Mesa revision, an unsupported Xvnc/Mesa task, an omitted checkpoint, and a prematurely marked Ready/Authorized source plan. All must remain NO-GO even when other supplied fields appear valid. Source CI has no ability to mint an accepted-generation record.

### Required successor handoff

Before submitting the *next* legitimate bounded fonts/XCB/X11 producer, host-deploy/host-install must independently authenticate the accepted base and predecessor generation/manifest/receipt, exact selected source and Host identity, signer/authority/checkpoint, protected catalogue/export and one-stage-per-lane policy, then separately approve the actual typed job. Before **Mesa/Xvnc/i3/xterm** can use the same route, a new finite task selection and source/pin compatibility review is required; do **not** graft those onto the three-stage chain automatically.

**Result: source comparison reviewable; graphical compiler submission NOT AUTHORIZED.** Re-open an exact final source HEAD before any protected admission. Real native acceptance and redistribution rights are distinct NO-GO gates.

# First Fonts: GitHub issue-opened → Actions → FIFO gateway

**Source implementation; not a native submission or issuer receipt.**
The original first Fonts request is an issue opened in **`zog144/host-deploy`**,
not `zog144/image-build`. GitHub `issues.opened` only executes a workflow in
the **same repository** as the issue. The image-build PR17 workflow is a
read-only cross-repository source acceptance workflow. The authoritative
trigger already lives on the host-deploy **default branch** at
`.github/workflows/gateway-issue-dispatch.yml`; the reviewed Task C
implementation is selected from
`zog144/host-deploy@cdbf97facb07979d1ad19dcb5791211c90146f5f`.

## Eligible issue

The first Fonts issue uses host-deploy's
`.github/ISSUE_TEMPLATE/first-fonts-gateway.md` and carries only the
schema, existing managed workspace identity, operation `build.submit`,
actual installed lane name and the single task
`graphics-fonts-image-v1`. The authored body **must omit** `source`,
`request_id` and `origin`. The reviewed dispatcher creates these on
`issues.opened`, and only after verifying original repository, issue
number/open state, initiating actor/creator, strict marker and JSON envelope.

The producer commit is always **`image-build@1f07e83dbd80dacb9bed0d6494c697375f0e26cd`**
with the unchanged October monthly pin. The event handler derives the
request's canonical 32-hex identity from the fixed host-deploy repository
and original issue number, so reruns/redelivery cannot choose another
request identity. The event has no authority to select a compiler
generation, accepted receipt, package recipe list, SSM target or AWS role.
Those remain frozen by the installed root-owned Fonts catalogue and
trusted Host gateway.

## Deployment controls — only after native Work admission

A repository administrator configures host-deploy's already reviewed
`ZOG_GATEWAY_DISPATCH_REVISION` to the exact tested Task C commit, never
a branch name, and checks that the default-branch issue workflow includes
the new `ZOG_GATEWAY_FONTS_ENABLED` environment variable. The normal
gateway variables select authorized actors, allowed operations,
`ZOG_GATEWAY_ROLE_ARN`, the approved `us-east-1` FIFO queue URL,
and its account. **Before native admission, leave both
`ZOG_GATEWAY_FONTS_ENABLED` and `ZOG_GATEWAY_SUBMIT_ENABLED` disabled.**
After the native operator has verified the actual installed source,
managed compiler lane, accepted compiler-purpose issuer/receipt,
single-task catalogue/hash receipt, trusted Host/SSM permission,
durable local journal and installed gateway, an administrator may
explicitly enable `build.submit`, the Fonts switch and FIFO forwarding.

The workflow checks `github.run_attempt == 1` and rejects a changed
triggering actor. The pinned Python implementation writes an exclusive,
mode-0600 canonical request file. The submit job revalidates the
original issue event, obtains short-lived GitHub-OIDC AWS credentials,
and makes **one** `SendMessage` call. The FIFO group is the selected
workspace ID; the deduplication ID is the issue-derived request ID.
The boto3 client has `total_max_attempts=1`. A missing acknowledgement
is **not retried automatically**; FIFO's bounded deduplication interval
is not durable idempotency. The trusted Host's existing local journal
and duplicate detection retain the authoritative long-lived send-once
and uncertain-result reconciliation. No direct GitHub-to-SSM path is
created.

## Verification and release ordering

PR17 source CI runs the original source/pin review and exercises the
real PR30 event parser and configured request builder against synthetic
`issues.opened` fixtures. It checks unauthorized or edited events,
source/identity injection, operator opt-ins, exact FIFO bytes,
deduplication and single-send failure handling without AWS credentials,
SQS messages or real GitHub issues. PR30's own CI also exercises the
actual gateway event workflow and tests duplicate/replayed requests.

**This change does not make PR17 an issue-event workflow.** Merging an
image-build issue workflow would listen to the wrong repository and
could bypass the existing gateway. Review and merge the relevant
host-deploy Task C workflow changes to its default branch, then apply
the administrator settings **only after** Work confirms native admission.
The original Fonts catalogue remains a single trusted root-owned
catalogue with its existing hash receipt; no additional signed
approval file, XFS quota or special execution deadline is introduced.

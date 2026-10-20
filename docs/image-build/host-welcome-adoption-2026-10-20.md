# Host-welcome adoption: authoritative image-build progress and graphical software

Date: 2026-10-20

## Producer contracts

Host-welcome may adopt the image-build producer only when deployment pins the exact
reviewed image-build commit supplied with the implementation handoff.

- projection: `image-build-post-install-progress-v2`
- local wire: `image-build-post-install-progress-rpc-v2`
- producer source binding: `image-build-post-install-source-v1`
- intent owner: `host-install`
- publication: `image-build-post-install-publication-v2`
- application artifacts: `applications-v1`
- views: `application-software-view-v1`
- consumer binding: `application-software-consumer-v1`

The fixed systemd deployment owns state path, application allowlist, source
repository/revision and numeric host-welcome UID. The broker uses `SO_PEERCRED`
before parsing a request and supports only bounded read-only snapshots.

Host-welcome should reject a snapshot whose source commit is not the deployed reviewed
pin, whose producer boot is not acceptable for the current observation, or whose
`observed_at` is outside its reviewed freshness window. Per-command terminal evidence
has its own controller observation time/boot and may legitimately predate a reboot.

## Claim boundaries

Request intent, command execution, immutable artifact publication, view publication,
selected-rootfs compatibility and runtime admission are independent facts. In
particular:

- command success never means software published;
- publication never means box-control admitted or mounted it;
- runtime observation never means graphical rendering or a usable local seat;
- greetd compilation/publication never grants a privileged PAM/logind role.

The six sanitized fixtures under
`examples/host-welcome/post-install-progress-v2/` are consumer/schema examples
only. They must never be presented as live installation evidence.

## Graphical software status

The machine-readable source/admission plan is
`project/bootstrap/graphical-applications-first.py` under
`image-build-graphical-application-plan-v1`.

First group: agreety, greetd, Xorg server, i3, Firefox ESR.
Later group: TurboVNC, VirtualGL; Chromium remains research-required; optional
Wayland compositor and graphical greeter remain unselected.

No first/later-group application in this checkpoint has a verified native
`applications-v1` artifact or `application-software-view-v1` ID. Empty ID arrays
are intentional and must not be replaced with source/package hashes.

## Native acceptance still required

Host-deploy Work plus host-install/box-control/root-control must separately demonstrate:

1. compiler-host builds from the exact pinned graphical sources/notices;
2. runtime library/ABI closure and reproducibility evidence;
3. immutable artifact/view publication and rollback;
4. Xvfb attachment/admission;
5. real local X11/seat input/display acceptance;
6. Firefox kiosk readiness;
7. PAM/logind/root-control review before any privileged greetd execution.

Host-welcome must preserve console/getty operation when any optional producer or
graphical gate is unavailable.

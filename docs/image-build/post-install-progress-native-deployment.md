# Native host-welcome image-build progress observer reference

**Status:** producer source contract implemented; native deployment acceptance remains
NO-GO until host-install stages the role and Work completes disposable-host
systemd/DAC/SELinux/reboot/getty acceptance.

This document implements the image-build side of the 2026-10-20 host-welcome
handoff. It deliberately does **not** install accounts, write `/etc`, enable
systemd units or authorize production activation.

## Reviewed producer implementation

The consumer-reviewed progress implementation remains:

- repository: `zog144/image-build`
- source revision: `fcc12f3db959afe395b1adfb5b0b4dc1f16a3258`
- projection: `image-build-post-install-progress-v2`
- wire: `image-build-post-install-progress-rpc-v2`
- source binding: `image-build-post-install-source-v1`

The broker, projection and all security-critical modules used by the snapshot path
are byte-identical between that reviewed revision and the image-build source that
introduced this deployment reference. The reference inventory pins 13 Git blob
identities and computes independent SHA-256 values when host-install reviews a
source checkout.

The source binding names the reviewed projection implementation. It does not claim
that every file in a later aggregate `zog` wheel came from that old commit.
Host-install must separately attest the actual interpreter, loaded modules and
wheel RECORD before enabling the socket.

## Fixed role

Producer-owned constants live in
`zog.image_build.post_install_progress_deployment`.

The exact consumer-visible policy remains:

`/etc/zog/host-welcome-image-progress-observer.json`

with schema `zog-host-welcome-image-progress-observer-v1` and exactly:

- `enabled=true`;
- independently resolved numeric `consumer_uid`;
- independently resolved distinct numeric `producer_uid`;
- `socket=/run/host-welcome/image-progress.sock`;
- `image_build_source_commit=fcc12f3db959afe395b1adfb5b0b4dc1f16a3258`.

The first-wave immutable graphical allowlist is exactly:

- `agreety`;
- `firefox-esr`;
- `greetd`;
- `i3`;
- `xorg-server`.

TurboVNC, Chromium and Weston/Wayland are intentionally not admitted by this
version. Their source/build/runtime acceptance remains separate.

## Reference systemd pair

Reference templates are:

- `examples/systemd/zog-host-welcome-image-progress.socket.in`;
- `examples/systemd/zog-host-welcome-image-progress.service.in`.

Host-install may package these only after checking them byte-for-byte against the
reviewed image-build source revision that supplies the deployment contract.

The socket is dedicated to host-welcome:

- one `AF_UNIX` listener at `/run/host-welcome/image-progress.sock`;
- `SocketUser=<resolved host-welcome UID>`;
- mode 0600;
- parent directory mode 0711;
- `Accept=no`, bounded backlog, removal on stop.

The service runs as the separately resolved image-build producer UID/GID and invokes
only `zog.image_build.post_install_progress_broker`. The state directory,
authorized consumer UID, application allowlist, repository and source revision are
fixed in the root-rendered unit. No request can select a state path, source,
application, pipeline, job or mutation operation.

The reference service clears inherited `PYTHONPATH`, restricts networking to
`AF_UNIX`, drops capabilities, enables no-new-privileges and makes the selected
image-build state path read-only in the service mount namespace. It has no
station-access socket, controller-progress socket or root-control socket.

## Root-owned staging requirements

host-install remains responsible for all privileged facts and writes. It must:

1. resolve the real dedicated host-welcome UID from the host account database;
2. resolve a distinct real image-build producer UID/GID from protected image-build
   ownership facts, not command-line fixture numbers;
3. resolve one canonical protected image-build state root and reject symlinked,
   group/world-writable or ownership-conflicting ancestry;
4. verify the reviewed source inventory before using the reference templates;
5. render and stage the exact root-owned policy/unit overlay without enabling it;
6. attest the approved interpreter, actual loaded image-build modules and aggregate
   wheel RECORD against the reviewed blob inventory, with no inherited
   `PYTHONPATH` or writable import root;
7. retain `production_activation_authorized=false` until native Work acceptance.

The consumer UID must not receive raw image-build state access. The producer service
gets only the read-only state path needed for the projection.

## Boot and recovery semantics

The live broker obtains the current Linux boot ID from
`/proc/sys/kernel/random/boot_id` at startup and includes it in every snapshot.
The durable image-build evidence may legitimately retain a controller terminal
observation from an older boot; that does not turn old process state into current
execution. Host-welcome independently applies freshness/current-boot policy.

The observer is optional. Network, station-access, image-build progress, graphics
and this socket must not become prerequisites for console/getty boot. Failure to
start or authenticate this role means image-build publication is unobserved; it
must never cause an automatic submit, resume, cancel, publication, service start or
graphical transition.

## Native acceptance still required

A disposable host must still prove:

- actual resolved UIDs/GIDs and no unintended supplementary access;
- protected socket parent/inode/mode plus host SELinux/LSM labeling;
- authorized observer success;
- wrong-UID denial both by DAC and broker `SO_PEERCRED`;
- exact producer peer UID seen by host-welcome;
- source-pin and stale/wrong-boot replay rejection;
- service activation/restart/reboot cleanup;
- read-only state mount and inability to mutate build state;
- failure/cancellation/interruption/reboot/mismatched-generation/absent-publication
  truthfulness;
- station/controller observer separation;
- offline first boot/getty usability with the observer absent;
- cleanup/disposal of the test host.

Passing source CI is not native deployment acceptance and does not authorize
production enablement.

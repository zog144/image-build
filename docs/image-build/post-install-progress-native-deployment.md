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
- source revision: `fe625fd901a62ef3c877a8fbc159e3b4aae7f952`
- projection: `image-build-post-install-progress-v2`
- wire: `image-build-post-install-progress-rpc-v2`
- source binding: `image-build-post-install-source-v1`
- transport authentication: `image-build-post-install-progress-linux-credentials-v1`

The reviewed runtime revision includes the socket-activation correction, the Gate C
receipt-only publication correction, and the October 24 cold-start correction. The
broker still attaches kernel-validated Linux `SCM_CREDENTIALS` to each reply and
contains disconnected client writes per connection. Broker construction now
validates only the fixed application/source/boot configuration and performs **no**
durable publication snapshot. The first consumer request performs one full
publication/artifact/view/rootfs verification, and every later request performs a
fresh full verification again; no provenance result is cached across requests.
This removes the duplicate cold-start observation without increasing the consumer
deadline or weakening fail-closed evidence checks.

The progress projection continues to reverify a matching publication receipt even
when no matching post-install pipeline exists; it leaves pipeline/command
identities absent and never infers build success or runtime admission from
publication. The reference inventory pins all 13 exact Git blob identities and
computes independent SHA-256 values when host-install reviews a source checkout.

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
- `image_build_source_commit=7b653e8be3f89730a52688d71df28513456f9cf3`.

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
only `zog.image_build.post_install_progress_broker`. systemd may create the
listening socket as PID 1/root; clients therefore MUST NOT use listener
`SO_PEERCRED` as producer authentication. The broker authenticates the client on
the accepted connection with `SO_PEERCRED` before parsing, then sends the first
byte of every reply with an `SCM_CREDENTIALS` ancillary record containing the
actual broker PID/UID/GID. A host-welcome consumer must enable Linux
`SO_PASSCRED`, receive the reply header with `recvmsg`, require exactly one
kernel credential record matching the protected policy producer UID, and only then
decode the frame body.

The state directory,
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
- exact producer reply UID seen by host-welcome through `SCM_CREDENTIALS`
  (listener `SO_PEERCRED` is expected to be PID 1/root under socket activation);
- authorized disconnect before request framing and during reply completion does not
  terminate/restart the broker, and a subsequent client is served by the same process;
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


## Gate C receipt-only publication semantics

A current host-install selection can legitimately reference an image-build
artifact/view that was produced by a finite controller path rather than a retained
post-install pipeline. In that case the read-only projection independently checks
the publication receipt, immutable artifact/view, exact selected rootfs generation,
compatibility descriptor and consumer binding.

When no matching pipeline exists:

- missing publication remains `waiting / intent-awaiting-pipeline`;
- corrupt, selection-mismatched, operation-mismatched, or incompatible publication
  evidence is `unknown / publication-evidence-conflict`;
- a verified artifact/view publication reports its publication state/message at
  top level with `phase=publishing`;
- `pipeline_id`, `pipeline_state`, `source_pin_identity` and `commands`
  remain absent/empty;
- `runtime_admission` remains `unobserved`.

If conflicting pipeline history does exist, the top-level pipeline conflict remains
visible even when the independent publication object itself verifies successfully.

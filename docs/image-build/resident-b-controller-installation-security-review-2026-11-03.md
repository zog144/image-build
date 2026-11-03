# Resident B controller privileged installation source review — November 3, 2026

This source-only review is stacked on image-build PR #14, itself stacked on Resident B PR #12. All source archive pins, package revisions, original notices, wheel-output records, and Boot A contracts remain unchanged. No selected generation, native build, service activation, STATE or live socket touched.

## Selected packaging and identity

* `box-control@b513a9bde79135c7569adc7cadb4d45a163c7841` declares `box-control = zog.box_control.cli:main`. Its selected source only performs `BoxControl.discover().evaluate()` as a **one-shot** evaluator. The recipe must not add a root service, singleton machine-wide project, or root socket group. A protected installer must later choose a real non-root project owner, independently authorized HOME/project and narrow socket access.
* `root-control@0c217182d25f05b9cc0f7528ee614bb5669370d3` declares `root-control = zog.root_control.daemon:main`, a root-owned **persistent** Unix-socket daemon. Its selected Python source gives `DEFAULT_SOCKET=Path("/run/zog/root-control.sock")`, explicitly `chmod(0660)`, and changes the socket GID only if a positive numeric `ROOT_CONTROL_SOCKET_GID` was *independently* provided. Its source image does not populate this variable or install such group membership.

The exact root unit is generated under `usr/lib/systemd/system/zog-root-control.service` by the held package stage, with `Type=exec`, `User=root`, `Group=root`, `ExecStart=/usr/bin/root-control`, `RuntimeDirectory=zog`, `RuntimeDirectoryMode=0755`, `UMask=0007`, `Restart=no`, and `Environment=ROOT_CONTROL_JOURNAL_BARRIER=0`. It requires a mounted `/state` and has **no activation section**. Static validation now parses and compares each service directive rather than accepting fragments somewhere inside the install script. In particular, a service drop-in, group setting, alternative executable, startup command, or `WantedBy` would require a new review.

## Two security boundaries intentionally *not* established by source recipes

1. `ConditionPathIsMountPoint=/state` + `RequiresMountsFor=/state` prevent starting without a mounted path, but **do not authenticate the correct installation, underlying device, STATE partition identity, original protected authority, or data integrity**. That requires a separately installed, independently authenticated host-install native receipt and boot/reboot observation. Do not infer it from systemd unit parsing.
2. Root-control's socket is a high-privilege mechanism endpoint. `0660` and root-owned `RuntimeDirectory` only become a safe non-root grant after an exact installer-selected, root-protected numeric GID and trusted membership. The image leaves the group absent (root group default). This review cannot grant access, and source verification must not fabricate the group/STATE/identity.

## Required source-only negative coverage

Tests reject substituted service user/group, `DynamicUser`/startup type/exec path changes, writable runtime directory, weak umask, missing STATE mount guard, auto-enable/install sections, added environmental group grants, unexpected `EnvironmentFile`, missing `python-resident312-final`, `resident312-dbus-next-final`, `resident312-image-build-final`, `box-control-final` or `systemd-final` runtime edges, wrong `/usr/bin` placement, and unintended privileged box-control service or shared `/state` project.

CI checks the actual upstream root daemon/box CLI and pyproject files at exact original revisions, **without importing or running them**. The original Resident B audit and wheel/RECORD negative suite are retained. Native outcome remains **NO-GO**, and the draft is not a boot/installation authorization.

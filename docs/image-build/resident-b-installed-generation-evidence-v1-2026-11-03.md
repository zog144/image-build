# Resident B installed-generation evidence v1 — source acceptance interface

**2026-11-03 · image-build PR #15 · source review, never native admission**

The read-only `tools/verify_resident_b_installed_evidence.py` defines a strict, exact-input verifier for **future** independently produced Resident B installation evidence. It runs against a caller-supplied mounted/extracted root directory, never executes installed programs or controllers, accesses real STATE, mounts partitions, selects a generation, or enables systemd. A synthetic CI fixture cannot be interpreted as a production installation receipt.

## Trust separation

Three independently provided inputs are required:

1. A trusted **upstream generation-selection signature**, `zog-resident-b-selected-input-generation-v1`, from a separately pinned generation authority. The selection must bind the exact generation ID and original source generation receipt SHA-256, declare `selection_status=accepted-as-input`, and explicitly deny native boot/service activation. It cannot be signed by the same key used for installed-byte observations.
2. A separately signed `zog-resident-b-installed-generation-evidence-v1` observation binding that generation and original source receipt, exact STATE identity, required output inventory with size/mode/SHA256, Python 3.12 ABI, external mount/slot observations and protected service/socket permissions. Every observed byte is checked against the read-only root directory, not accepted because an observation says `success`.
3. The verifier caller supplies the exact expected generation ID, STATE identity and independently selected trusted public keys, **outside** the untrusted evidence object. Mismatch or missing signatures hard-fail. This verifier does not supply/trust the keys or the generation itself.

The source review's immutable controller pins are box-control `b513a9bde79135c7569adc7cadb4d45a163c7841` and root-control `0c217182d25f05b9cc0f7528ee614bb5669370d3`; required paths derive from `project/host/resident-b-pr14-pr15-combined-source-review.json` and the exact source recipes. Foreign host compiler or Python ABI fallback is not evidence.

## Byte/permission checks

- Every declared controller source-output file must exist as a single-link, non-symlink regular file with a matching exact byte digest, size, ownership-independent mode and unique path. Required console scripts must have a Python **3.12** interpreter and executable mode 0755.
- Both `box_control-0.1.0.dist-info/RECORD` and `root_control-0.1.0.dist-info/RECORD` must match independently supplied record digests, exact member lists, per-member SHA-256 and sizes. `METADATA` and `RECORD` must be represented; extra/duplicate/unhashed members are denied.
- `_ssl`, `_sqlite3` and `_hashlib` must exist within the Python 3.12 `lib-dynload` directory and identify as x86-64 ELF64 little-endian dynamic/shared modules. This is **not yet** a full loader/dependency-closure or CA trust validation; those require native runtime evidence and linker observation.
- Root-control systemd service must be mode 0644, explicitly `User=root`/`Group=root`, depend on `/state` and have **no** `[Install]` auto-enable section. The external signed observation must include verified read-only rootfs slot, exact STATE mount ID, root-owned protected STATE, socket mode 0660 with provisioned protected group, and explicitly disabled service.
- Only `status=observed` and `accepted=false` are supported for native installed-byte observations; any fabricated `accepted`, self-signed generation selection, unreviewed output, wrong interpreter, insufficient receipt, or mismatched byte/permission fails closed.

The verifier returns `EVIDENCE_COHERENT_UNACCEPTED`, `accepted_generation=null`, `native_install_authorized=false` and `service_activation_authorized=false` on a *consistent* synthetic/native observation. It is **not** a source of authority and cannot decide whether the independently accepted generation is bootable.

## Native evidence still needed

An independent native runner must obtain authenticated installed-wheel/RECORD and actual ELF `DT_NEEDED` / linker-origin closure, sealed interpreter `ssl`/`sqlite3` imports, OpenSSL and SQLite version/source selection, CA bundle, actual service/socket owner/group and `STATE` device identity, generation selection receipts and reboot observations. The current verifier checks receipt-shaped mount/service claims under independent witness signatures, but does not attest the kernel mount table or invoke a service. Rights/notice authorization and no-host-fallback need separate independent evidence. Future native acceptance must be explicitly approved by the owning boot/Host programs; no compiler submission, native filesystem mutation, root-control service activation, AWS or Boot A upgrade is allowed here.

**Status:** source-verifier and synthetic corruption tests PASS; resident generation NOT SELECTED / native NO-GO.

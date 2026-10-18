# Data only; planning contract, not an executable recipe.
{
  "schema": 1,
  "source_version": "0.10.3",
  "cargo_lock": "upstream Cargo.lock",
  "cargo_source_closure": "cargo-sources.py",
  "build_strategy": "cargo --locked --offline after exact crate staging",
  "outputs": [
    "greetd",
    "agreety"
  ],
  "publication": "separate applications-v1 artifacts/views",
  "activation": "not-authorized",
  "blockers": [
    "per-crate-license-and-notice-review",
    "rootfs-pam-abi-selection",
    "controller-owned-greetd-privileged-role-review",
    "native-build-and-elf-closure-acceptance"
  ],
  "notes": [
    "The complete crates.io source closure is frozen before any native build.",
    "This plan does not authorize networked cargo resolution, PAM login, VT/seat ownership, or privileged greetd execution.",
    "greetd and agreety share source inputs but must publish as distinct immutable artifacts/views."
  ]
}

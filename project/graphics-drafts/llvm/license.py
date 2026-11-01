# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "llvm",
  "version": "21.1.6",
  "source": {
    "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-21.1.6/llvm-21.1.6.src.tar.xz",
    "sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
  },
  "status": "unresolved",
  "expression": "Apache-2.0 WITH LLVM-exception",
  "evidence": [
    {
      "path": "llvm-21.1.6.src/LICENSE.TXT",
      "sha256": "8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee",
      "source_sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
    },
    {
      "path": "llvm-21.1.6.src/include/llvm/Support/LICENSE.TXT",
      "sha256": "54cbc326a78b9400065bfc5830a57fdcdaf808286d4ac35d8a9e324aa77b7241",
      "source_sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
    },
    {
      "path": "llvm-21.1.6.src/lib/Support/BLAKE3/LICENSE",
      "sha256": "6a94bedb8b707ed97f6e310d0d015ab14e0683ffa0a612b02958581b9cc9fc0e",
      "source_sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
    },
    {
      "path": "llvm-21.1.6.src/test/YAMLParser/LICENSE.txt",
      "sha256": "d0d8b09800a45cd982e9568fc7669d9c1a4c330e275a821bbe24d54366d16fe9",
      "source_sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
    },
    {
      "path": "llvm-21.1.6.src/utils/lit/LICENSE.TXT",
      "sha256": "8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee",
      "source_sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
    }
  ],
  "components": [
    {
      "scope": "Source/bundled components",
      "expression": None,
      "status": "unresolved",
      "notes": "Original archive bytes verified; independent component copyright and distribution-rights review remains required."
    }
  ],
  "patches": [],
  "notes": [
    "Do not publish or redistribute until extracted source notices and complete file-level rights are reviewed.",
    "Source archive exact digest and selected original-member hashes verified by GitHub Actions run 41310820294; independent legal/feature-scoped component rights remain unresolved.",
    "Selected upstream rights members: LICENSE.TXT, include/llvm/Support/LICENSE.TXT, lib/Support/BLAKE3/LICENSE, test/YAMLParser/LICENSE.txt, utils/lit/LICENSE.TXT. Previous review-evidence status: archive-member-hashes-verified-rights-review-pending."
  ],
  "scope": "Exact llvm source/member SHA-256 evidence only; complete component rights/public redistribution review not approved"
}

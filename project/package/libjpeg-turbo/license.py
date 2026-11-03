# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "libjpeg-turbo",
  "version": "3.2.0",
  "source": {
    "url": "https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.2.0/libjpeg-turbo-3.2.0.tar.gz",
    "sha256": "6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e"
  },
  "status": "declared",
  "expression": "LicenseRef-libjpeg-turbo-Unreviewed-Original-Notice",
  "scope": "Original source notice members verified; per-file/bundled rights and redistribution approval remain unresolved.",
  "evidence": [
    {
      "path": "libjpeg-turbo-3.2.0/LICENSE.md",
      "sha256": "ba6bceebcba0fdd35488477c2cca8c4632ce82c74dbfbc87d886ce6fc4433579",
      "source_sha256": "6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e"
    }
  ],
  "components": [
    {
      "scope": "Selected bundled and generated code, release notices and actual linked inputs",
      "expression": None,
      "status": "unresolved",
      "notes": "Review all applicable notices in actual source graph before distribution."
    }
  ],
  "patches": [],
  "notes": [
    "Not native compiled. libjpeg-turbo SIMD disabled to avoid unreviewed NASM/Yasm and device-specific paths. Independent JPEG regression testing remains a native gate."
  ]
}

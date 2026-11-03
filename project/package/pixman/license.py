# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "pixman",
  "version": "0.46.4",
  "source": {
    "url": "https://cairographics.org/releases/pixman-0.46.4.tar.xz",
    "sha256": "a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239"
  },
  "status": "declared",
  "expression": "LicenseRef-pixman-Unreviewed-Original-Notice",
  "scope": "Original source notice members verified; per-file/bundled rights and redistribution approval remain unresolved.",
  "evidence": [
    {
      "path": "pixman-0.46.4/COPYING",
      "sha256": "fac9270f0987b96ff4533fca3548c633e02083cbba4a0172a3b149b2e4019793",
      "source_sha256": "a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239"
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

# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "turbovnc",
  "version": "3.3.1",
  "source": {
    "url": "https://github.com/TurboVNC/turbovnc/releases/download/3.3.1/turbovnc-3.3.1.tar.gz",
    "sha256": "9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"
  },
  "status": "unresolved",
  "expression": "LicenseRef-TurboVNC-Composite-Original-Scope-Unreviewed",
  "scope": "Original license and selected nested source bytes verified, but source inclusion/redistribution not independently approved.",
  "evidence": [
    {
      "path": "turbovnc-3.3.1/LICENSE.txt",
      "sha256": "8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643",
      "source_sha256": "9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"
    },
    {
      "path": "turbovnc-3.3.1/unix/Xvnc/programs/Xserver/COPYING",
      "sha256": "4cc0447a22635c7b2f1a93fec4aa94f1970fadeb72a063de006b51cf4963a06f",
      "source_sha256": "9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"
    },
    {
      "path": "turbovnc-3.3.1/unix/Xvnc/lib/libsha1/COPYING",
      "sha256": "4c387926596bfeacc5b72ebeb96ab36c299a07568e18592c727a6c11dd512c20",
      "source_sha256": "9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"
    },
    {
      "path": "turbovnc-3.3.1/unix/Xvnc/lib/zlib-ng/LICENSE.md",
      "sha256": "6c9f0d975b41afaa34d22f55bb8986ce69e5cb7ad327cb2b28820cd425edf5ee",
      "source_sha256": "9be0a0764d89f1a234cad7775ea142a01c0efe198523456899883bd6466691da"
    }
  ],
  "components": [
    {
      "scope": "Bundled Xserver and vendor Xorg code",
      "status": "unresolved",
      "expression": None,
      "notes": "Review every actually selected source, generated file, drivers/protocols and notices."
    },
    {
      "scope": "Bundled libsha1",
      "status": "unresolved",
      "expression": None,
      "notes": "Match source-object provenance to original copying and notices."
    },
    {
      "scope": "Bundled zlib-ng",
      "status": "unresolved",
      "expression": None,
      "notes": "Selected TVNC_ZLIBNG=OFF but must prove its objects absent; retain original notice evidence."
    }
  ],
  "patches": [],
  "notes": [
    "No native Xvnc, executable linker, server extension or redistribution approval observed."
  ]
}

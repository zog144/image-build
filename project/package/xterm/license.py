# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "xterm",
  "version": "412",
  "source": {
    "url": "https://invisible-island.net/archives/xterm/xterm-412.tgz",
    "sha256": "b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6"
  },
  "status": "declared",
  "expression": "LicenseRef-Xterm-412-Original-COPYING-Unreviewed",
  "scope": "Source-pinned notice evidence only; final redistribution approval and actual selected binary inventory pending The LicenseRef is a temporary identifier, not a redistribution grant.",
  "evidence": [
    {
      "path": "xterm-412/COPYING",
      "sha256": "f272fa007de2cffdb22b4df09e9a3aaec3555d5a6913229b70006ee137ab22b5",
      "source_sha256": "b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6"
    },
    {
      "path": "xterm-412/MANIFEST",
      "sha256": "378b17ae42a63d26e8c05e4af64f93faa68b80fc8c52ce3bc27ae913647aeafd",
      "source_sha256": "b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6"
    },
    {
      "path": "xterm-412/configure",
      "sha256": "83a7d727dfad2172e9c49c91374871ac5111e88fa08c4f2def5b872455914ba2",
      "source_sha256": "b48bc780c1cbc14f6d89269f7e593712af6095876960d650be28b55e5dad65a6"
    }
  ],
  "components": [
    {
      "scope": "xterm embedded generated parser, terminal tables, any notices in auxiliary libraries",
      "expression": None,
      "status": "unresolved",
      "notes": "Per-file inclusion review needed after native build graph."
    }
  ],
  "patches": [],
  "notes": [
    "Original xterm 412 archive checked in GitHub Actions 41457682657; none of these metadata fields imply a build or rights approval."
  ]
}

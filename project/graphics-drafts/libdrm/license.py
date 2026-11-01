# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "libdrm",
  "version": "2.4.128",
  "source": {
    "url": "https://dri.freedesktop.org/libdrm/libdrm-2.4.128.tar.xz",
    "sha256": "3bb35db8700c2a0b569f2c6729a53f5495786856b310854c8de57782a22bddac"
  },
  "status": "archive-member-hashes-verified-rights-review-pending",
  "expression": "MIT",
  "required_original_notice_paths": [
    "xf86drm.c",
    "xf86drm.h"
  ],
  "evidence": [
    {
      "path": "libdrm-2.4.128/xf86drm.c",
      "sha256": "676845942ab8b9bc5759b295528fce0f32b28ca7765c17d4546e253caaba62c4",
      "source_sha256": "3bb35db8700c2a0b569f2c6729a53f5495786856b310854c8de57782a22bddac"
    },
    {
      "path": "libdrm-2.4.128/xf86drm.h",
      "sha256": "5fad86acbddcc3b6a685690da0c7de59412d354d1375644734672f5c6bdf4202",
      "source_sha256": "3bb35db8700c2a0b569f2c6729a53f5495786856b310854c8de57782a22bddac"
    }
  ],
  "components": [
    {
      "scope": "Archive and drivers",
      "expression": None,
      "status": "unresolved"
    }
  ],
  "patches": [],
  "notes": [
    "Checksum from upstream 2.4.128 release announcement; source-header notice SHA256 pending.",
    "Source archive exact digest and selected original-member hashes verified by GitHub Actions run 41310820294; independent legal/feature-scoped component rights remain unresolved."
  ]
}

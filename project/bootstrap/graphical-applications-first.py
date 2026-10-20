# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "contract": "image-build-graphical-application-plan-v1",
  "artifact_contract": "applications-v1",
  "view_contract": "application-software-view-v1",
  "consumer_contract": "application-software-consumer-v1",
  "first_group": [
    {
      "id": "agreety-text-greeter",
      "application": "agreety",
      "catalogue_package": "agreety",
      "depends_on": [],
      "source_status": "cargo-source-closure-frozen",
      "build_status": "source-only",
      "publication": "separate-artifact-and-view",
      "privileged_role": False,
      "blockers": [
        "per-crate-license-and-notice-review",
        "offline-cargo-recipe-not-yet-authored",
        "native-runtime-abi-acceptance"
      ],
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "id": "greetd-login-daemon",
      "application": "greetd",
      "catalogue_package": "greetd",
      "depends_on": ["agreety"],
      "source_status": "cargo-source-closure-frozen",
      "build_status": "source-only",
      "publication": "separate-artifact-and-view",
      "privileged_role": True,
      "blockers": [
        "per-crate-license-and-notice-review",
        "offline-cargo-recipe-not-yet-authored",
        "pam-logind-native-abi-acceptance",
        "controller-root-control-privileged-role-review"
      ],
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "id": "xorg-server",
      "application": "xorg-server",
      "catalogue_package": "xorg-server",
      "depends_on": [],
      "source_status": "source-pinned",
      "build_status": "dependency-closure-incomplete",
      "publication": "separate-artifact-and-view",
      "privileged_role": False,
      "blockers": [
        "xorg-server-native-dependency-closure-incomplete",
        "source-license-notice-review-incomplete",
        "xvfb-acceptance-not-run",
        "physical-seat-acceptance-not-run"
      ],
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "id": "i3-minimal-desktop",
      "application": "i3",
      "catalogue_package": "i3",
      "depends_on": ["xorg-server"],
      "source_status": "source-pinned",
      "build_status": "dependency-closure-incomplete",
      "publication": "separate-artifact-and-view",
      "privileged_role": False,
      "blockers": [
        "pango-cairo-xkbcommon-xcb-cursor-closure-incomplete",
        "source-license-notice-review-incomplete",
        "xvfb-window-manager-acceptance-not-run"
      ],
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "id": "firefox-kiosk",
      "application": "firefox-esr",
      "catalogue_package": "firefox-esr",
      "depends_on": ["xorg-server"],
      "source_status": "source-pinned",
      "build_status": "dependency-closure-incomplete",
      "publication": "separate-artifact-and-view",
      "privileged_role": False,
      "blockers": [
        "gtk-nss-nspr-media-native-closure-incomplete",
        "bundled-third-party-license-review-incomplete",
        "reproducible-build-profile-not-frozen",
        "xvfb-kiosk-acceptance-not-run",
        "physical-seat-kiosk-acceptance-not-run"
      ],
      "verified_artifact_ids": [],
      "verified_view_ids": []
    }
  ],
  "prepared_foundation_batches": [
    "graphics-fonts",
    "graphics-xcb",
    "graphics-x11-core",
    "graphics-x11-session",
    "graphics-xcb-i3-support"
  ],
  "later_group": [
    {
      "application": "turbovnc",
      "catalogue_package": "turbovnc",
      "source_status": "source-pinned",
      "build_status": "dependency-closure-incomplete",
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "application": "virtualgl",
      "catalogue_package": "virtualgl",
      "source_status": "source-pinned",
      "build_status": "dependency-closure-incomplete",
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "application": "chromium",
      "catalogue_package": None,
      "source_status": "research-required",
      "build_status": "not-pinned",
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "application": "wayland-compositor",
      "catalogue_package": None,
      "source_status": "optional-unselected",
      "build_status": "not-pinned",
      "verified_artifact_ids": [],
      "verified_view_ids": []
    },
    {
      "application": "graphical-greeter",
      "catalogue_package": None,
      "source_status": "optional-unselected",
      "build_status": "not-pinned",
      "verified_artifact_ids": [],
      "verified_view_ids": []
    }
  ],
  "acceptance_order": [
    "source-and-notice-review",
    "package-build-and-tests",
    "applications-v1-publication",
    "application-software-view-v1-publication",
    "selected-rootfs-compatibility",
    "protected-box-control-admission",
    "xvfb",
    "physical-seat",
    "privileged-pam-logind-if-applicable"
  ]
}

# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "architecture": "x86_64",
  "stages": [
    {
      "id": "xcb-util-final",
      "project": "xcb-util",
      "stage": "final",
      "recipe": "xcb-util/stages/final"
    },
    {
      "id": "libev-final",
      "project": "libev",
      "stage": "final",
      "recipe": "libev/stages/final"
    },
    {
      "id": "yajl-final",
      "project": "yajl",
      "stage": "final",
      "recipe": "yajl/stages/final"
    },
    {
      "id": "startup-notification-final",
      "project": "startup-notification",
      "stage": "final",
      "recipe": "startup-notification/stages/final"
    },
    {
      "id": "xkeyboard-config-final",
      "project": "xkeyboard-config",
      "stage": "final",
      "recipe": "xkeyboard-config/stages/final"
    },
    {
      "id": "libxkbcommon-final",
      "project": "libxkbcommon",
      "stage": "final",
      "recipe": "libxkbcommon/stages/final"
    }
  ],
  "targets": [
    "libev-final",
    "yajl-final",
    "startup-notification-final",
    "xkeyboard-config-final",
    "libxkbcommon-final"
  ]
}

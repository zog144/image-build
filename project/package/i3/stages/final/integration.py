# Data only; parsed with ast.literal_eval.
{
  "project": "i3",
  "stage_id": "final",
  "version": "4.25.1",
  "native_admission": "HOLD: actual selected Meson pkgconf/headers/generated code/ELF and independent rights",
  "base_contract": "Original i3 4.25.1 Meson source, Zog-only immutable predecessor generation and pinned build tools; no Host headers, Python modules, X11 socket or font fallback.",
  "required_pkgconfig": [
    "libstartup-notification-1.0",
    "xcb",
    "xcb-xkb",
    "xcb-xinerama",
    "xcb-randr",
    "xcb-shape",
    "xcb-util",
    "xcb-cursor",
    "xcb-keysyms",
    "xcb-icccm",
    "xcb-xrm",
    "xkbcommon",
    "xkbcommon-x11",
    "yajl",
    "libpcre2-8",
    "cairo",
    "pangocairo",
    "glib-2.0",
    "gobject-2.0"
  ],
  "generated_source": [
    "build-i3/config.h",
    "build-i3/meson-info/intro-dependencies.json"
  ],
  "native_evidence": "Not captured; all output paths are expected-not-observed.",
  "patches": [],
  "patches_complete": True,
  "test_scope": "Source and dependency contract only."
}

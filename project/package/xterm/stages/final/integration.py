# Data only; parsed with ast.literal_eval.
{
  "project": "xterm",
  "stage_id": "final",
  "version": "412",
  "native_admission": "HOLD: sources/termcap/Xaw/Xft/luit/font closure and protected compiler required",
  "base_contract": "Source-verified xterm 412, but only inherited accepted Zog X11 libraries, ncurses, terminfo, luit and installed basic font; Host includes and fonts forbidden.",
  "selected_build_flags": [
    "--with-app-defaults=/usr/share/X11/app-defaults",
    "--disable-setuid",
    "--disable-setgid",
    "--enable-256-color"
  ],
  "dependency_review": {
    "source_inspection": "GitHub Actions 41499335984; original configure and install-ti target found",
    "missing_source": [
      "libXaw",
      "libXmu",
      "libXpm",
      "libXft",
      "luit",
      "basic-font"
    ],
    "runtime_resources": [
      "XTerm",
      "xterm terminfo entry",
      "X11 font path",
      "luit executable"
    ]
  },
  "test_scope": "No native compilation, terminfo ownership, environment isolation, rights/redistribution or Workspace launch verified."
}

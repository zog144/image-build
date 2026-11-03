# Data only; parsed with ast.literal_eval.
{
  "configure": [],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -f upstream/font-misc-misc-1.1.3/6x13.bdf\nmkdir -p build-basic-font\nbdftopcf -o build-basic-font/6x13.pcf upstream/font-misc-misc-1.1.3/6x13.bdf\ngzip -n -9 -c build-basic-font/6x13.pcf > build-basic-font/6x13.pcf.gz\nmkfontscale -b -s -o build-basic-font/fonts.dir build-basic-font"
    ]
  ],
  "test": [],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"\ninstall -Dm644 build-basic-font/6x13.pcf.gz \"$DESTDIR/usr/share/fonts/X11/misc/6x13.pcf.gz\"\ninstall -Dm644 build-basic-font/fonts.dir \"$DESTDIR/usr/share/fonts/X11/misc/fonts.dir\"\ninstall -Dm644 upstream/font-misc-misc-1.1.3/COPYING \"$DESTDIR/usr/share/licenses/basic-font/COPYING\""
    ]
  ]
}

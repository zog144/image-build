# Graphics RPM/upstream review matrix

This is maintained recipe evidence, not an execution log. The source versions are the
versions selected by Zog's October 2026 monthly pin. Fedora Rawhide specs were fetched
in full on 2026-10-10 and their exact `rawhide` revisions were recorded with
`git ls-remote`. The reproducible research job also attempted the corresponding
openSUSE Factory source API paths; every direct Factory source request returned HTTP
401. Where a public OBS package/spec was discoverable, it is noted as fallback
packaging evidence. Otherwise Fedora plus exact upstream/BLFS metadata is the recorded
maintained RPM/upstream fallback. No unavailable openSUSE review is marked complete.

| Zog source | Selected version | Fedora Rawhide spec evidence | openSUSE evidence / exception | Requirements and Zog decision |
|---|---:|---|---|---|
| libpng | 1.6.58 | `libpng.spec` @ `189b72618658df96aff1c66d3c746dc0d4818dad`; Fedora 1.6.58-2; GCC, zlib-devel, CMake; downstream multilib patch | Factory API 401; public OBS `libpng16` packaging found but indexed older; not substituted | Zog uses upstream Autotools release, system zlib, no Fedora multilib patch, full upstream check |
| FreeType | 2.14.3 | `freetype.spec` @ `d6facd5816a4796f8eee47558239a02291221f3f`; Fedora 2.14.3-2; X11/libpng/zlib/bzip2/Brotli/HarfBuzz plus distro patches | Factory API 401; no current Factory spec bytes available to research job | Zog requires zlib/bzip2/libpng, explicitly disables HarfBuzz/Brotli; X11 is demo-only and not enabled in foundation |
| Fontconfig | 2.18.3 | `fontconfig.spec` @ `5d0ba8c986c2813cde0a2c6552b15ef859fd9717`; libxml2, FreeType, gettext, gperf, Meson/Ninja; current Fedora has several downstream policy patches including mono-detection | Factory API 401; public Factory-linked OBS package exists but source bytes unavailable to job | Zog retains upstream 2.18.3 unpatched, uses Expat rather than Fedora libxml2 choice, avoids host fc-cache mutation, records Fedora policy patches as non-Zog |
| Check | 0.15.2 | `check.spec` @ `71244a0b48ae80d1a9cd9ad4902fe253dfcc8c47`; GCC/libtool/make/pkgconf, optional distro subunit/texinfo and downstream patches | Factory API 401; public OBS Check 0.15.2 spec is available from GNOME:Factory/Factory linkage | Zog uses exact upstream release as libxcb/libevdev test support; no MinGW/subunit packaging split |
| libevdev | 1.14.0 | `libevdev.spec` @ `4e9b4ac72763eae0cc55c5d7fd66bc8439d64967`; Fedora 1.14.0-1; Meson/GCC/Python; tests and docs disabled by Fedora | Factory API 401; public X11:XOrg-linked OBS source indexed 1.13.1, older than selected release | Zog enables tests but excludes only upstream `needs-uinput`; tools/docs disabled; full uinput suite needs separately authorized device access |
| Python libevdev | 0.13.1 | `python-libevdev.spec` @ `4b39f45905b0bdc8578a797b0e7b2bec7fdf2e99`; Fedora 0.13.1-4; hatchling build; runtime native libevdev | Factory API 401; public openSUSE/SLE spec evidence is older (0.9) and confirms pytest + native libevdev model | Zog directly installs unchanged pure-Python package for xorgproto test support; device/root pytest cases remain external |
| xorgproto | 2026.1 | Fedora package `xorg-x11-proto-devel.spec` @ `e830e192e31d7fefaf6cf70f96c99e5e59ec5c01` is 2025.1-3; Meson/pkgconfig/GCC | Factory API 401; no current Factory spec bytes available | Zog intentionally selects newer upstream 2026.1; Python libevdev/native libevdev are explicit test prerequisites; legacy protocols disabled |
| libXau | 1.0.12 | `libXau.spec` @ `26b19948012efe452a102729068d9ca02ceadf1c`; Autotools, xorg macros/proto, pkgconfig; upstream check | Factory API 401; public Factory-linked OBS package indexed 1.0.11 | Zog uses Meson release recipe already prepared and preserves xorgproto dependency semantics |
| libXdmcp | 1.1.5 | `libXdmcp.spec` @ `88bc51eec4a8c561dcf8af33231b0e5380b81cd6`; Autotools/xorgproto | Factory API 401; no current bytes available | Zog uses upstream release and requires the authentication library outputs needed by libxcb/TurboVNC |
| xcb-proto | 1.17.0 | `xcb-proto.spec` @ `e73c011335f3a28013fa5c4699586bc0c1620a0c`; Fedora 1.17.0-12; Autotools, libxml2, Python; `make check` | Factory API 401; public OBS 1.17.0 package found | Zog retains XML parse/import checks and Python generator payload; no distro binary |
| libxcb | 1.17.0 | `libxcb.spec` @ `de0da2fada5296269f6b78b74365cbcea97f1e87`; Xau, xcb-proto, xorg macros, Python, libtool; docs add doxygen/graphviz/libxslt | Factory API 401; available public OBS index is historical, so not used as current-version authority | Zog enables XInput/XKB/DRI protocol libraries, requires Check test support and XDM auth, and does not require documentation-only tools |

## Test/device findings

libevdev 1.14.0's Meson file marks its kernel/device-facing tests with the
`needs-uinput` suite. The test sources directly use `/dev/uinput`. Zog therefore
does not grant device access in a package build. The final-stage recipe runs Meson's
non-`needs-uinput` tests and records full uinput coverage as external.

Python libevdev 0.13.1's pytest tree contains tests reading `/dev/input/event*`,
root-only cases, and uinput device creation. The exact xorgproto dependency is the
event-code constants/API, so Zog retains a device-independent import/constants test
and does not classify the device suite as passed.

## Evidence paths

Fedora immutable spec paths have the form
`https://src.fedoraproject.org/rpms/<package>/blob/<revision>/f/<package>.spec`.
The raw spec bodies and revision list were captured by
`.github/workflows/graphics-recipe-research.yml` on 2026-10-10.

The same job attempted
`https://api.opensuse.org/source/openSUSE:Factory/<package>/<package>.spec?expand=1`
for each row; those unauthenticated calls returned HTTP 401. Public OBS search pages
were used only as secondary packaging evidence and version context. This exception is
preserved rather than claiming a current Factory spec review that could not be read.


## Consumer-driven X11 core review

This batch is intentionally narrower than the complete Xorg library bundle. The
accepted graphics-XCB generation provides xorgproto, Xau, Xdmcp, XCB and the font
foundation. Same-batch edges below are only the newly built X11 core.

| Zog source | Selected | Fedora Rawhide evidence | Decision |
|---|---:|---|---|
| xtrans | 1.6.0 | Fedora source is packaged as `xorg-x11-xtrans-devel`; no direct `xtrans` Rawhide spec revision is treated as authoritative here | Header-only transport support; no runtime library |
| libX11 | 1.8.13 + 4 upstream fixes | `bcfb1f667006437e073677ede305a08ac543a6ec`; Fedora 1.8.13 also carries post-release security work | Apply official upstream CVE-2026-88806, -94283, -94284 and -94285 commits with exact patch hashes and per-file hash chains; retire when a fixed release contains them |
| libXext | 1.3.7 | `ef20ef23327573efdd7e77cb43e671d8a23ee40e` (Fedora still 1.3.6) | Select newer exact upstream release; depend on same-batch libX11 |
| libXfixes | 6.0.2 | `88ddb80cc358e3ba5a255e5c5e9c20ba473d9cb0` (Fedora 6.0.1) | Select newer exact upstream release; no Fedora patch copied |
| libXi | 1.8.3 | `d4fd33f773830c1ec062ef5aef51058775cd59c8` | Needed by libXtst/VirtualGL; specs generation disabled in first Zog profile |
| libXtst | 1.2.5 | `9f6d103add158ca758cc5a1c73ea19e9020b9fa2` | Required by VirtualGL |
| libXv | 1.0.13 | `956307eddd52ca9873165d7c967bfeef8eba1d3d` | Prepared because VirtualGL supports XVideo; final VirtualGL feature selection may omit it |
| libxkbfile | 1.2.0 | `81b3b98d4e63e84c1c190cd7b4c1416aca4206f6` (Fedora 1.1.3) | Required by TurboVNC Xvnc |
| libfontenc | 1.1.9 | `e2f99c8ba175d3b9fcc29a6e1fd88919ec99abb2` (Fedora 1.1.8) | Required by libXfont2; inherited base supplies zlib |
| libXfont2 | 2.0.9 | `e87bac79e8155fef29baf71603cdcaa9f9092043` | Required by TurboVNC Xvnc; use FreeType but disable Fontconfig integration in this server-core pass |

The reproducible source job downloaded each selected X.Org release and recorded its
archive and COPYING SHA-256. Direct openSUSE Factory source-API review for this
expanded batch remains to be recorded separately; the earlier Factory API calls
returned HTTP 401, so this table does not claim current Factory spec inspection.

## XCB/i3 support review — phase 1 and cursor closure

The successful `desktop-and-gl` research job on 2026-10-10 established the
following Fedora Rawhide immutable revisions. The openSUSE Factory direct source
probe again returned unavailable/HTTP 401 evidence and is therefore not claimed as
complete review. `xcb-util-renderutil` was accidentally omitted from that job; the
workflow correction in this bundle adds it before the cursor recipe is allowed to
advance to recipe-authored.

| Zog source | Selected | Fedora Rawhide evidence | Decision |
|---|---:|---|---|
| xcb-util | 0.4.1 | `0f1b53bfec87a0cdfbd73d25a41acd30ad100b38`; libxcb >= 1.4, GCC/make; upstream check | Exact XCB release; base utility library |
| xcb-util-image | 0.4.1 | `848a4e81c69358a7eccf60c432c7b51fd261b0fd`; xcb-util >= 0.3.8, m4 | Same-batch dependency on xcb-util; retain upstream `make check` |
| xcb-util-keysyms | 0.4.1 | `a587c4382558406b9f582ab31f29b197aa45ac1b`; xcb-util build macros | Runtime directly uses libxcb; no maintained upstream test target in selected release path |
| xcb-util-wm | 0.4.2 | `1dac1c8da1980c61f93e61906ab67ff772d5b906`; xcb-util build macros | Provides both xcb-icccm and xcb-ewmh required by i3/XCB consumers |
| xcb-util-xrm | 1.3 | `24ff5585b00bef5c233ba2bc5702471db9cb59cd`; xcb-aux and X11; Autotools | Release asset is upstream GitHub v1.3; links xcb-aux from xcb-util and uses Xlib in tests |
| xcb-util-renderutil | 0.3.10 | immutable revision **pending corrected research run**; Fedora 45/Rawhide package evidence shows 0.3.10 and `pkgconfig(xcb-renderutil)` | Required by xcb-util-cursor; do not promote to recipe-authored until immutable spec revision is captured |
| xcb-util-cursor | 0.1.6 | `bcb146d4e75281329fd998cca63c4ab780812684`; requires xcb-util, xcb-render, xcb-renderutil and xcb-image | Direct i3 dependency; hold recipe promotion with renderutil so its full dependency evidence remains atomic |

The current i3 4.25.1 Meson consumer graph additionally requires XCB XKB, Xinerama,
RandR and Shape; xkbcommon plus xkbcommon-x11; PCRE2 >= 10; Cairo/Pango;
GLib/GObject; libev; YAJL; and startup-notification. Those edges are tracked in the
next ledger phase rather than hidden behind distribution packages.


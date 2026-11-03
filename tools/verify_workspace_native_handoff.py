#!/usr/bin/env python3
"""Offline source handoff gate, NOT a native authority or generator of accepted IDs."""
import json
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("fonts", "XCB", "X11", "LLVM", "Mesa", "Xvnc-i3-xterm", "mesa-demos-smoke")
EDGES = (("fonts","Xvnc-i3-xterm"), ("XCB","X11"), ("X11","Mesa"),
         ("X11","Xvnc-i3-xterm"), ("LLVM","Mesa"), ("Mesa","Xvnc-i3-xterm"),
         ("Xvnc-i3-xterm","mesa-demos-smoke"))
RECEIPTS = ("fonts","XCB","X11","zlib_native_environment","ncurses_temporary","LLVM","Mesa")
SOURCES = {"workspace_pr9_reviewed_input":"db13d73a45f8a3be579226656442c331a9f701ea",
           "mesa_pr8":"9cbd652226b863a7b4bb2d6d9539722e1a262508"}
MUST_OUTPUT = ("usr/bin/Xvnc","usr/bin/i3","usr/bin/xterm","usr/lib/dri/swrast_dri.so",
               "usr/bin/glxgears","usr/bin/xkbcomp","usr/share/fonts/X11/misc/6x13.pcf.gz",
               "usr/share/terminfo/x/xterm", "usr/share/licenses/turbovnc/libsha1-COPYING")
REQUIRED_TOOLS = ("C-C++-linker-ar-objcopy-readelf", "meson-ninja-cmake-pkgconf",
                  "python-generators","XKB-and-font-tools","build-utilities")


# Exact review schema, not a generalized admission parser. Unknown success or
# authority-shaped fields must never be silently ignored by source CI.
ROOT_FIELDS = frozenset((
    "schema", "status", "source_revisions", "source_revision_policy",
    "producer_order", "producer_edges", "accepted_generation_receipts",
    "generation_receipt_policy", "inherited_stages", "source_packages",
    "selected_package_order_contract", "required_resources", "required_tools",
    "required_tool_provenance", "expected_outputs", "protected_evidence",
    "native_accepted", "rights_authorized", "build_submission_allowed",
    "canonical_promotion_allowed", "rights_gate", "native_readiness",
))
REQUIRED_DEPENDENCIES = {
    "i3": {"libxkbcommon-final", "xkeyboard-config-final", "libX11-final",
           "libxcb-final", "xcb-util-cursor-final", "pango-final"},
    "xterm": {"libXt-final", "libXaw-final", "libXmu-final", "libXpm-final",
              "libXft-final", "ncurses-temporary", "luit-final", "basic-font-final"},
    "turbovnc": {"mesa-final", "zlib-native-environment", "xkbcomp-final",
                  "xkeyboard-config-final", "libX11-final", "libXfont2-final",
                  "pixman-final", "libjpeg-turbo-final", "openssl-final"},
}
STAGE_PATHS = {
    "i3": ROOT/"project/package/i3/stages/final",
    "xterm": ROOT/"project/package/xterm/stages/final",
    "turbovnc": ROOT/"project/graphics-first-workspace/turbovnc-draft/stages/final",
    "basic-font": ROOT/"project/package/basic-font/stages/final",
    "xkbcomp": ROOT/"project/package/xkbcomp/stages/final",
    "xkeyboard-config": ROOT/"project/package/xkeyboard-config/stages/final",
}

# An omitted source manifest output must fail even if the handoff still
# mentions that output. The selected files are frozen independent obligations.
EXPECTED_STAGE_OUTPUTS = {
    "i3": frozenset((
        "usr/bin/i3","usr/bin/i3bar","usr/bin/i3-msg","usr/bin/i3-nagbar",
        "usr/share/licenses/i3/LICENSE")),
    "xterm": frozenset((
        "usr/bin/xterm","usr/share/X11/app-defaults/XTerm",
        "usr/share/terminfo/x/xterm","usr/share/licenses/xterm/COPYING")),
    "turbovnc": frozenset((
        "usr/bin/Xvnc","usr/bin/vncserver","usr/bin/vncpasswd",
        "usr/share/licenses/turbovnc/LICENSE.txt",
        "usr/share/licenses/turbovnc/Xserver-COPYING",
        "usr/share/licenses/turbovnc/libsha1-COPYING")),
    "basic-font": frozenset((
        "usr/share/fonts/X11/misc/6x13.pcf.gz",
        "usr/share/fonts/X11/misc/fonts.dir",
        "usr/share/licenses/basic-font/COPYING")),
    "xkbcomp": frozenset(("usr/bin/xkbcomp","usr/share/licenses/xkbcomp/COPYING")),
    "xkeyboard-config": frozenset(("usr/share/X11/xkb",)),
}

REQUIRED_RESOURCES = frozenset((
    "usr/share/fonts/X11/misc/6x13.pcf.gz", "usr/share/fonts/X11/misc/fonts.dir",
    "usr/share/X11/xkb", "usr/bin/xkbcomp", "usr/share/X11/app-defaults/XTerm",
    "usr/share/terminfo/x/xterm",
))
REQUIRED_DESKTOP = frozenset((
    "basic-font","bdftopcf","mkfontscale","xkbcomp","xkeyboard-config",
    "xcb-util-renderutil","xcb-util-cursor","i3","xterm","turbovnc",
    "libX11","libxcb","libXfont2","libxkbcommon","pixman","libjpeg-turbo",
))
REQUIRED_MESA = frozenset(("llvm","mesa","mesa-demos","libdrm","libxshmfence","libXxf86vm"))

def review_local_stage_closure(record, *, dependency_overrides=None, manifest_overrides=None):
    """Compare handoff to actual local stage metadata, not copied claims."""
    dependency_overrides = dependency_overrides or {}
    manifest_overrides = manifest_overrides or {}
    for name, prerequisites in REQUIRED_DEPENDENCIES.items():
        dependency = dependency_overrides.get(
            name, ast.literal_eval((STAGE_PATHS[name]/"dependencies.py").read_text()))
        if not isinstance(dependency, dict) or set(dependency) != {"build", "runtime"}:
            raise ValueError("invalid actual package dependency schema: "+name)
        all_deps = set(dependency["build"]) | set(dependency["runtime"])
        if not prerequisites.issubset(all_deps):
            raise ValueError("missing actual package predecessor: "+name)
        if "zlib-final" in all_deps or "ncurses-final" in all_deps:
            raise ValueError("invented inherited final-stage dependency: "+name)
    declared_outputs = set(record.get("expected_outputs", []))
    for name, path in STAGE_PATHS.items():
        manifest = manifest_overrides.get(name, ast.literal_eval((path/"produce-manifest.py").read_text()))
        if not isinstance(manifest,dict) or not isinstance(manifest.get("required"),list):
            raise ValueError("missing actual output manifest: "+name)
        required=set(manifest["required"])
        if not EXPECTED_STAGE_OUTPUTS[name].issubset(required):
            raise ValueError("actual stage manifest omits reviewed installed resource: "+name)
        if not required.issubset(declared_outputs):
            raise ValueError("handoff omits actual package output: "+name)
    packages = record.get("source_packages",{})
    if not isinstance(packages,dict) or set(packages)!={"desktop","mesa_draft"}:
        raise ValueError("source package groups missing")
    for group, must in (("desktop",REQUIRED_DESKTOP),("mesa_draft",REQUIRED_MESA)):
        items=packages.get(group)
        if not isinstance(items,list) or len(items)!=len(set(items)) or not must.issubset(set(items)):
            raise ValueError("missing or duplicate selected source package: "+group)
    if not REQUIRED_RESOURCES.issubset(set(record.get("required_resources",[]))):
        raise ValueError("required installed fonts/XKB/terminfo resource missing")
    for name in ("i3","xterm","turbovnc"):
        origin = (ROOT/"project/graphics-first-workspace/turbovnc-draft/package.py"
                  if name=="turbovnc" else ROOT/"project/package"/name/"package.py")
        if ast.literal_eval(origin.read_text()).get("status") != "catalogue-only":
            raise ValueError("selected source package already admitted: "+name)
    return True

def verify(record):
    if set(record) != ROOT_FIELDS:
        raise ValueError("unrecognized source handoff field or missing gate; no implicit authorization")
    if record.get("schema") != "zog-first-workspace-source-to-native-handoff-v1":
        raise ValueError("unknown Workspace handoff schema")
    if record.get("status") != "PREPARED_NOT_SUBMITTABLE":
        raise ValueError("source handoff cannot claim native readiness")
    order=record.get("producer_order")
    if tuple(order or ()) != STAGES or len(set(order))!=len(order):
        raise ValueError("missing or reordered native predecessor")
    if {tuple(x) for x in record.get("producer_edges", [])} != set(EDGES):
        raise ValueError("missing/changed dependency edge")
    indices={name:i for i,name in enumerate(order)}
    for predecessor,consumer in EDGES:
        if indices[predecessor]>=indices[consumer]:
            raise ValueError("Mesa/Xvnc or fonts/X11 producer ordering violated")
    receipts=record.get("accepted_generation_receipts")
    if not isinstance(receipts,dict) or set(receipts)!=set(RECEIPTS):
        raise ValueError("missing inherited or graphical predecessor receipt slot")
    if any(value is not None for value in receipts.values()):
        raise ValueError("fabricated or unauthenticated generation receipt")
    if record.get("source_revisions")!=SOURCES:
        raise ValueError("source revision changed; independently re-freeze exact sources")
    if "re-frozen" not in record.get("source_revision_policy",""):
        raise ValueError("moving PR head cannot count as immutable source")
    for key in ("native_accepted","rights_authorized","build_submission_allowed","canonical_promotion_allowed"):
        if record.get(key) is not False:
            raise ValueError("source-only handoff escalated: "+key)
    if record.get("native_readiness")!="REFUSE_MISSING_AUTHENTIC_RECEIPTS_AND_INDEPENDENT_ADMISSION":
        raise ValueError("source-only negative-readiness policy removed")
    for key in ("inherited_stages","required_resources","required_tools","expected_outputs","protected_evidence"):
        if not isinstance(record.get(key),list) or not record[key]:
            raise ValueError("missing handoff evidence: "+key)
    for token in ("zlib-native-environment","ncurses-temporary"):
        if token not in record["inherited_stages"]:
            raise ValueError("missing inherited selected Zog stage: "+token)
    for output in MUST_OUTPUT:
        if output not in record["expected_outputs"]:
            raise ValueError("missing native output: "+output)
    tools=record.get("required_tool_provenance")
    if not isinstance(tools,dict) or set(tools)!=set(REQUIRED_TOOLS) or any(not v for v in tools.values()):
        raise ValueError("missing selected build-tool origins or no-Host-leakage evidence")
    if not record.get("rights_gate","").startswith("HOLD:"):
        raise ValueError("component rights cannot be source-approved")
    for key in REQUIRED_TOOLS:
        descriptor = tools[key].lower()
        if "host defaults" in descriptor or "host fallback" in descriptor:
            raise ValueError("unreviewed host tool provenance: "+key)
    review_local_stage_closure(record)
    return True

def refuse_native_readiness(record):
    """Never infer an authorized generation from a source JSON file.
    
    Authenticity requires a separate protected verifier; this check cannot
    create, import or trust any receipt it is asked to read.
    """
    receipts=record.get("accepted_generation_receipts",{})
    missing=[name for name in RECEIPTS if not isinstance(receipts,dict) or receipts.get(name) is None]
    if missing:
        raise ValueError("native-readiness DENIED: authentic protected generation receipts missing: "+
                         ", ".join(missing))
    raise ValueError("native-readiness DENIED: source CI cannot authenticate or authorize generation receipts")

if __name__ == "__main__":
    record=json.loads((ROOT/"project/graphics-first-workspace/source-to-native-handoff.json").read_text())
    verify(record)
    try:
        refuse_native_readiness(record)
    except ValueError as err:
        if not str(err).startswith("native-readiness DENIED:"):
            raise
        print("Workspace handoff source checks PASS; "+str(err))
    else:
        raise AssertionError("source-only gate wrongly admitted native build")

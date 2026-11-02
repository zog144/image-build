# Data only; parsed with ast.literal_eval.
{
  "project": "glib",
  "stage_id": "final",
  "version": "2.86.5",
  "native_admission": "HOLD: codegen/interpreter/toolchain origin, exact pkgconf feature and output graph, selected copyright",
  "base_contract": "All build tools and Python code generators require separately authenticated selected immutable Zog compiler/software inputs. Environment name checks alone are not native attestation.",
  "build_feature_scope": "-Dtests=false -Dinstalled_tests=false -Ddocumentation=false -Dintrospection=disabled -Dman-pages=disabled -Dlibmount=disabled -Dselinux=disabled -Dsysprof=disabled -Dnls=disabled",
  "codegen_requires_isolated_python": [
    "glib-mkenums",
    "glib-genmarshal",
    "gdbus-codegen"
  ],
  "prohibited_fallback": [
    "Host Python",
    "Host pkgconfig .pc",
    "Host CMake/Meson wrap",
    "Host libraries",
    "Unselected optional feature"
  ],
  "patches": [],
  "patches_complete": True,
  "test_scope": "Source-only planned install outputs; actual configured options and ELF checks native-held."
}

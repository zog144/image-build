# Data only; parsed with ast.literal_eval.
{
  "project": "cairo",
  "stage_id": "final",
  "version": "1.18.4",
  "native_admission": "HOLD: codegen/interpreter/toolchain origin, exact pkgconf feature and output graph, selected copyright",
  "base_contract": "All build tools and Python code generators require separately authenticated selected immutable Zog compiler/software inputs. Environment name checks alone are not native attestation.",
  "build_feature_scope": "-Dauto_features=disabled",
  "codegen_requires_isolated_python": [],
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

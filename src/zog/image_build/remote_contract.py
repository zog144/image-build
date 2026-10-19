"""Shared remote-operation contract constants.

Kept separate from the executable adapter so pre-provenance readiness checks can
reason about an operation without importing or initializing the full CLI.
"""

REQUEST_SCHEMA = "image-build-remote-operation-v1"
RESULT_SCHEMA = "image-build-remote-result-v1"
CAPABILITIES_SCHEMA = "image-build-remote-capabilities-v1"
EXECUTION_EVIDENCE_SCHEMA = "image-build-remote-execution-evidence-v1"

GENERIC_PIPELINE_MODES = (
    "bootstrap",
    "image",
    "native-check",
    "seed-check",
)

SUPPORTED_OPERATIONS = (
    "capabilities.inspect",
    "recipe.validate",
    "recipes.snapshot",
    "worker.inspect",
    "toolchain.specification.inspect",
    "toolchain.submit",
    "toolchain.inspect",
    "toolchain.resume",
    "package.inspect",
    "dependencies.resolve",
    "pipeline.submit",
    "pipeline.inspect",
    "pipeline.resume",
    "pipeline.cancel",
    "pipeline.retry",
    "generation.inspect",
    "diagnostic.submit",
    "diagnostic.inspect",
)

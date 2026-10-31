# Immutable graphical predecessor composition

`mode=image` continues to require its `selection` to be a promoted,
self-hosted stage-2 **toolchain**. It never accepts an image as a toolchain.

For the two finite successor tasks only, the optional
`graphical_predecessor` is an independently accepted image generation ID.
The producer reopens its canonical immutable generation, validates the
manifest and full root inventory, source Host/Project build-record closure,
single installed-verification report and cleaned-up successful execution,
and checks its exact stage, architecture, toolchain ancestry and, for X11,
transitive Fonts → XCB ancestry. Unknown, foreign, incomplete and unverified
images fail closed. There is no public arbitrary image-layer operation.

XCB stages select the original accepted toolchain and bind the accepted
Fonts image. X11 selects the **same original toolchain** and binds the
accepted XCB image, whose root already contains Fonts. No caller changes
the toolchain ID. In the disposable per-package build root, the producer
first copies the toolchain, then merges the accepted predecessor image
without overwriting any non-directory path, then merges the required new
build dependencies. In the published output generation the producer first
merges inherited graphical runtime files, then the new runtime files.
Conflicts fail closed; the toolchain and predecessor generation directories
are never modified.

Every package build identity and the output generation input identity
bind the predecessor generation, exact manifest SHA-256, canonical
build-record generation-root record ID and composition contract.
The canonical assembly provenance retains the source predecessor manifest
as a hashed material and records the strict merge action. Pending
pipelines retain immutable arguments; resume reopens the exact same
accepted predecessor. No automatic retry, activation, protected source
rebind or native compiler admission is added.

The existing read-only `graphical_generation_acceptance` must verify
these extra arguments and ancestry for genuine successor outputs before
host-deploy may promote the next catalogue. The graphically chained
output still requires genuine installed verification; a successful
pipeline status alone is not accepted generation evidence.

This is source-level composition. No native Host, SSM, Stage A admission,
live compiler or installed protected catalogue is changed.

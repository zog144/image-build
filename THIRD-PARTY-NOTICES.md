# Third-party notices for image-build source

The image-build repository contains original Zog source code and build recipes
that refer to separately licensed upstream packages. The Zog first-party
grant is **BSD-3-Clause OR GPL-3.0-only**. It does not change the licensing
of upstream programs, recipes, patches or documentation owned by others.

Each third-party package's version-bound `project/package/*/license.py` record
contains the upstream license declaration and available evidence. These
records are source-review metadata and do not by themselves grant permission
to redistribute the package's source archive, built binary, or the contents
of a combined filesystem image.

For any binary distribution, the actual shipped component set and complete
required upstream copyright, license texts, exceptions and notices must be
recorded and verified separately. Some Rust dependency records (including
maturin and cryptography build closures) remain under review; no assertion
that all binary redistribution obligations are satisfied is made here.

No Zog private historical verification archive is incorporated by this notice.

# Host enrollment package bootstrap

Build host-identify 0.3.4, host-install 0.4.3 and host-discover 0.4.5 from exact
private GitHub source revisions recorded in the October pin. The resolver puts
host-identify and host-install before host-discover. Existing Python dependencies
come from the accepted HTTP-signatures generation, with exact canonical bindings.
Backend and runtime requirements are checked before building each wheel.

GitHub tarballs are downloaded by version-share with authorized repository access,
verified against the pinned Git tree, then seeded into the hash-addressed source
cache. Build jobs receive no GitHub credentials. Cache misses for these private
URLs require authorized prefetch; normal anonymous fetch is not sufficient.
Archives are build inputs outside Git, not vendored program repositories.

Each wheel is tested before installation. Installed-root checks cover fresh
identity authorization, repeat initialization without key replacement, 0600 key
files, signed enrollment message verification, altered body rejection, managed
session binding, and refusal to regenerate a missing identity. A separate legacy
transport fixture simulates pending/approved enrollment and verifies the resulting
signed heartbeat. Its mock approval is only synthetic test data: it never contacts
or approves a real registry record. The fixture does not prove the full managed
beacon/STATE mount path, AWS IID verification, replay persistence or live enrollment.
Host-install imports are tested; disk operations and service activation are excluded.
All generated identities live only in temporary build directories and are removed.
No private machine identities are included in reusable outputs.

Private Alex Black COPYRIGHT notices are hash-bound; no public license is granted.
The existing canonical producer captures inputs before dispatch and binds installed
verification and package outputs to the new immutable generation. Full package
pytest suites and boot acceptance remain separate validation work.

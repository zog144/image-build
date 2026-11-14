# Real inherited zlib source-stage binding

November 2, 2026 · Mesa PR #8. The LLVM and Mesa draft predecessor
references previously named `zlib-final`, although this repository only
authors `project/package/zlib/stages/native-environment`.
They now refer to the real `zlib-native-environment` source stage.
Tests reject the fictitious `zlib-final` stage and require its original
source metadata on the accepted ancestor path.

This is a source-stage correction, **not** a claim that an installed zlib
runtime, headers, pkg-config file or usable cross-bootstrap generation
has been witnessed for the later software-GL build. The exact inherited
generation and all build-input locations must be verified during native
admission. Existing Mesa rights/native NO-GO and six-package source
draft boundaries remain unchanged.

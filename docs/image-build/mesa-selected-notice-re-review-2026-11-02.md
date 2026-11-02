# Mesa selected original-notice delivery re-review — source only

**2026-11-02.** Reviewed PR #8 against the exact six draft
`license.py`, `stages/final/build.py`, `produce-manifest.py` and
`rights-admission-evidence.json` records.

The current original notice delivery plans for LLVM, Mesa, libdrm,
libxshmfence, libXxf86vm and mesa-demos each name exact original
source paths that are already recorded in their source-bound rights
metadata. Each planned installed path is explicitly present in the
authored install command and `produce-manifest.py`. The added
source tests reject an unlisted original notice, mismatched
SHA-256 source-archive binding, an omitted installed notice,
or an attempt to assert native or rights approval from these plans.

**These are consistency checks on authored source strings**, not a
proof that any compiler actually executed, that the selected source
graph includes or excludes a bundled file, or that matching notice
bytes were actually delivered. They deliberately do not duplicate
`verify_mesa_native_evidence.py` or its synthetic ar/response checks.

Specific selected-scope holds retained:
- LLVM: prove BLAKE3 and generated tables/code inclusion, map separate
  license texts to linked installed libraries.
- Mesa: prove exactly which GLAPI generated and llvmpipe sources link;
  demonstrate excluded Vulkan/imgui sources absent in native objects,
  and verify GLX loader paths from the Zog software root.
- libdrm: prove selected common library and inherited header rights,
  and that disabled vendor/KMS/udev material is not linked.
- libxshmfence/libXxf86vm: map compiled source objects and separate
  inherited xorgproto header copyrights, and inspect actual installed
  SONAME/notice bytes.
- mesa-demos: independently resolve the original glxgears/glxinfo
  public-domain and copyright headers and exact linked compile units.

The existing source-level tools deliberately hold unsupported
linker scripts, thin/extended archives, opaque implicit defaults,
ELF interpreters and real `ld.so` resolution. Only an authenticated
native selected-build trace can justify extending the verifier to
accept any such format, and any extension must remain fail-closed.

**Decision:** original selected-notice delivery *plans* are mutually
consistent. All six source rights records and output-specific grants
remain **unresolved**. Native installed bytes, release authorization
and canonical admission remain NO-GO. No frozen Boot A source change.

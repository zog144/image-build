# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "package": "pyyaml",
  "version": "6.0.3",
  "source": {
    "url": "https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz",
    "sha256": "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
  },
  "status": "unresolved",
  "expression": "MIT",
  "evidence": [
    {
      "path": "pyyaml-6.0.3/LICENSE",
      "sha256": "8d3928f9dc4490fd635707cb88eb26bd764102a7282954307d3e5167a577e8a4",
      "source_sha256": "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
    }
  ],
  "components": [
    {
      "scope": "Built wheel and bundled source files",
      "expression": None,
      "status": "unresolved",
      "notes": "Full selection and redistribution attribution pending."
    }
  ],
  "patches": [
    {
      "scope": "Exact PyYAML 6.0.3 pyproject.toml build-system declaration only",
      "expression": None,
      "status": "unresolved",
      "notes": "Pure-Python Mesa build profile removes conditional Cython requirements, preserves _pyyaml_pep517 backend and records original/revised SHA-256 in build output. Transformation must be independently reviewed before admission."
    }
  ],
  "notes": [
    "Original archive-member LICENSE digest checked by graphics archive inspector. No publication authority.",
    "Unmodified upstream archive pin remains authoritative; prepare applies reviewed-in-source transformation and retains original/revised digests. No unrecorded Cython fallback."
  ],
  "scope": "Build-only module rights; full distribution approval withheld"
}

# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "status": "build-only-source-evidence; not install-admitted",
  "purpose": "Mesa Mako template generation and PyYAML parser under isolated accepted Python; other packaging tools must be frozen separately",
  "packages": {
    "mako": {
      "version": "1.4.3",
      "source_sha256": "cd6537fe88d5fec315c55c2f8529bc4ce7a9a352ad7db3eeaa6a66e2dd4ec37a",
      "evidence": [
        {
          "path": "mako-1.4.3/LICENSE",
          "sha256": "8c1d171bc5d341ad9cd33d5e2c39b96a82c7bd49b3ae89a470c37e5822232054",
          "source_sha256": "cd6537fe88d5fec315c55c2f8529bc4ce7a9a352ad7db3eeaa6a66e2dd4ec37a"
        }
      ],
      "license": "MIT",
      "unresolved": [
        "MarkupSafe exact source/runtime dependency",
        "Python packaging backend isolation"
      ]
    },
    "pyyaml": {
      "version": "6.0.3",
      "source_sha256": "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f",
      "evidence": [
        {
          "path": "pyyaml-6.0.3/LICENSE",
          "sha256": "8d3928f9dc4490fd635707cb88eb26bd764102a7282954307d3e5167a577e8a4",
          "source_sha256": "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
        }
      ],
      "license": "MIT",
      "unresolved": [
        "Select pure Python load semantics or immutable Cython extension/ABI",
        "PEP 517 and build backend pins"
      ]
    }
  }
}

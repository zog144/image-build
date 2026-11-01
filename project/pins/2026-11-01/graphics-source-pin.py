# Data only; parsed with ast.literal_eval.
{
  "schema": 1,
  "date": "2026-11-01",
  "scope": "first-workspace-graphics-only",
  "status": "supplementary-source-review-only-NOT-canonical-monthly-snapshot",
  "policy": "Do not alter October 2026 Boot A/graphical chain pins. Hold canonical snapshots and build admission until full dependency/source/notice closure.",
  "packages": {
    "llvm": {
      "version": "21.1.6",
      "source": {
        "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-21.1.6/llvm-21.1.6.src.tar.xz",
        "sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad"
      },
      "upstream_revision": None,
      "status": "native-held",
      "recipes": {
        "llvm/stages/final": [
          {
            "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-21.1.6/llvm-21.1.6.src.tar.xz",
            "sha256": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad",
            "destination": "upstream",
            "archive": True
          }
        ]
      }
    },
    "mesa": {
      "version": "25.3.0",
      "source": {
        "url": "https://archive.mesa3d.org/mesa-25.3.0.tar.xz",
        "sha256": "0fd54fea7dbbddb154df05ac752b18621f26d97e27863db3be951417c6abe8ae"
      },
      "upstream_revision": None,
      "status": "native-held",
      "recipes": {
        "mesa/stages/final": [
          {
            "url": "https://archive.mesa3d.org/mesa-25.3.0.tar.xz",
            "sha256": "0fd54fea7dbbddb154df05ac752b18621f26d97e27863db3be951417c6abe8ae",
            "destination": "upstream",
            "archive": True
          }
        ]
      }
    },
    "mesa-demos": {
      "version": "9.0.0",
      "source": {
        "url": "https://archive.mesa3d.org/demos/mesa-demos-9.0.0.tar.xz",
        "sha256": "3046a3d26a7b051af7ebdd257a5f23bfeb160cad6ed952329cdff1e9f1ed496b"
      },
      "upstream_revision": None,
      "status": "native-held",
      "recipes": {
        "mesa-demos/stages/final": [
          {
            "url": "https://archive.mesa3d.org/demos/mesa-demos-9.0.0.tar.xz",
            "sha256": "3046a3d26a7b051af7ebdd257a5f23bfeb160cad6ed952329cdff1e9f1ed496b",
            "destination": "upstream",
            "archive": True
          }
        ]
      }
    }
  }
}

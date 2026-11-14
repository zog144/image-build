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
    },
    "libdrm": {
      "version": "2.4.128",
      "source": {
        "url": "https://dri.freedesktop.org/libdrm/libdrm-2.4.128.tar.xz",
        "sha256": "3bb35db8700c2a0b569f2c6729a53f5495786856b310854c8de57782a22bddac"
      },
      "upstream_revision": None,
      "status": "source-contract-native-held",
      "recipes": {
        "libdrm/stages/final": [
          {
            "url": "https://dri.freedesktop.org/libdrm/libdrm-2.4.128.tar.xz",
            "sha256": "3bb35db8700c2a0b569f2c6729a53f5495786856b310854c8de57782a22bddac",
            "destination": "upstream",
            "archive": True
          }
        ]
      }
    },
    "mako": {
      "version": "1.4.3",
      "source": {
        "url": "https://files.pythonhosted.org/packages/5a/09/e07c4b5579a79f4b16f8d4f29f6c54514ac787c4ad506b8c4f28a0e6b0bf/mako-1.4.3.tar.gz",
        "sha256": "cd6537fe88d5fec315c55c2f8529bc4ce7a9a352ad7db3eeaa6a66e2dd4ec37a"
      },
      "upstream_revision": None,
      "status": "pinned-python-build-input-unpack-not-admitted",
      "recipes": {}
    },
    "pyyaml": {
      "version": "6.0.3",
      "source": {
        "url": "https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz",
        "sha256": "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
      },
      "upstream_revision": None,
      "status": "pinned-python-build-input-unpack-not-admitted",
      "recipes": {}
    },
    "libxshmfence": {
      "version": "1.3.3",
      "source": {
        "url": "https://xorg.freedesktop.org/archive/individual/lib/libxshmfence-1.3.3.tar.xz",
        "sha256": "d4a4df096aba96fea02c029ee3a44e11a47eb7f7213c1a729be83e85ec3fde10"
      },
      "upstream_revision": None,
      "status": "drafted-glx-closure-not-admitted",
      "recipes": {
        "libxshmfence/stages/final": [
          {
            "url": "https://xorg.freedesktop.org/archive/individual/lib/libxshmfence-1.3.3.tar.xz",
            "sha256": "d4a4df096aba96fea02c029ee3a44e11a47eb7f7213c1a729be83e85ec3fde10",
            "destination": "upstream",
            "archive": True
          }
        ]
      }
    },
    "libXxf86vm": {
      "version": "1.1.7",
      "source": {
        "url": "https://xorg.freedesktop.org/archive/individual/lib/libXxf86vm-1.1.7.tar.xz",
        "sha256": "ae50c0f669e0af5a67cc4cd0f54f21d64a64d2660af883e80e95d3fe51b945d8"
      },
      "upstream_revision": None,
      "status": "drafted-glx-closure-not-admitted",
      "recipes": {
        "libXxf86vm/stages/final": [
          {
            "url": "https://xorg.freedesktop.org/archive/individual/lib/libXxf86vm-1.1.7.tar.xz",
            "sha256": "ae50c0f669e0af5a67cc4cd0f54f21d64a64d2660af883e80e95d3fe51b945d8",
            "destination": "upstream",
            "archive": True
          }
        ]
      }
    }
  }
}

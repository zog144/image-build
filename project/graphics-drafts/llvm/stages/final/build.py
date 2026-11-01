# Data only; parsed with ast.literal_eval.
{
  "configure": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "command -v cmake; command -v ninja; command -v g++\ncmake -S upstream/llvm-21.1.6.src -B build-llvm -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_TARGET_ARCH=X86 -DLLVM_ENABLE_PROJECTS= -DLLVM_ENABLE_RTTI=ON -DLLVM_BUILD_LLVM_DYLIB=ON -DLLVM_LINK_LLVM_DYLIB=ON -DLLVM_ENABLE_ZLIB=FORCE_ON -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_TERMINFO=OFF -DLLVM_ENABLE_LIBEDIT=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_ENABLE_BINDINGS=OFF"
    ]
  ],
  "build": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "cmake --build build-llvm --parallel 2"
    ]
  ],
  "test": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -x build-llvm/bin/llvm-config\nbuild-llvm/bin/llvm-config --version | grep -Fx 21.1.6\nbuild-llvm/bin/llvm-config --targets-built | tr ' ' '\\n' | grep -Fx X86\ntest \"$(build-llvm/bin/llvm-config --has-rtti)\" = YES\nbuild-llvm/bin/llvm-config --shared-mode | grep -Fx shared\n# The shared LLVM JIT linker ABI must also be checked after install."
    ]
  ],
  "install": [
    [
      "/bin/bash",
      "-eu",
      "-o",
      "pipefail",
      "-c",
      "test -n \"${DESTDIR:-}\"; DESTDIR=\"$DESTDIR\" cmake --install build-llvm --prefix /usr\ntest -x \"$DESTDIR/usr/bin/llvm-config\"\n# Verify libLLVM runtime output and its ELF closure before native admission."
    ]
  ]
}

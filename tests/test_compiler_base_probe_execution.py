"""Probe/controller integration regressions; no native acceptance is asserted."""
import json
from types import SimpleNamespace

from zog.image_build import compiler_base_probe as probe
from zog.image_build.configuration import input_manifest
from zog.image_build.runner import BuildExecutionResult


def test_probe_prepares_real_adapter_input_manifest_before_execution(tmp_path):
    root = tmp_path / 'selected-root'
    root.mkdir()
    (root / 'original').write_text('retained bytes')
    calls = []

    class Executor:
        def configuration(self):
            return {'fixture': 'source-only'}

        def __call__(self, request):
            # This is the actual configured adapter's pre-registration reader,
            # rather than a mock that accepts an unprepared request.
            manifest = input_manifest(request)
            prepared = json.loads((request.root.parent / 'prepared.json').read_text())
            assert prepared['binding']['generation'] == 'a' * 64
            assert prepared['binding']['command_sha256'] == probe.COMMAND_SHA256
            assert len(manifest) == 64
            calls.append(request)
            return BuildExecutionResult('fixture-r', 'fixture-i', 0, True, 'fixture-j')

    result = probe.execute_native_probe(
        SimpleNamespace(runner=SimpleNamespace(execute=Executor())),
        SimpleNamespace(root=root, generation='a' * 64), tmp_path / 'attempt')
    assert len(calls) == 1
    assert calls[0].read_only_root and not calls[0].network_access
    assert calls[0].timeout_seconds == 120
    assert result['native_accepted'] is False
    assert (root / 'original').read_text() == 'retained bytes'


def test_native_trace_capture_uses_header_and_linker_output_streams(tmp_path):
    # Exercise the exact shell command using tiny source-only executable stubs.
    # The stubs reproduce the documented output streams without a real compiler.
    import subprocess
    source = tmp_path / 'source'; source.mkdir()
    output = tmp_path / 'output'; output.mkdir()
    tools = tmp_path / 'tools'; tools.mkdir()
    (source / 'probe.c').write_bytes(probe.SOURCE)
    gcc = tools / 'gcc'
    gcc.write_text('''#!/bin/sh
case "$1" in
-dumpmachine) echo x86_64-linux-gnu ;;
-E) test "$2" = -H; echo '. /usr/include/stdio.h' >&2 ;;
*)
  case "$*" in
  *-Wl,-t*)
    echo /usr/lib/Scrt1.o
    echo /usr/lib/libc.so
    for arg in "$@"; do last="$arg"; done
    printf '#!/bin/sh\\necho zog-compiler-probe\\n' > "$last"
    chmod +x "$last"
    ;;
  esac ;;
esac
''')
    gcc.chmod(0o755)
    for name in ('as','ld'):
        p=tools/name; p.write_text('#!/bin/sh\nexit 0\n'); p.chmod(0o755)
    command=probe.COMMAND.replace('/usr/bin/gcc', str(gcc)).replace('/usr/bin/as', str(tools/'as')).replace('/usr/bin/ld', str(tools/'ld')).replace('/image-build/source',str(source)).replace('/image-build/output',str(output))
    subprocess.run(['/bin/sh','-eu','-c',command],check=True,capture_output=True)
    assert probe._lines((output/'includes.txt').read_bytes(),kind='include') == ['/usr/include/stdio.h']
    assert probe._lines((output/'links.txt').read_bytes(),kind='library') == ['/usr/lib/Scrt1.o','/usr/lib/libc.so']

"""Disposable-host integration faults; never run on a shared compiler host.

Copyright (c) 2026 Alex Black. SPDX-License-Identifier: BSD-3-Clause OR GPL-3.0-only
Requires the opt-in barrier and a dedicated provenance-root-control.service.
"""
import argparse
import socket as sockets
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import generation_provenance as base
import source_patch_provenance as materials

SERVICE = 'provenance-root-control.service'


def wait_for(test, seconds=15):
    deadline = time.monotonic() + seconds
    while not test():
        if time.monotonic() >= deadline:
            raise TimeoutError('controlled fault did not reach its expected state')
        time.sleep(.1)


def property_of(unit, name):
    return subprocess.check_output(['systemctl', 'show', unit, '-p', name, '--value'], text=True).strip()


def listening(path):
    # A pathname can survive SIGKILL; Type=simple active does not mean listening.
    # Connecting without a protocol request cannot submit or mutate a build.
    with sockets.socket(sockets.AF_UNIX, sockets.SOCK_STREAM) as probe:
        probe.settimeout(.2)
        try:
            probe.connect(str(path))
        except OSError:
            return False
    return True


def inject_submit(root, socket, *, missing):
    original = base.BoxControl.submit_build_job
    fired = False

    def submit(control, **request):
        nonlocal fired
        job = original(control, **request)
        if fired:
            return job
        fired = True
        unit = job['unit_name']
        if not missing:
            # No RefUnit keeper: allow the real hook to save evidence, then lose
            # the controller connection before it collects the process result.
            wait_for(lambda: property_of(unit, 'ActiveState') in ('inactive', 'failed'))
        subprocess.run(['systemctl', 'kill', '--kill-whom=main', '--signal=KILL', SERVICE], check=True)
        wait_for(lambda: property_of(SERVICE, 'MainPID') == '0')
        if missing:
            # The library emits its marker, sleeps five seconds, then compiles.
            # Keep the broker absent through both execution and the stop hook.
            time.sleep(10)
        wait_for(lambda: property_of(unit, 'LoadState') == 'not-found')
        subprocess.run(['systemctl', 'restart', SERVICE], check=True)
        wait_for(lambda: listening(socket) and property_of(SERVICE, 'ActiveState') == 'active')
        base.write_json(root/'evidence/barrier-fault.json', dict(
            job_id=job['job_id'], invocation_id=job['invocation_id'],
            unit=unit, missing_exit_evidence=missing, absent_before_restart=True))
        return job
    return submit


def inspect_recovered(root, socket):
    builder, provenance, trace = materials.context(root, socket)
    first = base.read(root/'evidence/first.json')
    fault = base.read(root/'evidence/barrier-fault.json')
    command = trace.inspect_command(first['binding']['build_id'], 'packages/number-library/build-0')
    control = builder.runner.execute.control
    job = control.inspect_build_job(fault['job_id'])
    logs = trace.logs(first['binding']['build_id'], 'packages/number-library/build-0', limit=50)
    assert job['exit_evidence_source'] == 'exit-hook', job
    assert job['journal_barrier']['status'] == 'synchronized', job
    assert command['job_id']['value'] == fault['job_id']
    assert command['execution']['invocation_id']['value'] == fault['invocation_id']
    assert command['command']['value'] == job['request']['command']
    assert command['outcome']['value'] == 'success' and command['exit_code']['value'] == 0
    assert command['recovery']['status'] == 'complete'
    assert logs['availability'] == 'available' and logs['entries'], logs
    base.write_json(root/'evidence/barrier-recovered.json', dict(
        passed=True, controller=job, command=command, logs=logs))


def unknown(root, socket):
    state = root/'state'
    config = base.read(root/'config.json')
    provenance = base.Provenance(state, **config)
    control = base.BoxControl(base.Project(root), systemd_transport=base.RootControlSystemdTransport(socket, timeout_seconds=90))
    adapter = base.BoxControlExecutionAdapter(control, execution_user_id=21001, execution_group_id=21001,
        startup_timeout_seconds=30, termination_grace_seconds=3, wait_timeout_seconds=120,
        resource_limits={'thread-count-maximum':128, 'memory-maximum-bytes':768*1024**2},
        input_manifest_id=lambda request:base.identity(base.inventory(request.root)))
    builder = base.ImageBuild(package_dir=root/'package', state_dir=state,
        runner=base.BoxControlRunner(adapter, timeout=90), provenance=provenance)
    seed = base.read_selection(base.read(root/'seed.json')['directory'])
    with patch.object(base.BoxControl, 'submit_build_job', inject_submit(root, socket, missing=True)):
        try:
            builder.verify_seed(['number-print'], host_bootstrap=seed)
        except base.BuildExecutionPending:
            pass
        else:
            raise AssertionError('missing exit evidence was accepted')
    p = base.pipeline(state)
    binding = base.package_binding(state, p)
    trace = base.BuildTrace(root, host_id=config['host_id'], record_project_id=config['project_id'],
        record_store=provenance.store.directory, controller=base.BoxControlReader(control))
    command = trace.inspect_command(binding['build_id'], 'packages/number-library/build-0')
    fault = base.read(root/'evidence/barrier-fault.json')
    job = control.inspect_build_job(fault['job_id'])
    assert job['outcome'] == 'unknown' and job['exit_code'] is None, job
    assert job['journal_barrier']['status'] == 'unconfirmed', job
    assert not job['process_cleanup_complete']
    assert command['outcome']['value'] == 'unknown' and command['exit_code']['value'] is None
    assert command['recovery']['status'] == 'blocked' and not command['recovery']['automatic_action']
    assert command['job_id']['value'] == fault['job_id']
    assert command['command']['value'] == job['request']['command']
    logs = trace.logs(binding['build_id'], 'packages/number-library/build-0', limit=50)
    before = sorted(x.name for x in (state/'build-job').glob('*.json'))
    frozen = dict(binding)
    # A second resume must retain the same unknown identity and frozen inputs.
    try:
        builder.resume(p.parent.name)
    except base.BuildExecutionPending:
        pass
    else:
        raise AssertionError('unknown outcome was redispatched or accepted')
    assert base.package_binding(state, p) == frozen
    assert sorted(x.name for x in (state/'build-job').glob('*.json')) == before
    manifests = [base.read(p) for p in (state/'image-build/generations').glob('*/manifest.json')]
    assert manifests and all(m['kind'] == 'host-bootstrap' for m in manifests)
    cancelled = control.cancel_build_job(job['job_id'])
    assert cancelled['outcome'] == 'unknown' and cancelled['process_cleanup_complete']
    builder.release_pipeline(p.parent.name)
    after = control.inspect_build_job(job['job_id'])
    assert after['outcome'] == 'unknown' and after['resources_released']
    base.write_json(root/'evidence/barrier-unknown.json', dict(passed=True,
        controller=job, command=command, logs=logs, released=after, frozen_binding=frozen,
        resume_preserved_identity=True, job_count=len(before)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['publish-recovered', 'inspect-recovered', 'unknown'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--socket', type=Path, required=True)
    args = parser.parse_args()
    if args.phase == 'publish-recovered':
        sys.argv[1] = 'publish'
        with patch.object(base.BoxControl, 'submit_build_job', inject_submit(args.root, args.socket, missing=False)):
            materials.main()
    elif args.phase == 'inspect-recovered':
        inspect_recovered(args.root, args.socket)
    else:
        unknown(args.root, args.socket)


if __name__ == '__main__':
    main()

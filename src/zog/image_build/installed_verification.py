"""Retained installed-test reports; commands and logs stay with execution owners."""
import json
import hashlib
from pathlib import Path

from .errors import ImageBuildError
from .filesystem import inventory
from .metadata import identity

CONTRACT = 'image-build-installed-verification-v1'
NAME = 'installed-verification.json'
ARGV_FIELD = 'verification_argv'
TARGETED_CHECK = 'resident-boot-a-targeted'


def verification_argv(owner_inputs):
    """Return the exact single installed-check argv frozen by the owner.

    New producers should freeze ARGV_FIELD explicitly. The targeted Boot A
    compatibility branch exists only for already-retained v1 owner inputs that
    predate ARGV_FIELD but whose verification_check unambiguously required
    pipefail. Other legacy callers retain the historical shorter argv.
    """
    _require(isinstance(owner_inputs, dict), 'installed verification owner inputs differ')
    script = owner_inputs.get('verification_command')
    _require(isinstance(script, str) and bool(script.strip()),
             'installed verification command was not frozen')
    legacy = ['/bin/bash', '-eu', '-c', script]
    pipefail = ['/bin/bash', '-eu', '-o', 'pipefail', '-c', script]
    explicit = owner_inputs.get(ARGV_FIELD)
    if explicit is None:
        return pipefail if owner_inputs.get('verification_check') == TARGETED_CHECK else legacy
    _require(isinstance(explicit, list) and all(isinstance(item, str) and item for item in explicit),
             'installed verification argv is invalid')
    _require(explicit in (legacy, pipefail), 'unsupported installed verification argv')
    if owner_inputs.get('verification_check') == TARGETED_CHECK:
        _require(explicit == pipefail, 'targeted installed verification must preserve pipefail')
    return list(explicit)


def verification_commands(owner_inputs):
    return [verification_argv(owner_inputs)]


def _read(path):
    if path.is_symlink():
        raise ImageBuildError('installed verification evidence must not be a symlink')
    return json.loads(path.read_bytes())


def _require(condition, message):
    if not condition:
        raise ImageBuildError(message)


def _subject(p, binding, root, owner_inputs):
    _require(owner_inputs.get('verification_report_contract') == CONTRACT,
             'installed verification report contract was not frozen')
    _require(identity(owner_inputs) == binding['generation'],
             'installed verification owner inputs differ')
    commands = verification_commands(owner_inputs)
    return dict(schema=1, kind=CONTRACT,
        generation_id=json.dumps([p.host_id, p.project_id, binding['generation']], separators=(',', ':')),
        assembly_attempt=binding['prepared'], check=owner_inputs.get('verification_check', 'installed-trust'),
        root_inventory_digest='sha256:'+identity(inventory(root)),
        commands_digest='sha256:'+identity(commands),
        policy_digest='sha256:'+identity(owner_inputs['execution_policy']))


def _execution(value):
    _require(type(value.get('exit_code')) is int and value['exit_code'] == 0
             and value.get('cleanup_complete') is True,
             'installed verification lacks successful cleaned-up completion')
    for key in ('runtime_id', 'invocation_id', 'journal_reference'):
        _require(isinstance(value.get(key), str) and bool(value[key]),
                 'installed verification lacks execution identity')
    return {key:value[key] for key in ('runtime_id','invocation_id','journal_reference',
                                      'exit_code','cleanup_complete')}



def _prepared_binding(prepared, expected, owner_inputs):
    """Validate optional v2 execution metadata without changing the legacy report."""
    if not isinstance(prepared, dict):
        raise ImageBuildError('installed verification preparation differs')
    base = {'root', 'binding', 'commands'}
    if set(prepared) == base:
        _require(prepared == expected, 'installed verification candidate or frozen inputs changed')
        return
    from . import verification_observations as vo
    fields = base | {
        'verification_observation_contract',
        'producer_policy_digest',
        'execution_environments',
    }
    _require(set(prepared) == fields
             and prepared['root'] == expected['root']
             and prepared['binding'] == expected['binding']
             and prepared['commands'] == expected['commands']
             and prepared['verification_observation_contract'] == vo.V2_SCHEMA,
             'installed verification candidate or frozen inputs changed')
    _require(prepared['producer_policy_digest'] ==
             vo.producer_policy_digest(owner_inputs['execution_policy']),
             'installed verification producer policy differs')
    environments = prepared['execution_environments']
    _require(isinstance(environments, list)
             and len(environments) == len(expected['commands']),
             'installed verification execution environments differ')
    for environment in environments:
        vo.validate_execution_environment(environment)

def capture(p, binding, root, owner_inputs, verification_attempt, execution):
    """Capture only completed evidence for exactly the candidate that was tested."""
    folder = Path(verification_attempt)
    commands = verification_commands(owner_inputs)
    subject = _subject(p, binding, root, owner_inputs)
    prepared = _read(folder/'prepared.json')
    completed = _read(folder/'verification.json')
    checkpoint = _read(folder/'command-0.execution.json')
    _prepared_binding(
        prepared,
        dict(root=inventory(root), binding=owner_inputs, commands=commands),
        owner_inputs,
    )
    _require(completed == dict(outputs=inventory(folder/'output'), policy=owner_inputs['execution_policy']),
             'installed verification outputs or policy changed')
    _require(checkpoint == execution and execution.get('policy') == (owner_inputs['execution_policy'] or {}).get('controller'),
             'installed verification completion differs')
    request = execution.get('request', {})
    _require(request.get('command') == commands[0]
             and request.get('root') == str((folder/'root').resolve())
             and request.get('source') == str((folder/'source').resolve())
             and request.get('output') == str((folder/'output').resolve())
             and request.get('read_only_root') is True
             and request.get('network_access') is False
             and request.get('timeout_seconds') == owner_inputs['execution_policy']['execution_timeout_seconds'],
             'installed verification request differs')
    report = dict(subject, outcome='succeeded', execution=dict(host_id=p.host_id, **_execution(execution)),
                  trace=dict(host_id=p.host_id, build_id='attempt:'+folder.name),
                  request_digest='sha256:'+identity(request))
    return p._bytes(NAME, report)


def validate(p, binding, root, owner_inputs, reports, *, execution=None):
    """Producer semantics layered over build-record's artifact/hash validation."""
    contract = owner_inputs.get('verification_report_contract')
    if contract is None:
        _require(not reports, 'cannot retrofit installed verification onto a legacy assembly')
        return
    _require(contract == CONTRACT and len(reports) == 1,
             'frozen installed verification report is required')
    descriptor = reports[0]
    _require(descriptor.get('name') == NAME, 'installed verification report descriptor differs')
    # The caller verifies descriptor bytes through canonical build-record before
    # accepting a generation. Reading here never follows a report-supplied locator.
    from zog.build_record.model import artifact
    artifact(descriptor)
    path = p.root/'artifacts'/descriptor['digest'][7:]
    _require(not path.is_symlink(), 'installed verification report must not be a symlink')
    with path.open('rb') as stream:
        raw = stream.read(65537)
    _require(len(raw) <= 65536 and len(raw) == descriptor['size']
             and 'sha256:'+hashlib.sha256(raw).hexdigest() == descriptor['digest'],
             'installed verification report bytes differ')
    report = json.loads(raw)
    subject = _subject(p, binding, root, owner_inputs)
    _require(set(report) == set(subject) | {'outcome','execution','trace','request_digest'}
             and all(report.get(k) == v for k,v in subject.items())
             and report['outcome'] == 'succeeded',
             'installed verification report subject differs')
    evidence = report['execution']
    _require(isinstance(evidence, dict) and set(evidence) ==
             {'host_id','runtime_id','invocation_id','journal_reference','exit_code','cleanup_complete'}
             and evidence['host_id'] == p.host_id, 'installed verification execution scope differs')
    _execution(evidence)
    trace = report['trace']
    _require(isinstance(trace,dict) and set(trace) == {'host_id','build_id'}
             and trace['host_id'] == p.host_id and isinstance(trace['build_id'],str)
             and trace['build_id'].startswith('attempt:') and len(trace['build_id']) > 8,
             'installed verification trace scope differs')
    from zog.build_record.model import digest
    digest(report['request_digest'])
    if execution is not None:
        _require(evidence == dict(host_id=p.host_id, **_execution(execution))
                 and report['request_digest'] == 'sha256:'+identity(execution.get('request'))
                 and execution.get('policy') == owner_inputs['execution_policy'].get('controller'),
                 'installed verification owner execution differs')

"""Resumable synchronous projection of the controller's richer build records."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from .errors import ImageBuildError
from .runner import BuildExecutionResult


INHERITED_EXECUTION_CONTRACT = "zog-build-inherited-peer-v2"


def _require_inherited_record(raw, fields, label):
    """Old stored identity or incomplete v2 state is never upgraded/replayed."""
    if (type(raw) is not dict or raw.get("schema") != 2
            or raw.get("execution_contract") != INHERITED_EXECUTION_CONTRACT
            or set(raw) != set(fields) | {"schema", "execution_contract"}):
        raise ImageBuildError("legacy or incompatible " + label + " is inspection-only; refusing replay")
    return raw


def _require_inherited_peer():
    """Only the privileged receiver may derive credentials from SO_PEERCRED.

    A process running as root may inspect old evidence but may not register
    or start a compiler; this local check is not itself proof of the child UID.
    """
    if os.geteuid() == 0 or os.getegid() == 0:
        raise ImageBuildError("inherited build requires an authenticated nonroot controller peer")
    from zog.box_control.build_protocol import INHERITED_EXECUTION_CONTRACT as wire
    if wire != INHERITED_EXECUTION_CONTRACT:
        raise ImageBuildError("installed box-control inherited-peer v2 wire is not selected")


class BuildExecutionPending(ImageBuildError):
    def __init__(self, record):
        self.request_id = record['request_id']
        self.job_id = record['job_id']
        self.state = record['state']
        for name in ('build_root_id','source_workspace_id','output_workspace_id'):
            setattr(self, name, record['request'][name])
        super().__init__(f'build {self.job_id} is {self.state}; resume the same command checkpoint')


class BuildRegistrationPending(ImageBuildError):
    """A sent registration needs later inspection, never a replacement request."""
    def __init__(self, resource_id, observed):
        self.resource_id = resource_id
        self.state = observed['state']
        self.phase = observed.get('phase')
        super().__init__(f'registration {resource_id} is {self.state}; revisit the same identity')


class BuildExecutionFailed(ImageBuildError):
    def __init__(self, record):
        self.record = record
        super().__init__(f"build {record['job_id']}: {record['outcome']}; {record.get('error') or record.get('journal_reference')}")


class BoxControlExecutionAdapter:
    def __init__(self, control, *, startup_timeout_seconds, termination_grace_seconds, wait_timeout_seconds,
                 resource_limits, input_manifest_id, device_profile=None, execution_identity="inherit"):
        if execution_identity != "inherit":
            raise ImageBuildError("controller execution_identity must be inherit")
        self.execution_identity = execution_identity
        self.device_profile = device_profile
        self.control = control
        self.startup_timeout_seconds = startup_timeout_seconds
        self.termination_grace_seconds = termination_grace_seconds
        self.wait_timeout_seconds = wait_timeout_seconds
        self.resource_limits = dict(resource_limits)
        # Explicit value or caller resolver; never infer this from an arbitrary path.
        self.input_manifest_id = input_manifest_id
        if wait_timeout_seconds < 0: raise ValueError('negative caller wait timeout')

    def configuration(self):
        return dict(**({'device_profile':self.device_profile} if self.device_profile is not None else {}),
                    execution_identity=self.execution_identity,
                    execution_contract=INHERITED_EXECUTION_CONTRACT,
                    project_root=str(self.control.project.path),
                    socket_path=str(getattr(self.control.systemd_transport, "socket_path", "test-transport")),
                    startup_timeout_seconds=self.startup_timeout_seconds,
                    termination_grace_seconds=self.termination_grace_seconds,
                    resource_limits=self.resource_limits)

    def release_resources(self, directory):
        from zog.box_control.build_jobs import BuildJobs
        from zog.box_control.durability import replace_json
        directory = Path(directory)
        resource_path = directory / 'controller-resources.json'
        if not resource_path.exists(): return
        _require_inherited_peer()
        resource = _require_inherited_record(json.loads(resource_path.read_text()),
            {'resource_id', 'registration'}, 'build resource')
        released = directory / 'controller-released.json'
        if released.exists(): return
        for checkpoint in sorted(directory.glob('*.controller.json')):
            saved = _require_inherited_record(json.loads(checkpoint.read_text()),
                {'binding', 'resource_id', 'request_id', 'job_id'}, 'build checkpoint')
            if saved['resource_id'] != resource['resource_id']:
                raise ImageBuildError('command resource identity differs')
            job_id = BuildJobs.job_id(saved['request_id'])
            record = self.control.refresh_build_job(job_id)
            self._assert_controller_record(record, 'build job')
            if not record['process_cleanup_complete']:
                raise BuildExecutionPending(record)
            released_record = self.control.release_build_job(job_id)
            self._assert_controller_record(released_record, 'released build job')
            if isinstance(released_record, dict):
                from .trace_records import capture_observation
                capture_observation(checkpoint, released_record)
        released_root = self.control.release_build_root(resource['resource_id'])
        self._assert_controller_record(released_root, 'released build resource')
        replace_json(released, {'resource_id': resource['resource_id'],
                                'execution_contract': INHERITED_EXECUTION_CONTRACT})

    @staticmethod
    def _assert_controller_record(record, label):
        if (type(record) is not dict
                or record.get("execution_contract") != INHERITED_EXECUTION_CONTRACT):
            raise ImageBuildError("incompatible " + label + " response; inherited peer v2 required")

    @staticmethod
    def _assert_registration_status(observed, resource_id, registration):
        """Read the *server* schema-2 peer identity, not a box-control marker.

        On registration timeout, the independent root-control inspection RPC
        returns its own schema-2 record with kernel-derived execution_identity.
        An absent record is an inspection result only, never permission to
        register a replacement identity or start an old operation.
        """
        if type(observed) is not dict or observed.get("resource_id") != resource_id:
            raise ImageBuildError("root-control registration inspection identity differs")
        if observed.get("state") == "absent":
            if set(observed) != {"resource_id", "state"}:
                raise ImageBuildError("ambiguous absent registration inspection")
            return
        peer = observed.get("execution_identity")
        if (observed.get("schema") != 2
                or type(peer) is not dict or set(peer) != {"uid", "gid"}
                or any(type(peer[k]) is not int or peer[k] <= 0 for k in peer)
                or observed.get("intent") != registration):
            raise ImageBuildError("root-control registration is not authenticated peer-bound schema 2")

    def _register(self, resource_id, registration, directory):
        """Reconcile only a typed registration reply timeout; never retry starts."""
        _require_inherited_peer()
        from zog.box_control.durability import replace_json
        from zog.box_control import errors
        pending_path = directory/'registration-pending.json'
        binding = {'schema': 2, 'execution_contract': INHERITED_EXECUTION_CONTRACT,
                   'resource_id': resource_id, 'registration': registration}

        def inspect():
            observed = self.control.inspect_build_root(resource_id)
            self._assert_registration_status(observed, resource_id, registration)
            replace_json(directory/'registration-progress.json', {
                'schema': 2, 'execution_contract': INHERITED_EXECUTION_CONTRACT,
                'resource_id': resource_id, 'state': observed['state'],
                'phase': observed.get('phase'), 'updated_at': observed.get('updated_at')})
            if observed['state'] not in {'ready', 'importing', 'absent'}:
                raise ImageBuildError('Registration cannot continue: '+observed['state'])
            return observed

        def reconcile_ready():
            result = self.control.register_build_root(resource_id=resource_id, **registration)
            self._assert_controller_record(result, 'registration result')
            # Only the controller reconciles its mutation guard. A crash before
            # removing this marker simply repeats the safe ready inspection.
            pending_path.unlink()
            from .filesystem import sync_directory
            sync_directory(directory)
            return result

        if pending_path.exists():
            if _require_inherited_record(json.loads(pending_path.read_text()),
                    {'resource_id', 'registration'}, 'pending registration') != binding:
                raise ImageBuildError('Pending registration identity or intent changed')
            observed = inspect()
            if observed['state'] != 'ready':
                raise BuildRegistrationPending(resource_id, observed)
            return reconcile_ready()
        try:
            result = self.control.register_build_root(resource_id=resource_id, **registration)
            self._assert_controller_record(result, 'registration result')
            return result
        except errors.RecoveryRequired as failure:
            cause = failure
            timeout_type = getattr(errors, 'RootControlReplyTimeout', ())
            while cause is not None and not isinstance(cause, timeout_type):
                cause = cause.__cause__
            if cause is None or cause.operation != 'build_register':
                raise
            replace_json(pending_path, binding)
            observed = {'state': 'absent'}
            # Bound both caller time and poll count. Inspection calls are independently
            # bounded by box-control (10s). An old controller fails closed here.
            deadline = time.monotonic() + 120
            for delay in (1, 2, 4, 8, 15, 15, 15, 15):
                if time.monotonic() + delay >= deadline:
                    break
                time.sleep(delay)
                observed = inspect()
                print(f"Registration {resource_id}: {observed['state']} / {observed.get('phase', 'unknown')}", flush=True)
                if observed['state'] == 'ready':
                    # The mutation API validates identical intent and clears its own
                    # recovery marker. No caller edits controller state.
                    return reconcile_ready()
            raise BuildRegistrationPending(resource_id, observed) from failure

    def execute_for_attempt(self, request, checkpoint):
        from zog.box_control.durability import replace_json
        from zog.box_control.locking import ProjectLock
        from .trace_records import capture_request, capture_observation
        checkpoint = Path(checkpoint)
        resources_path = request.root.parent / 'controller-resources.json'
        pending_path = request.root.parent / 'registration-pending.json'

        def reject_old_before_mutation():
            if checkpoint.exists():
                _require_inherited_record(json.loads(checkpoint.read_text()),
                    {'binding', 'resource_id', 'request_id', 'job_id'}, 'build checkpoint')
            if resources_path.exists():
                _require_inherited_record(json.loads(resources_path.read_text()),
                    {'resource_id', 'registration'}, 'build resource')
            if pending_path.exists():
                _require_inherited_record(json.loads(pending_path.read_text()),
                    {'resource_id', 'registration'}, 'pending registration')

        # Fast fail first: even the historical command's lock file must not
        # be created just to learn that old identity cannot be replayed.
        _require_inherited_peer()
        reject_old_before_mutation()
        with ProjectLock(checkpoint.with_suffix('.lock')):
            # Repeat the check under lock to reject records appearing in
            # between read-only preflight and the exclusive operation lock.
            _require_inherited_peer()
            reject_old_before_mutation()
            intent = json.loads(json.dumps(asdict(request),default=str,allow_nan=False))
            manifest_id = self.input_manifest_id(request) if callable(self.input_manifest_id) else self.input_manifest_id
            config = dict(startup_timeout_seconds=self.startup_timeout_seconds, termination_grace_seconds=self.termination_grace_seconds,
                          resource_limits=self.resource_limits, input_manifest_id=manifest_id)
            if self.device_profile is not None: config['device_profile'] = self.device_profile
            binding = {'execution_contract': INHERITED_EXECUTION_CONTRACT,
                       'request':intent,'configuration':config}
            capture_request(checkpoint.with_name(checkpoint.name.removesuffix('.controller.json') + '.log'), request, config)
            # One shared registration across this package's sequential commands.
            with ProjectLock(resources_path.with_suffix('.lock')):
                registration = dict(prepared_root=str(request.root),source_directory=str(request.source),
                                    output_directory=str(request.output),input_manifest_id=manifest_id,
                                    )
                if resources_path.exists():
                    resource = _require_inherited_record(json.loads(resources_path.read_text()),
                        {'resource_id', 'registration'}, 'build resource')
                    if resource['registration'] != registration: raise ImageBuildError('package resource binding changed')
                else:
                    resource = {'schema': 2, 'execution_contract': INHERITED_EXECUTION_CONTRACT,
                                'resource_id':uuid.uuid4().hex,'registration':registration}
                    replace_json(resources_path,resource)
                if not checkpoint.exists():
                    self._register(resource['resource_id'], registration, request.root.parent)
            rid = resource['resource_id']
            if checkpoint.exists():
                saved = _require_inherited_record(json.loads(checkpoint.read_text()),
                    {'binding', 'resource_id', 'request_id', 'job_id'}, 'build checkpoint')
                if saved['binding'] != binding or saved['resource_id'] != rid:
                    raise ImageBuildError('command attempt intent changed; cannot reuse identity')
            else:
                request_id = self.control.issue_build_request_id()
                from zog.box_control.build_jobs import BuildJobs
                saved = dict(schema=2,execution_contract=INHERITED_EXECUTION_CONTRACT,
                             binding=binding,resource_id=rid,request_id=request_id,
                             job_id=BuildJobs.job_id(request_id))
                replace_json(checkpoint,saved)  # Durable before first submission.
            arguments = dict(build_root_id=rid,source_workspace_id=rid+'-source',output_workspace_id=rid+'-output',
                command=list(request.command),environment=dict(request.environment),working_directory=request.working_directory,
                read_only_root=request.read_only_root,network_access=request.network_access,
                execution_timeout_seconds=request.timeout_seconds,
                **{k:v for k,v in config.items() if k != 'input_manifest_id'})
            from zog.box_control.build_jobs import BuildJobs
            from zog.box_control.errors import RuntimeOperationError
            from zog.box_control.build_protocol import canonical_request
            job_id = BuildJobs.job_id(saved['request_id'])
            try:
                record = self.control.inspect_build_job(job_id)
            except RuntimeOperationError as error:
                # Absence of the controller's authoritative record proves that
                # this identity has not been accepted. Other read faults block.
                if str(error) != 'unknown build identity: job:' + job_id:
                    raise
                record = self.control.submit_build_job(request_id=saved['request_id'], **arguments)
            self._assert_controller_record(record, 'build job')
            if record['request_id'] != saved['request_id'] or record['request'] != canonical_request(arguments):
                raise ImageBuildError('controller record differs from command binding')
            # Nonblocking resume must reconcile once before checking its deadline.
            # inspect_build_job only reads persisted state, which may be stale.
            if not record['process_cleanup_complete']:
                record = self.control.refresh_build_job(record['job_id'])
                self._assert_controller_record(record, 'refreshed build job')
            capture_observation(checkpoint, record)
            deadline = time.monotonic()+self.wait_timeout_seconds
            while not record['process_cleanup_complete']:
                if record['state']=='unknown' or time.monotonic() >= deadline:
                    raise BuildExecutionPending(record)
                time.sleep(min(0.2,max(0,deadline-time.monotonic())))
                record = self.control.refresh_build_job(record['job_id'])
                self._assert_controller_record(record, 'refreshed build job')
                capture_observation(checkpoint, record)
            if record['outcome'] not in ('success','nonzero-exit'):
                raise BuildExecutionFailed(record)
            if record['exit_code'] is None or not record['invocation_id'] or not record['journal_reference']:
                raise BuildExecutionFailed(record)
            return BuildExecutionResult(record['runtime_id'],record['invocation_id'],record['exit_code'],
                                        record['process_cleanup_complete'],record['journal_reference'])

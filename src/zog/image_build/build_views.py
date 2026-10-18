"""Read-only command grouping. Authorize the attempt directory before calling."""
import hashlib
import json
from pathlib import Path
from .errors import ImageBuildError


def read_build_commands(attempt, *, after=None, limit=50):
    """Page command mappings without submitting jobs or refreshing their state."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be an integer from 1 through 100')
    if after is not None and not isinstance(after, str):
        raise ValueError('after must be a command key')
    attempt = Path(attempt)
    entries = []
    for path in sorted([*(attempt / 'packages').glob('*/*.view.json'), *attempt.glob('*.view.json'),
                        *(attempt / 'packages').glob('*/test-fixture-cache/*.view.json'),
                        *(attempt / 'packages').glob('*/test-fixture-runtime/*.view.json')]):
        key = path.relative_to(attempt).as_posix()
        if after is not None and key <= after:
            continue
        raw = json.loads(path.read_text())
        checkpoint = raw['checkpoint']
        if raw.get('schema') != 1 or Path(checkpoint).name != checkpoint:
            raise ImageBuildError('invalid command view')
        saved_path = path.with_name(checkpoint)
        saved = json.loads(saved_path.read_text()) if saved_path.exists() else None
        job_id = None
        if saved is not None:
            request_id = saved.get('request_id')
            if not isinstance(request_id, str) or not request_id:
                raise ImageBuildError('invalid command request identity')
            job_id = hashlib.sha256(request_id.encode()).hexdigest()[:32]
            if saved.get('job_id', job_id) != job_id:
                raise ImageBuildError('command job identity mismatch')
        entries.append(dict(raw, command_key=key, job_id=job_id,
                            request_id=saved['request_id'] if saved else None))
        if len(entries) > limit:
            break
    page = entries[:limit]
    return dict(commands=page, has_more=len(entries) > limit,
                next_after=page[-1]['command_key'] if page else after)

"""Literal monthly source locks. Normal builds never resolve a moving branch."""
from datetime import date
from pathlib import Path
import pprint

from .errors import ImageBuildError
from .metadata import identity, literal

SUPPLEMENTAL_BUILD_SOURCE_CONTRACT = "image-build-supplemental-build-source-pin-v1"


def supplemental_build_source(path, sources, month, repository_path):
    record = literal(path)
    required = {"schema", "contract", "month", "scope", "repository_path", "sources"}
    if (
        not isinstance(record, dict)
        or set(record) != required
        or record.get("schema") != 1
        or record.get("contract") != SUPPLEMENTAL_BUILD_SOURCE_CONTRACT
        or record.get("month") != month
        or record.get("scope") != "build-only"
        or record.get("repository_path") != repository_path
        or record.get("sources") != sources
    ):
        raise ImageBuildError("invalid supplemental build source pin")
    return record


def load(path):
    record = literal(path)
    try:
        day = date.fromisoformat(record['date'])
        if record['schema'] != 1 or day.day != 1 or not isinstance(record['packages'], dict):
            raise ValueError('invalid schema/date/packages')
        return record
    except (KeyError, TypeError, ValueError) as error:
        raise ImageBuildError('invalid monthly commit-pin.py') from error


def validate(directory, packages):
    """Require an explicit lock for every recipe before new execution."""
    record = load(Path(directory)/'commit-pin.py')
    for name, package in packages.items():
        entry = record['packages'].get(name)
        if not isinstance(entry, dict) or entry.get('sources') != list(package.sources):
            raise ImageBuildError(f'{name}: recipe sources differ from monthly pin; review both together')
    return record


def snapshot(catalogue, entries, destination, pin_date=None):
    pins = Path(catalogue).parent/'pins'
    selected = pin_date or literal(pins/'current.py')['date']
    try:
        day = date.fromisoformat(selected)
        if day.day != 1 or selected != day.isoformat():
            raise ValueError('not a monthly date')
    except (TypeError, ValueError) as error:
        raise ImageBuildError('invalid pin date') from error
    monthly = load(pins/selected/'commit-pin.py')
    if monthly['date'] != selected:
        raise ImageBuildError('pin directory/date mismatch')
    packages = {}
    for entry in entries:
        project = monthly['packages'].get(entry['project'], {})
        key = entry['recipe']
        pin_policy = entry.get('pin_policy', 'monthly-recipe')
        sources = project.get('recipes', {}).get(key)
        supplemental = None
        if sources is None and pin_policy == 'catalogue-source':
            selected_sources = literal(Path(catalogue)/key/'sources.py')
            source = project.get('source')
            if (
                not isinstance(source, dict)
                or len(selected_sources) != 1
                or {k:selected_sources[0].get(k) for k in ('url','sha256')} != source
            ):
                raise ImageBuildError(
                    f'{key}: catalogue-source recipe differs from reviewed monthly package source'
                )
            sources = selected_sources
        elif sources is None and pin_policy == 'supplemental-build-source':
            sources = literal(Path(catalogue)/key/'sources.py')
            repository_path = 'project/package/' + key + '/supplemental-pin.py'
            supplemental = supplemental_build_source(
                Path(catalogue)/key/'supplemental-pin.py',
                sources,
                selected,
                repository_path,
            )
        elif sources is None or pin_policy != 'monthly-recipe':
            raise ImageBuildError(f'{key}: missing reviewed monthly source pin')
        packages[entry['id']] = {
            'sources': sources,
            'project': entry['project'],
            'recipe': key,
            **({'pin_policy': pin_policy} if pin_policy != 'monthly-recipe' else {}),
            **(
                {
                    'supplemental_pin': {
                        'repository_path': supplemental['repository_path'],
                        'identity': identity(supplemental),
                    }
                }
                if supplemental is not None else {}
            ),
        }
    record = {'schema': 1, 'date': selected, 'monthly_identity': identity(monthly), 'packages': packages}
    path = Path(destination)/'commit-pin.py'
    if path.exists():
        if load(path) != record:
            raise ImageBuildError('recorded monthly pins changed; use a new operation')
    else:
        if any(Path(destination).iterdir()):
            raise ImageBuildError('legacy recipes have no monthly pins; use a new operation directory')
        path.write_text('# Literal monthly source snapshot; do not execute.\n'+pprint.pformat(record, sort_dicts=False)+'\n')
    return record

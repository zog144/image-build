"""Publish an application image from an accepted runtime's exact package outputs.

No package execution, active-selection changes, or controller mutation occurs.
The original installed verification is retained as evidence, not rerun or relabelled.
"""
import argparse
import fcntl
import json
import re
from pathlib import Path

from . import ImageBuild, read_selection
from .errors import ImageBuildError
from .filesystem import inventory, write_json
from .generation_provenance import prepare, finish, verify as verify_generation
from .metadata import Package
from .provenance import Provenance
from .rootfs_compatibility import derive, FIELD
from .application_data_targets import (
    FIELD as DATA_TARGET_FIELD,
    bind as bind_application_data_targets,
    directories as application_data_directories,
    validate_root as validate_application_data_root,
)
from .runtime_facilities import (
    FIELD as FACILITY_FIELD,
    ROOT_MODES,
    ROOTS,
    derive as derive_runtime_facilities,
)
from . import host_labels, installed_verification

POLICY = 'accepted-runtime-application-image-v1'
MOUNTPOINTS = {
    **ROOT_MODES,
    'root': 0o750,
    'var': 0o755,
    **application_data_directories(),
    'var/tmp': 0o1777,
}


def _same_contents(base, candidate, facility_intent):
    """Preserve accepted bytes while normalizing runtime facilities to empty roots."""
    old = {r['path']: r for r in base}
    new = {r['path']: r for r in candidate}
    nested = {item['path'].lstrip('/') for item in facility_intent['directories']}
    facility_roots = set(ROOTS)
    missing = sorted(nested - set(old))
    if missing:
        raise ImageBuildError(
            'runtime facility intent is absent from accepted contents: ' + ', '.join(missing)
        )
    retained = {}
    for name, record in old.items():
        top = name.split('/', 1)[0]
        if top not in facility_roots:
            retained[name] = record
            continue
        if record['kind'] != 'directory':
            raise ImageBuildError(
                'accepted runtime facility contains immutable content: ' + name
            )
        if name == top:
            if record['mode'] != ROOT_MODES[top]:
                raise ImageBuildError(
                    'accepted runtime facility root mode differs: ' + name
                )
        elif name not in nested:
            raise ImageBuildError(
                'accepted runtime facility directory lacks package intent: ' + name
            )
    additions = {
        name: {'path': name, 'kind': 'directory', 'mode': mode}
        for name, mode in MOUNTPOINTS.items()
        if name not in retained
    }
    if new != {**retained, **additions}:
        raise ImageBuildError(
            'application image differs from accepted contents beyond '
            'provenance-bound runtime facility normalization and empty mountpoints'
        )


def publish(builder, selection, components, work, source_revision):
    """Durable, inactive publication; caller supplies exact retained output paths."""
    work = Path(work).resolve()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', work.name):
        raise ImageBuildError('invalid runtime image operation name')
    if not re.fullmatch(r'[0-9a-f]{40}', source_revision):
        raise ImageBuildError('exact producer revision required')
    p = builder.provenance
    if not p or not p.generation_contract:
        raise ImageBuildError('runtime image publication requires canonical provenance')
    work.mkdir(parents=True, exist_ok=True)
    with (work/'operation.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with builder.locked():
            base = read_selection(selection)
            manifest = base.manifest
            execution = manifest.get('verification_execution', {})
            if (manifest['kind'] != 'toolchain' or not manifest.get('self_hosted')
                    or type(execution.get('exit_code')) is not int or execution['exit_code'] != 0
                    or execution.get('cleanup_complete') is not True
                    or manifest['inputs'].get('verification_report_contract') != installed_verification.CONTRACT
                    or FIELD not in manifest):
                raise ImageBuildError('accepted descriptor-bearing runtime toolchain required')
            bundle = verify_generation(p, base)
            if set(components) != set(manifest['packages']):
                raise ImageBuildError('exact accepted runtime package set required')
            built = {}
            for name, path in sorted(components.items()):
                record = dict(manifest['packages'][name], root=str(Path(path).resolve()))
                if inventory(record['root']) != record['outputs']:
                    raise ImageBuildError('accepted package output changed: '+name)
                p.verify_output(record['provenance'], name, record)
                built[name] = record
            compatibility = derive(built, manifest['inputs']['architecture'])
            facility_intent = derive_runtime_facilities(built)
            data_targets = bind_application_data_targets(manifest['outputs'])
            if compatibility != manifest[FIELD]:
                raise ImageBuildError('accepted runtime compatibility changed')
            intent = dict(policy=POLICY, source_revision=source_revision, base=base.generation,
                          components={n:r['root'] for n,r in built.items()}, mountpoints=MOUNTPOINTS,
                          runtime_facility_intent=facility_intent,
                          application_data_targets=data_targets,
                          provenance=p.configuration(), application_software_compatibility=compatibility)
            saved = work/'intent.json'
            if saved.exists() and json.loads(saved.read_text()) != intent:
                raise ImageBuildError('frozen runtime image publication changed')
            write_json(saved, intent)
            # Keep the complete verified base graph, including installed execution
            # evidence, as a hash-bound assembly material. Do not claim a fresh test.
            evidence = p._bytes('accepted-runtime-provenance.json', bundle)
            labels = host_labels.snapshot(built)
            label_material = p._bytes('host-label-omissions.json', labels)
            mounts = p._bytes('application-mountpoints.json', MOUNTPOINTS)
            facilities = p._bytes('application-runtime-facilities.json', facility_intent)
            data_target_material = p._bytes(
                'application-data-targets.json', data_targets
            )
            attempt = builder.state/'image-build/attempts'/(work.name+'-assembly')
            inputs = dict(schema=2, kind='image', architecture=compatibility['architecture'],
                          publication=intent, assembly_attempt=attempt.name,
                          base_generation_record=manifest['build_record'],
                          accepted_runtime_evidence=evidence, provenance=p.configuration(),
                          composition_policy=host_labels.POLICY, host_label_evidence=label_material,
                          application_software_compatibility=compatibility,
                          runtime_facility_intent=facility_intent,
                          application_data_targets=data_targets)
            definitions = {n:Package(n,(),(),(),{},{},(),{}) for n in built}
            binding = prepare(p, attempt, definitions, list(built), built, inputs,
                composition_materials=[
                    label_material,
                    mounts,
                    facilities,
                    data_target_material,
                    evidence,
                ],
                composition_actions=[
                    'Retain accepted runtime package membership and exact package outputs as provenance inputs.',
                    'Omit only directory-only package trees beneath controller runtime facility roots while composing the application image; reject files, symlinks and special objects there.',
                    'Materialize /applications, /run, /proc, /sys and /dev as empty real directories; preserve omitted package directory intent in application-runtime-facilities.json.',
                    'Materialize the reviewed /var/lib/station-access and /var/lib/archive-mirror paths only as empty immutable writable-mount targets; reject accepted content or redirection at either target.',
                    'Preserve original installed verification in accepted-runtime-provenance.json.',
                ])
            root = host_labels.compose(
                attempt, built, list(built), labels, directories=MOUNTPOINTS,
                omit_empty_directory_trees=ROOTS,
            )
            validate_application_data_root(root, data_targets)
            _same_contents(manifest['outputs'], inventory(root), facility_intent)
            pointer = finish(p, attempt, binding, root)
            accepted = builder._publish(root, inputs, 'image', dict(
                application_software_compatibility=compatibility,
                runtime_facility_intent=facility_intent,
                application_data_targets=data_targets,
                build_record=pointer,
                packages={n:{k:v for k,v in r.items() if k!='root'} for n,r in built.items()},
                verification_inherited_from=base.generation, purpose='application-runtime',
                host_boot_ready=False))
            exported = verify_generation(p, accepted)
            write_json(work/'canonical-generation.json', exported)
            result = dict(phase='complete', generation=accepted.generation, root=str(accepted.root),
                          kind='image', source_revision=source_revision, base=base.generation,
                          canonical_record=pointer['record'],
                          canonical_export=str(work/'canonical-generation.json'))
            write_json(work/'result.json', result)
            return result


def run(project, selection, work, base_components, source_revision):
    project, selection, work = map(lambda x: Path(x).resolve(), (project, selection, work))
    base = read_selection(selection)
    p = Provenance.from_configuration(project/'state', base.manifest['inputs']['provenance'])
    builder = ImageBuild(package_dir=work/'unused', state_dir=project/'state',
                         maximum_generations=32, provenance=p)
    return publish(builder, selection, json.loads(Path(base_components).read_text()), work, source_revision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project','selection','work','base-components','source-revision'):
        parser.add_argument('--'+name, required=True)
    print(json.dumps(run(**vars(parser.parse_args()))), flush=True)


if __name__ == '__main__':
    main()

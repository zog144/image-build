"""Report catalogue coverage for a proposed host profile; never infer installed state."""
import argparse
import json
from pathlib import Path

from .errors import ImageBuildError
from .metadata import literal, identity
from .filesystem import digest

RECIPE_FILES = ('package.py', 'sources.py', 'build.py', 'dependencies.py', 'produce-manifest.py')


def inspect(profile, catalogue):
    profile = literal(profile); catalogue = Path(catalogue)
    if (
        profile['schema'] != 1
        or profile['status'] not in {'planning-not-installable', 'boot-a-source-candidate'}
    ):
        raise ImageBuildError('unsupported host source profile')
    items = []
    for item in profile['items']:
        name = item['project']
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
            raise ImageBuildError('invalid profile project')
        directory = catalogue/name
        stages = []
        for d in sorted((directory/'stages').glob('*')):
            if not d.is_dir(): continue
            # Stage package.py is normally materialized from the canonical package record.
            expected = RECIPE_FILES[1:]
            missing = [f for f in expected if not (d/f).is_file()]
            stages.append({'stage':d.name, 'recipe_files_present':not missing,
                           'missing_files':missing,
                           'file_hashes':{f:digest(d/f) for f in expected if (d/f).is_file()}})
        items.append({**item, 'catalogue_present':directory.is_dir(),
                      'package_metadata_present':(directory/'package.py').is_file(),
                      'license_metadata_present':(directory/'license.py').is_file(),
                      'stages':stages, 'host_acceptance':'not-assessed',
                      'recipe_gap':not any(s['recipe_files_present'] for s in stages)})
    by_name = {item['project']: item for item in items}
    boot = profile.get('boot_a')
    if boot is not None:
        projects = boot.get('projects')
        if (
            not isinstance(projects, list)
            or projects != list(dict.fromkeys(projects))
            or any(name not in by_name for name in projects)
        ):
            raise ImageBuildError('invalid Boot A project selection')
        recipe_gaps = [
            name for name in projects
            if not by_name[name]['catalogue_present'] or by_name[name]['recipe_gap']
        ]
        boot_report = {**boot, 'recipe_gaps': recipe_gaps,
                       'source_recipe_complete': not recipe_gaps}
    else:
        boot_report = None
    return {'schema':1, 'profile':profile['profile'], 'profile_identity':identity(profile),
            'status':profile['status'], 'installable':False,
            'source_candidate':bool(boot_report and boot_report['source_recipe_complete']),
            'dependency_closure':profile.get('dependency_closure', 'not-reviewed'),
            'live_inventory':'not-performed', 'items':items,
            'boot_a':boot_report, 'resident_b':profile.get('resident_b'),
            'recipe_review_candidates':profile['recipe_review_candidates'],
            'candidate_note':profile['candidate_note'], 'acceptance':profile['acceptance'],
            'excluded_from_first_host':profile['excluded_from_first_host']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', required=True); p.add_argument('--catalogue', required=True)
    a = p.parse_args(); print(json.dumps(inspect(a.profile, a.catalogue), indent=2))


if __name__ == '__main__': main()

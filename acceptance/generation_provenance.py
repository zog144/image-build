"""Opt-in live acceptance; run only on an isolated disposable systemd host.

Copyright (c) 2026 Alex Black. SPDX-License-Identifier: BSD-3-Clause OR GPL-3.0-only
This driver never provisions hosts. Commands run through real box-control jobs.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from unittest.mock import patch

from zog.box_control import BoxControl, Project
from zog.box_control.runtime.root_control import RootControlSystemdTransport
from zog.build_record import canonical, inspect, verify_artifacts
from zog.build_trace import BuildTrace, BoxControlReader, TraceError
from zog.image_build import ImageBuild
from zog.image_build.artifacts import import_completed
from zog.image_build.box_control_adapter import BoxControlExecutionAdapter, BuildExecutionPending
from zog.image_build.engine import read_selection
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import inventory, write_json
from zog.image_build.metadata import identity
from zog.image_build.provenance import Provenance
from zog.image_build.runner import BoxControlRunner


def read(path):
    return json.loads(path.read_text())


def pipeline(state):
    return max((state/'image-build/pipelines').glob('*/pipeline.json'), key=lambda p:p.stat().st_mtime_ns)


def package_binding(state, path, name='number-library'):
    attempt = next(iter(read(path)['attempts'].values()))
    p = state/'image-build/attempts'/attempt/'packages'/name/'provenance.json'
    return read(p)


def prepare_packages(root):
    notice = 'Copyright (c) 2026 Alex Black. Public Zog-owned acceptance fixture. BSD-3-Clause OR GPL-3.0-only.\n'
    definitions = {
        'number-library': ({'number.c':'int zog_number(void) { return 42; }\n'}, [],
            {'build':[['/bin/sh','-c','echo acceptance-library-start; sleep 5; cc -c src/number.c -o number.o; ar rcs libnumber.a number.o']],
             'install':[['/bin/sh','-c','mkdir -p "$DESTDIR/usr/lib"; cp libnumber.a "$DESTDIR/usr/lib/"']]}, ['usr/lib/libnumber.a']),
        'number-print': ({'main.c':'#include <stdio.h>\nint zog_number(void);\nint main(void) { printf("%d\\n", zog_number()); return 0; }\n'}, ['number-library'],
            {'build':[['cc','-static','src/main.c','/usr/lib/libnumber.a','-o','number-print']],
             'test':[['./number-print']],
             'install':[['/bin/sh','-c','mkdir -p "$DESTDIR/usr/bin"; cp number-print "$DESTDIR/usr/bin/"']]}, ['usr/bin/number-print']),
    }
    monthly = dict(schema=1,date='2026-10-01',packages={})
    selected = dict(schema=1,date='2026-10-01',packages={})
    for name,(files,deps,steps,outputs) in definitions.items():
        directory=root/'package'/name; directory.mkdir(parents=True)
        archive=root/(name+'.tar')
        with tarfile.open(archive,'w',format=tarfile.USTAR_FORMAT) as tf:
            for filename,content in {**files,'COPYRIGHT':notice}.items():
                data=content.encode(); info=tarfile.TarInfo(filename);info.size=len(data);info.mode=0o644
                tf.addfile(info,io.BytesIO(data))
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        sources=[dict(url=archive.as_uri(),sha256=digest,destination='src',archive=True)]
        license_record=dict(schema=1,package=name,version='acceptance-1',source=dict(url=archive.as_uri(),sha256=digest),status='reviewed',expression='BSD-3-Clause OR GPL-3.0-only',scope='Original fixture source only; excludes bootstrap system libraries.',evidence=[dict(path='COPYRIGHT',sha256=hashlib.sha256(notice.encode()).hexdigest(),source_sha256=digest)],components=[],patches=[],notes=['Original synthetic fixture under the first-party grant; excludes bootstrap system libraries.'])
        for filename,value in {'sources.py':sources,'dependencies.py':dict(build=deps,runtime=[]),'build.py':steps,'produce-manifest.py':outputs,'license.py':license_record}.items():
            (directory/filename).write_text(repr(value)+'\n')
        monthly['packages'][name]={'recipes':{'acceptance':sources}}
        selected['packages'][name]=dict(sources=sources,project=name,recipe='acceptance')
    selected['monthly_identity']=identity(monthly)
    (root/'monthly.py').write_text(repr(monthly));(root/'package/commit-pin.py').write_text(repr(selected))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['init','cancel','prepare','publish','recover','reuse','verify'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--seed',type=Path)
    parser.add_argument('--socket',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();state=root/'state';evidence=root/'evidence'
    if args.phase=='init':
        root.mkdir(parents=True,exist_ok=False)
        if os.listxattr(root):
            raise ImageBuildError('acceptance requires new directories without extended attributes; use a compatible disposable host')
        evidence.mkdir();prepare_packages(root)
        subprocess.run(['git','init',str(root)],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['git','-C',str(root),'add','package','monthly.py','number-library.tar','number-print.tar'],check=True)
        subprocess.run(['git','-C',str(root),'-c','user.name=Alex Black','-c','user.email=acceptance@localhost','commit','-m','Freeze private acceptance catalogue'],check=True,stdout=subprocess.DEVNULL)
        revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        pin=Provenance.capture_pin(state,root/'monthly.py',repository=root.as_uri(),revision=revision,repository_path='monthly.py')
        config=dict(host_id='provenance-acceptance',project_id=root.name,pin=pin)
        write_json(root/'config.json',config)
    config=read(root/'config.json')
    if args.phase not in ('init','cancel'):
        config['retry_of']={'number-library':read(evidence/'cancelled.json')['result']}
    provenance=Provenance(state,**config)
    control=BoxControl(Project(root),systemd_transport=RootControlSystemdTransport(args.socket,timeout_seconds=90))
    class Adapter(BoxControlExecutionAdapter):
        def execute_for_attempt(self,request,checkpoint):
            if args.phase=='prepare':
                write_json(evidence/'prepared.json',package_binding(state,pipeline(state)))
                os._exit(75)  # Crash the caller after frozen provenance, before dispatch.
            if args.phase=='cancel' and not (evidence/'cancel-job.json').exists():
                self.wait_timeout_seconds=0
                try:
                    super().execute_for_attempt(request,checkpoint)
                except BuildExecutionPending as pending:
                    write_json(evidence/'cancel-job.json',dict(job_id=pending.job_id))
                    control.cancel_build_job(pending.job_id)
                finally:
                    self.wait_timeout_seconds=120
            return super().execute_for_attempt(request,checkpoint)
    adapter=Adapter(control,execution_user_id=21001,execution_group_id=21001,
        startup_timeout_seconds=30,termination_grace_seconds=3,wait_timeout_seconds=120,
        resource_limits={'thread-count-maximum':128,'memory-maximum-bytes':768*1024**2},
        input_manifest_id=lambda request:identity(inventory(request.root)))
    builder=ImageBuild(package_dir=root/'package',state_dir=state,runner=BoxControlRunner(adapter,timeout=90),provenance=provenance)
    if args.phase=='init':
        assert args.seed is not None
        seed=builder.import_bootstrap(args.seed,{'id':'distribution-bootstrap-acceptance','self_hosted':False})
        write_json(root/'seed.json',dict(directory=str(seed.root.parent)))
        return
    seed=read_selection(read(root/'seed.json')['directory'])
    if args.phase=='cancel':
        try:builder.verify_seed(['number-print'],host_bootstrap=seed)
        except ImageBuildError:pass
        else:raise AssertionError('cancelled job unexpectedly succeeded')
        p=pipeline(state);binding=package_binding(state,p)
        assert provenance.store.get(binding['result'])['data']['outcome']=='cancelled'
        write_json(evidence/'cancelled.json',binding);builder.release_pipeline(p.parent.name)
    elif args.phase=='prepare':
        builder.verify_seed(['number-print'],host_bootstrap=seed)
        raise AssertionError('preparation crash did not fire')
    elif args.phase=='publish':
        # Current recipe/pin selection changes must never enter recovery.
        shutil.copytree(root/'package',root/'original-package')
        (root/'monthly.py').write_text('changed current monthly selection')
        (root/'package/commit-pin.py').write_text('changed current pin')
        (root/'package/number-library/build.py').write_text("{'build':[['false']]}")
        import zog.image_build.generation_provenance as gp
        def interrupted(path,data):
            write_json(path,data)
            if Path(path).parent.name=='assembly' and Path(path).name=='generation.json':
                write_json(evidence/'publication.json',data)
                write_json(evidence/'jobs-before-recovery.json',sorted(p.name for p in (state/'build-job').glob('*.json')))
                os._exit(76)
        with patch.object(gp,'write_json',side_effect=interrupted):builder.resume(pipeline(state).parent.name)
        raise AssertionError('publication crash did not fire')
    elif args.phase=='recover':
        p=pipeline(state);result=builder.resume(p.parent.name)
        assert result.manifest['build_record']==read(evidence/'publication.json')
        original=read(evidence/'prepared.json');current=package_binding(state,p)
        assert original['prepared']==current['prepared'] and original['inputs']==current['inputs']
        cancelled=read(evidence/'cancelled.json')
        assert current['prepared']!=cancelled['prepared'] and current['inputs']==cancelled['inputs']
        start=provenance.store.get(current['prepared'])['data'];assert start['retry_of']==cancelled['result']
        assert sorted(p.name for p in (state/'build-job').glob('*.json'))==read(evidence/'jobs-before-recovery.json')
        assert subprocess.check_output([result.root/'usr/bin/number-print'],text=True).strip()=='42'
        assert not (result.root/'usr/lib/libnumber.a').exists()
        write_json(evidence/'first.json',dict(generation=result.generation,pipeline=p.parent.name,binding=current))
        builder.release_pipeline(p.parent.name);import_completed(builder,p.parent.name)
        shutil.rmtree(root/'package');shutil.copytree(root/'original-package',root/'package')
    elif args.phase=='reuse':
        before=sorted(p.name for p in (state/'build-job').glob('*.json'))
        result=builder.verify_seed(['number-library'],host_bootstrap=seed)
        first=read(evidence/'first.json');assert result.generation!=first['generation']
        assert result.manifest['packages']['number-library']['provenance']=={k:first['binding'][k] for k in ('output','result')}
        assert before==sorted(p.name for p in (state/'build-job').glob('*.json'))
        write_json(evidence/'second.json',dict(generation=result.generation,pipeline=pipeline(state).parent.name))
        builder.release_pipeline(pipeline(state).parent.name)
    else:
        first=read(evidence/'first.json');second=read(evidence/'second.json')
        trace=BuildTrace(root,host_id=config['host_id'],record_project_id=config['project_id'],record_store=provenance.store.directory,controller=BoxControlReader(control))
        roots=trace.generations(output=first['binding']['output'],limit=1);rows=roots['items']
        if roots['has_more']:rows+=trace.generations(output=first['binding']['output'],limit=1,cursor=roots['next_cursor'])['items']
        assert {r['generation'] for r in rows}=={first['generation'],second['generation']}
        reports=[]
        for generation in (first['generation'],second['generation']):
            selection=read_selection(state/'image-build/generations'/generation)
            bundle=provenance.store.bundle([selection.manifest['build_record']['record']]);report=inspect(bundle)
            assert not report['missing_records']
            assets={p['digest']:str(provenance.root/'artifacts'/p['digest'][7:]) for p in report['artifacts']}
            verified=verify_artifacts(bundle,assets);assert all(v['status']=='verified' for v in verified['artifact_verification'])
            export=evidence/(generation+'.json');export.write_bytes(canonical(bundle))
            from zog import build_record
            standalone=subprocess.run([sys.executable,'-S','-m','zog.build_record','inspect',str(export)],cwd=evidence,env={'PATH':os.environ['PATH'],'PYTHONPATH':str(Path(build_record.__file__).resolve().parents[2])},capture_output=True,text=True)
            assert standalone.returncode in (0,3),standalone.stderr
            assert json.loads(standalone.stdout)==report
            page=trace.generation_provenance(generation,limit=2);ids=[]
            while True:
                ids.extend(row['id'] for row in page['records']['items'])
                if not page['records']['has_more']:break
                page=trace.generation_provenance(generation,limit=2,cursor=page['records']['next_cursor'])
            assert set(ids)==set(bundle['records']) and len(ids)==len(set(ids))
            reports.append(dict(generation=generation,root=bundle['roots'][0],records=len(ids),complete=report['complete'],missing=report['missing_records'],verified_artifacts=len(assets)))
        # Damage disposable retained-material copies only; live records remain immutable.
        from zog.image_build.generation_provenance import verify as verify_generation
        rejected=[]
        selection=read_selection(state/'image-build/generations'/first['generation'])
        recipe=provenance.store.get(first['binding']['inputs'])['data']['recipe']['digest']
        for damage in ('missing','corrupt'):
            copy_state=root/('rejection-'+damage)
            copy_root=copy_state/'image-build/build-record'
            shutil.copytree(provenance.root,copy_root)
            material=copy_root/'artifacts'/recipe[7:]
            if damage=='missing':material.unlink()
            else:material.write_bytes(b'corrupt disposable recipe')
            isolated=Provenance(copy_state,**config)
            try:verify_generation(isolated,selection)
            except (ImageBuildError,ValueError,OSError):rejected.append(damage)
            else:raise AssertionError('damaged required recipe accepted')
        assert rejected==['missing','corrupt']
        command=trace.inspect_command(first['binding']['build_id'],'packages/number-print/test-0')
        logs=trace.logs(first['binding']['build_id'],'packages/number-print/test-0',limit=10)
        assert logs['availability']=='available' and '42' in json.dumps(logs['entries']),logs
        assert command['job_id']['value'] and command['execution']['invocation_id']['value']
        write_json(evidence/'result.json',dict(passed=True,rejected_materials=rejected,generations=reports,membership=rows,journal=dict(job_id=command['job_id']['value'],invocation_id=command['execution']['invocation_id']['value'],availability=logs['availability'],entries=logs['entries']),self_hosting_tested=False))
    print(args.phase+' passed',flush=True)

if __name__=='__main__':main()

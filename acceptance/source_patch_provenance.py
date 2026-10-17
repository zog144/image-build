"""Real source/patch acceptance on a disposable host; see acceptance/README.md.

Copyright (c) 2026 Alex Black. SPDX-License-Identifier: BSD-3-Clause OR GPL-3.0-only
Original Zog-owned fixture sources and patches are generated outside the checkout.
"""
import argparse
import ast
import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from unittest.mock import patch

import generation_provenance as base


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literal(path):
    return ast.literal_eval(path.read_text())


def git_commit(root, paths, message):
    if not (root/'.git').exists():
        subprocess.run(['git','init',str(root)],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['git','-C',str(root),'add',*paths],check=True)
    if subprocess.run(['git','-C',str(root),'rev-parse','--verify','HEAD'],capture_output=True).returncode==0 and subprocess.run(['git','-C',str(root),'diff','--cached','--quiet']).returncode==0:
        return subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    subprocess.run(['git','-C',str(root),'-c','user.name=Alex Black','-c','user.email=acceptance@localhost','commit','-m',message],check=True,stdout=subprocess.DEVNULL)
    return subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()


def configure_sources(root, changed=False):
    """Declare actual local Git commits, byte hashes and two independent patches."""
    monthly=literal(root/'monthly.py');selected=literal(root/'package/commit-pin.py')
    for name in ('number-library','number-print'):
        directory=root/'package'/name;archive=root/(name+'.tar')
        with tarfile.open(archive) as tf:
            files={m.name:tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
        patches=[]
        if name=='number-library':
            number=41 if changed else 40
            files['number.c']=f'#include "offset.h"\nint zog_number(void) {{ return {number} + ZOG_OFFSET; }}\n'.encode()
            files['offset.h']=b'#define ZOG_OFFSET 0\n'
            definitions=[('number-step.patch','number.c',files['number.c'],files['number.c'].replace(str(number).encode(),str(number+1).encode())),
                         ('offset-step.patch','offset.h',files['offset.h'],b'#define ZOG_OFFSET 1\n')]
            if changed:definitions.reverse()
            for index,(filename,target,before,after) in enumerate(definitions,1):
                contents=''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='src/'+target,tofile='src/'+target)).encode()
                (root/filename).write_bytes(contents)
                spec=dict(url=(root/filename).as_uri(),sha256=sha(contents),destination=filename,archive=False)
                patches.append(dict(id=filename,order=index,source=spec,applies_to=dict(version='acceptance-1',stage='acceptance'),files=[dict(path=target,before_sha256=sha(before),after_sha256=sha(after))]))
            steps=literal(directory/'build.py')
            commands='; '.join('patch --batch --fuzz=0 -p0 -i '+p['id'] for p in patches)
            steps['build']=[['/bin/sh','-ec','echo acceptance-library-start; sleep 5; '+commands+'; cc -c src/number.c -o number.o; ar rcs libnumber.a number.o']]
            (directory/'build.py').write_text(repr(steps))
        upstream=root/'upstream'/name;upstream.mkdir(parents=True,exist_ok=True)
        for filename,data in files.items():(upstream/filename).write_bytes(data)
        for p in patches:(upstream/p['id']).write_bytes((root/p['id']).read_bytes())
        revision=git_commit(upstream,['.'],'Changed original fixture' if changed else 'Original source and patches')
        with tarfile.open(archive,'w',format=tarfile.USTAR_FORMAT) as tf:
            for filename,data in files.items():
                info=tarfile.TarInfo(filename);info.size=len(data);info.mode=0o644;tf.addfile(info,io.BytesIO(data))
        sources=[dict(url=archive.as_uri(),sha256=sha(archive.read_bytes()),destination='src',archive=True)]+[p['source'] for p in patches]
        license_record=literal(directory/'license.py');license_record['source']={k:sources[0][k] for k in ('url','sha256')}
        for e in license_record['evidence']:e['source_sha256']=sources[0]['sha256']
        (directory/'license.py').write_text(repr(license_record))
        (directory/'sources.py').write_text(repr(sources))
        (directory/'integration.py').write_text(repr(dict(stage_id='acceptance',patches=patches,patches_complete=True)))
        declaration=dict(schema=1,sources=[dict(source=s,upstream=[dict(repository=upstream.as_uri(),revision=revision,revision_type='git')]) for s in sources])
        (directory/'source-provenance.py').write_text(repr(declaration))
        monthly['packages'][name]['recipes']['acceptance']=sources;selected['packages'][name]['sources']=sources
    selected['monthly_identity']=base.identity(monthly)
    (root/'monthly.py').write_text(repr(monthly));(root/'package/commit-pin.py').write_text(repr(selected))


_original_packages=base.prepare_packages

def prepare_packages(root):
    _original_packages(root);configure_sources(root)


def recovery_guards(original):
    def checked(self,builder,package,package_dir,*args):
        binding=original(self,builder,package,package_dir,*args)
        data=self.store.get(binding['inputs'])['data']
        if not data['patches']:return binding
        evidence=builder.state.parent/'evidence';jobs=sorted((builder.state/'build-job').glob('*.json'))
        descriptor=data['patches'][0];rejections=[]
        for label,path in [('retained-patch',self.root/'artifacts'/descriptor['digest'][7:]),('staged-patch',package_dir/'source'/descriptor['name'])]:
            saved=path.read_bytes()
            for damage in ('missing','corrupt'):
                try:
                    if damage=='missing':path.unlink()
                    else:path.write_bytes(b'corrupt controlled patch')
                    try:original(self,builder,package,package_dir,*args)
                    except (ValueError,OSError,base.ImageBuildError) as error:
                        rejections.append(dict(material=label,damage=damage,error=str(error)))
                    else:raise AssertionError('changed required patch accepted')
                finally:path.write_bytes(saved)
                assert sorted((builder.state/'build-job').glob('*.json'))==jobs
        assert original(self,builder,package,package_dir,*args)==binding
        base.write_json(evidence/'patch-recovery-guards.json',dict(rejected=rejections,prepared=binding['prepared'],inputs=binding['inputs'],no_new_jobs=True))
        return binding
    return checked


def context(root,socket):
    state=root/'state';config=base.read(root/'config.json');config['retry_of']={'number-library':base.read(root/'evidence/cancelled.json')['result']}
    provenance=base.Provenance(state,**config)
    control=base.BoxControl(base.Project(root),systemd_transport=base.RootControlSystemdTransport(socket,timeout_seconds=90))
    adapter=base.BoxControlExecutionAdapter(control,execution_user_id=21001,execution_group_id=21001,startup_timeout_seconds=30,termination_grace_seconds=3,wait_timeout_seconds=120,resource_limits={'thread-count-maximum':128,'memory-maximum-bytes':768*1024**2},input_manifest_id=lambda request:base.identity(base.inventory(request.root)))
    builder=base.ImageBuild(package_dir=root/'package',state_dir=state,runner=base.BoxControlRunner(adapter,timeout=90),provenance=provenance)
    trace=base.BuildTrace(root,host_id=config['host_id'],record_project_id=config['project_id'],record_store=provenance.store.directory,controller=base.BoxControlReader(control))
    return builder,provenance,trace


def pages(call,key):
    first=call(None);page=first;rows=[]
    while True:
        rows.extend(page[key]['items'])
        if not page[key]['has_more']:break
        page=call(page[key]['next_cursor'])
    assert len({r['id'] for r in rows})==len(rows)
    return first,rows


def verify_materials(root,socket):
    builder,provenance,trace=context(root,socket);evidence=root/'evidence'
    first=base.read(evidence/'first.json');second=base.read(evidence/'second.json');third=base.read(evidence/'third.json')
    subjects=[first['binding']['build_id'],'generation:'+second['generation'],'generation:'+third['generation']]
    views=[]
    for subject in subjects:
        response,rows=pages(lambda cursor:trace.materials(subject,'number-library',cursor=cursor,limit=1),'items')
        assert response['availability']=='available' and response['artifact_verification']=='not-checked'
        inputs=provenance.store.get(response['inputs'])['data']
        assert [r['descriptor'] for r in rows if r['kind']=='patch']==inputs['patches']
        assert [r['record'] for r in rows if r['kind']=='source']==inputs['sources']
        assert all(r['upstream'][0]['revision'] for r in rows if r['kind']=='source')
        assert [r['position'] for r in rows if r['kind']=='patch']==[1,2]
        views.append(dict(subject=subject,inputs=response['inputs'],rows=rows))
    assert views[0]['inputs']==views[1]['inputs']!=views[2]['inputs']
    unchanged=trace.compare_materials(subjects[0],subjects[1],'number-library');assert unchanged['change_count']==0
    comparison,changes=pages(lambda cursor:trace.compare_materials(subjects[1],subjects[2],'number-library',limit=1,cursor=cursor),'changes')
    assert any('upstream' in r.get('changes',{}) and 'archives' in r['changes'] for r in changes)
    assert sum('position' in r.get('changes',{}) for r in changes)==2
    assert any('digest' in r.get('changes',{}).get('descriptor_fields',[]) for r in changes)
    selection=base.read_selection(builder.state/'image-build/generations'/third['generation'])
    bundle=provenance.store.bundle([selection.manifest['build_record']['record']]);report=base.inspect(bundle);assert not report['missing_records']
    assets={a['digest']:str(provenance.root/'artifacts'/a['digest'][7:]) for a in report['artifacts']}
    verified=base.verify_artifacts(bundle,assets);assert all(v['status']=='verified' for v in verified['artifact_verification'])
    export=evidence/(third['generation']+'.json');export.write_bytes(base.canonical(bundle))
    from zog import build_record
    check=subprocess.run([sys.executable,'-S','-m','zog.build_record','inspect',str(export)],cwd=evidence,env={'PYTHONPATH':str(Path(build_record.__file__).resolve().parents[2])},capture_output=True,text=True)
    assert check.returncode in (0,3) and json.loads(check.stdout)==report
    for name in ('first','second'):
        generation=base.read(evidence/(name+'.json'))['generation'];prior=evidence/(generation+'.json')
        assert base.canonical(provenance.store.bundle(base.read(prior)['roots']))==prior.read_bytes()
    # The new build's journal and executable independently witness the applied patches.
    binding=third['binding'];logs=trace.logs(binding['build_id'],'packages/number-print/test-0',limit=10)
    journal_passed=logs['availability']=='available' and '43' in json.dumps(logs['entries'])
    result=dict(passed=journal_passed,provenance_passed=True,journal_assertion_passed=journal_passed,journal_availability=logs['availability'],views=views,changes=changes,reuse_change_count=0,third_generation=dict(generation=third['generation'],root=bundle['roots'][0],records=len(bundle['records']),verified_artifacts=len(assets),complete=report['complete']),journal=logs['entries'],historical_exports_unchanged=True)
    base.write_json(evidence/'materials-result.json',result)
    assert journal_passed, 'Provenance passed, but invocation-scoped journal evidence is unavailable; see materials-result.json'


def main():
    phase=sys.argv[1]
    if phase in ('changed','materials'):
        parser=argparse.ArgumentParser();parser.add_argument('phase');parser.add_argument('--root',type=Path,required=True);parser.add_argument('--socket',type=Path,required=True);args=parser.parse_args();root=args.root.resolve()
        if phase=='materials':verify_materials(root,args.socket)
        else:
            # The old monthly bytes were deliberately changed by recovery testing.
            subprocess.run(['git','-C',str(root),'restore','monthly.py'],check=True)
            configure_sources(root,changed=True)
            revision=git_commit(root,['package','monthly.py','number-library.tar','number-print.tar'],'New explicit source and patch selection')
            config=base.read(root/'config.json');config['pin']=base.Provenance.capture_pin(root/'state',root/'monthly.py',repository=root.as_uri(),revision=revision,repository_path='monthly.py');base.write_json(root/'config.json',config)
            builder,provenance,trace=context(root,args.socket)
            seed=base.read_selection(base.read(root/'seed.json')['directory']);result=builder.verify_seed(['number-print','number-library'],host_bootstrap=seed)
            assert subprocess.check_output([result.root/'usr/bin/number-print'],text=True).strip()=='43'
            p=base.pipeline(builder.state);binding=base.package_binding(builder.state,p)
            base.write_json(root/'evidence/third.json',dict(generation=result.generation,pipeline=p.parent.name,binding=binding))
            builder.release_pipeline(p.parent.name)
        print(phase+' passed',flush=True)
    else:
        base.prepare_packages=prepare_packages
        if phase=='prepare':
            with patch.object(base.Provenance,'prepare',recovery_guards(base.Provenance.prepare)):base.main()
        else:base.main()


if __name__=='__main__':main()

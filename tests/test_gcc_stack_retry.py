import copy
import runpy
from pathlib import Path
import pytest
from jobs.gcc_test_retry import retry_request, STACK_BYTES


def records():
    req = {'build_root_id':'a', 'source_workspace_id':'a-source','output_workspace_id':'a-output',
           'command':['/bin/bash','-eu','-o','pipefail','-c','ulimit -s unlimited\nmake check'],
           'resource_limits':{'thread-count-maximum':2048,'memory-maximum-bytes':1000000000}}
    failed = {'state':'completed','exit_code':1,'process_cleanup_complete':True,'resources_released':False,'request':req}
    built = copy.deepcopy(failed); built['exit_code'] = 0
    return failed,built


def test_retry_preserves_original_and_suite():
    failed,built = records(); before=copy.deepcopy(failed)
    request=retry_request(failed,built)
    assert failed==before
    assert request['resource_limits']['stack-maximum-bytes']==STACK_BYTES
    assert request['command'][-1].endswith('make check')
    assert 'Verified stack limit' in request['command'][-1]


@pytest.mark.parametrize('change', ['running','released','different-root','bad-build','command'])
def test_retry_rejects_uncertain_inputs(change):
    f,b=records()
    if change=='running': f['process_cleanup_complete']=False
    elif change=='released': f['resources_released']=True
    elif change=='different-root': b['request']['build_root_id']='other'
    elif change=='bad-build': b['exit_code']=1
    else: f['request']['command'][-1]='echo unexpected'
    with pytest.raises(ValueError): retry_request(f,b)


def test_backend_patch_contract():
    module=runpy.run_path(str(Path(__file__).resolve().parents[1]/'handoffs/gcc-stack-limit-pass1/patch_backend.py'))
    original = 'if '+module['OLD']+':\n    pass\n'+module['ANCHOR']
    modified=module['patched'](original)
    assert "values['LimitSTACK'] = ('t', stack)" in modified
    assert "values['LimitSTACKSoft'] = ('t', stack)" in modified
    with pytest.raises(ValueError): module['patched'](modified)

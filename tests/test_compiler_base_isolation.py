import copy
import pytest
from zog.image_build import compiler_base_acceptance as ca
from zog.image_build.compiler_base_isolation import validate
from zog.image_build.errors import ImageBuildError
from test_compiler_base_acceptance import signed_fixture

def test_explicit_kernel_mounts_do_not_claim_no_host_mounts(tmp_path):
    b,s,c,a,sign=signed_fixture(tmp_path)
    iso=c['native_probe']['isolation']
    for path,kind in [('/sys','sysfs'),('/sys/fs/cgroup','cgroup2')]:
        iso['mounts'].append({'mount':path,'root':'/','type':kind,'source':kind,'options':'rw,nosuid,nodev,noexec'})
    assert ca.resolve(b,s,sign())['generation_kind']=='image'
    assert 'pivot_root' not in iso and 'host_mounts_visible' not in iso

@pytest.mark.parametrize('mutation',['host_usr','host_sys_bind','root_rw','wrong_root','same_net','same_mnt','eth0','caps','root_uid','wrong_job','wrong_files','duplicate_mount','invented_boolean','no_witness'])
def test_bad_observations_denied_even_with_valid_signature(tmp_path,mutation):
    b,s,c,a,sign=signed_fixture(tmp_path);i=c['native_probe']['isolation']
    if mutation=='host_usr':i['mounts'].append({'mount':'/usr','root':'/usr','type':'xfs','source':'/dev/host','options':'ro'})
    elif mutation=='host_sys_bind':i['mounts'].append({'mount':'/sys','root':'/','type':'xfs','source':'/dev/host','options':'ro'})
    elif mutation=='root_rw':i['mounts'][0]['options']='rw'
    elif mutation=='wrong_root':i['mounts'][0]['root']='/other/root'
    elif mutation=='same_net':i['network_namespace']=i['host_network_namespace']
    elif mutation=='same_mnt':i['mount_namespace']=i['host_mount_namespace']
    elif mutation=='eth0':i['network_interfaces'].append('eth0')
    elif mutation=='caps':i['effective_capabilities']='0000000000000001'
    elif mutation=='root_uid':i['uid']=0
    elif mutation=='wrong_job':i['invocation_id']='other'
    elif mutation=='wrong_files':i['selected_files']=copy.deepcopy(i['selected_files']);i['selected_files']['compiler']['sha256']='sha256:'+'0'*64
    elif mutation=='duplicate_mount':i['mounts'].append(copy.deepcopy(i['mounts'][0]))
    elif mutation=='invented_boolean':i['pivot_root']=True
    elif mutation=='no_witness':i['witness_sha256']=None
    with pytest.raises(ImageBuildError):ca.resolve(b,s,sign())

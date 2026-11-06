"""Signed observations of a compiler job, not a claim of total Host isolation.

The native owner authenticates the witness before signing. Pseudo filesystems
are explicitly visible; this profile makes no syscall or escape-proof claim.
"""
import re
from pathlib import PurePosixPath
from .errors import ImageBuildError

SCHEMA = 'image-build-compiler-isolation-v2'
PROFILE = 'selected-root-kernel-mounts-v1'
PSEUDO = {
    '/dev': 'tmpfs', '/dev/pts': 'devpts', '/dev/shm': 'tmpfs',
    '/dev/mqueue': 'mqueue', '/dev/hugepages': 'hugetlbfs',
    '/proc': 'proc', '/sys': 'sysfs', '/sys/kernel/security': 'securityfs',
    '/sys/fs/cgroup': 'cgroup2', '/sys/fs/pstore': 'pstore',
    '/sys/firmware/efi/efivars': 'efivarfs', '/sys/fs/bpf': 'bpf',
    '/sys/kernel/debug': 'debugfs', '/sys/kernel/tracing': 'tracefs',
    '/sys/kernel/config': 'configfs', '/sys/fs/fuse/connections': 'fusectl',
    '/run': 'tmpfs', '/run/systemd/incoming': 'tmpfs', '/tmp': 'tmpfs',
}
FIELDS = {'schema','profile','witness_sha256','runtime_id','invocation_id',
          'uid','gid','effective_capabilities','no_new_privileges',
          'mount_namespace','host_mount_namespace','network_namespace',
          'host_network_namespace','network_interfaces','imported_root',
          'source_root','output_root','mounts','selected_files'}

def deny():
    raise ImageBuildError('compiler base NOT ACCEPTED: invalid observed isolation')

def absolute(value):
    return (type(value) is str and value.startswith('/') and len(value)<1024
            and PurePosixPath(value).as_posix()==value
            and '..' not in PurePosixPath(value).parts and '\x00' not in value)

def validate(value, completion, installed_paths):
    if type(value) is not dict or set(value)!=FIELDS: deny()
    if value['schema']!=SCHEMA or value['profile']!=PROFILE: deny()
    if not isinstance(value['witness_sha256'],str) or not re.fullmatch('sha256:[0-9a-f]{64}',value['witness_sha256']): deny()
    for name in ('runtime_id','invocation_id'):
        if value[name]!=completion[name]: deny()
    if any(type(value[k]) is not int or value[k]<=0 for k in ('uid','gid')): deny()
    if value['effective_capabilities']!='0000000000000000' or value['no_new_privileges'] is not True: deny()
    for kind in ('mount','network'):
        a,b=value[kind+'_namespace'],value['host_'+kind+'_namespace']
        prefix='mnt' if kind=='mount' else 'net'
        if (type(a) is not str or type(b) is not str or a==b or
            not re.fullmatch(prefix+r':\[[0-9]+\]',a) or
            not re.fullmatch(prefix+r':\[[0-9]+\]',b)): deny()
    if value['network_interfaces']!=['lo']: deny()
    for name in ('imported_root','source_root','output_root'):
        if not absolute(value[name]) or value[name]=='/': deny()
    if len({value[k] for k in ('imported_root','source_root','output_root')})!=3: deny()
    if type(value['selected_files']) is not dict or set(value['selected_files'])!={'compiler','linker','libc_header'}: deny()
    for role, item in value['selected_files'].items():
        if item!=installed_paths[role]: deny()
    mounts=value['mounts']
    if type(mounts) is not list or not 1<=len(mounts)<=40: deny()
    seen=set()
    for m in mounts:
        if type(m) is not dict or set(m)!={'mount','root','type','source','options'}: deny()
        path=m['mount']
        if not absolute(path) or path in seen: deny()
        seen.add(path)
        if not absolute(m['root']) or type(m['source']) is not str or not 0<len(m['source'])<1024: deny()
        if type(m['options']) is not str: deny()
        options=m['options'].split(',')
        if not options or any(not re.fullmatch('[a-z0-9_=.-]+',x) for x in options): deny()
        if len(set(options))!=len(options) or ('ro' in options)==('rw' in options): deny()
        if path=='/':
            if m['root']!=value['imported_root'] or 'ro' not in options or m['type'] not in ('xfs','ext4','btrfs','overlay'): deny()
        elif path=='/root':
            if m['root']!=value['imported_root']+'/root' or m['type'] not in ('xfs','ext4','btrfs','overlay'): deny()
        elif path in ('/image-build/source','/image-build/output'):
            key='source_root' if path.endswith('source') else 'output_root'
            if m['root']!=value[key] or m['type'] not in ('xfs','ext4','btrfs','overlay'): deny()
        elif path=='/var/tmp':
            # systemd PrivateTmp backing, never an arbitrary Host bind.
            if not m['root'].startswith('/var/tmp/systemd-private-') or not m['root'].endswith('/tmp') or m['type'] not in ('xfs','ext4','btrfs','tmpfs'): deny()
        elif path in PSEUDO:
            if m['type']!=PSEUDO[path]: deny()
            if path=='/tmp':
                if not m['root'].startswith('/systemd-private-') or not m['root'].endswith('/tmp'): deny()
            elif path=='/run/systemd/incoming':
                if not m['root'].startswith('/systemd/propagate/') or 'ro' not in options: deny()
            elif m['root']!='/': deny()
        else:
            # In particular deny /usr, /lib, /lib64 and nested Host overlays.
            deny()
    if not {'/','/proc','/image-build/source','/image-build/output'}.issubset(seen): deny()
    return True

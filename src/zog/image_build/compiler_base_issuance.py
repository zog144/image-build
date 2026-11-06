"""Compiler-purpose, exact-claim signing; no enrollment or key generation.

The protected owner installs a reviewed approval after operator consent. File
ownership alone does not prove enrollment. This command never creates policy,
changes a generation, dispatches a job, or selects Task C signing authority.
"""
import argparse
import base64
import os
import stat
import re
import tempfile
from pathlib import Path
from . import compiler_base_acceptance as ca

PURPOSE = 'compiler-base-capability'
APPROVAL = 'image-build-compiler-signing-approval-v1'

def envelope(claim, authority, approval, key):
    """Pure signing boundary; callers must independently authenticate all inputs."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    ca.exact(approval, ('schema','purpose','claim_sha256','authority_sha256',
                       'key_id','reader_revision'), 'compiler signing approval')
    if (approval['schema']!=APPROVAL or approval['purpose']!=PURPOSE or
        approval['claim_sha256']!=ca.digest(ca.canonical(claim)) or
        approval['authority_sha256']!=ca.digest(ca.canonical(authority)) or
        approval['key_id']!=authority['key_id'] or
        type(approval['reader_revision']) is not str or
        not re.fullmatch('[0-9a-f]{40}',approval['reader_revision'])):
        ca.deny('no exact compiler-purpose approval')
    public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    if public!=authority['ed25519_public_key']:
        ca.deny('signer differs from enrolled compiler key')
    if claim.get('schema')!=ca.SCHEMA or claim.get('status')!='independently-accepted-for-compiler-use':
        ca.deny('not a compiler capability claim')
    for field in ('host_id','installation_id','state_volume_id','project_id','execution_environment_sha256'):
        if claim.get(field)!=authority[field]:ca.deny('signing scope differs from enrolled authority')
    ca.validate_probe(claim['native_probe'],claim)
    return ca.canonical({'schema':ca.SCHEMA,'key_id':authority['key_id'],
                         'claim':claim,'signature':base64.b64encode(
                             key.sign(ca.DOMAIN+ca.canonical(claim))).decode('ascii')})

def protected_file(path, *, maximum=65536):
    path=Path(path)
    if not path.is_absolute():ca.deny('protected issuer path must be absolute')
    for parent in path.parents:
        st=parent.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or st.st_mode&0o022:
            ca.deny('issuer parent is not protected')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode) not in (0o400,0o600) or st.st_size>maximum:
            ca.deny('issuer input is not a protected bounded file')
        raw=os.read(fd,maximum+1)
        if len(raw)>maximum:ca.deny('issuer input exceeds bound')
        return raw
    finally:os.close(fd)

def publish(directory,generation,raw):
    """Atomic create-only publication; identical rerun reopens existing bytes."""
    if type(generation) is not str or not ca.HEX64.fullmatch(generation):ca.deny('invalid generation receipt name')
    directory=Path(directory); target=directory/(generation+'.json')
    fd,name=tempfile.mkstemp(prefix='.compiler-receipt-',dir=directory)
    try:
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),0o400);stream.write(raw);stream.flush();os.fsync(stream.fileno())
        try:os.link(name,target,follow_symlinks=False)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes()!=raw:ca.deny('different receipt already exists; preserve original')
        dfd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:os.unlink(name)
    if target.is_symlink() or target.read_bytes()!=raw:ca.deny('receipt readback differs')
    return ca.digest(raw)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('authority','approval','claim','private-key','reader-revision'):
        p.add_argument('--'+field,required=True)
    args=p.parse_args(argv)
    if os.geteuid()!=0:ca.deny('compiler issuer must run as installed protected owner')
    # JSON is canonical, duplicate-free, bounded, and root-owned. Private seed
    # never appears in argv, environment, output or a generated receipt.
    def document(path):
        raw=protected_file(path)
        import json
        value=json.loads(raw,object_pairs_hook=ca._no_duplicates)
        if ca.canonical(value)!=raw:ca.deny('issuer input is not canonical JSON')
        return value
    authority=document(args.authority);approval=document(args.approval);claim=document(args.claim)
    ca.native_authority(args.authority)
    directory=Path(authority['receipt_directory'])
    for parent in (directory,*directory.parents):
        st=parent.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or st.st_mode&0o022:
            ca.deny('receipt directory ancestry is not protected')
    if approval['reader_revision']!=args.reader_revision:ca.deny('installed reader selection differs from approval')
    # Native owner attests executable/RECORD bytes separately; an argv revision
    # is not self-attestation and cannot replace that installation evidence.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    seed=protected_file(args.private_key,maximum=32)
    if len(seed)!=32:ca.deny('expected enrolled raw Ed25519 seed')
    raw=envelope(claim,authority,approval,Ed25519PrivateKey.from_private_bytes(seed))
    print(publish(authority['receipt_directory'],claim['generation_id'],raw))

if __name__=='__main__':main()

import json
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from zog.image_build import compiler_base_acceptance as ca
from zog.image_build import compiler_base_issuance as ci
from zog.image_build.errors import ImageBuildError
from test_compiler_base_acceptance import signed_fixture

def setup_issuance(tmp_path):
    b,s,c,a,_=signed_fixture(tmp_path);key=Ed25519PrivateKey.generate()
    a['ed25519_public_key']=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    approval={'schema':ci.APPROVAL,'purpose':ci.PURPOSE,'claim_sha256':ca.digest(ca.canonical(c)),
              'authority_sha256':ca.digest(ca.canonical(a)),'key_id':a['key_id'],'reader_revision':'a'*40}
    return b,s,c,a,approval,key

def test_exact_approval_sign_publish_and_real_resolve(tmp_path):
    b,s,c,a,p,k=setup_issuance(tmp_path)
    raw=ci.envelope(c,a,p,k);digest=ci.publish(a['receipt_directory'],s.generation,raw)
    assert ci.publish(a['receipt_directory'],s.generation,raw)==digest
    assert ca.resolve(b,s,digest)['generation_kind']=='image'
    with pytest.raises(ImageBuildError):ci.publish(a['receipt_directory'],s.generation,b'changed')

@pytest.mark.parametrize('change',['purpose','claim','authority','key','reader'])
def test_task_c_or_changed_scope_cannot_sign(tmp_path,change):
    b,s,c,a,p,k=setup_issuance(tmp_path)
    if change=='purpose':p['purpose']='task-c-event'
    elif change=='claim':c['generation_id']='b'*64
    elif change=='authority':a['installation_id']='other'
    elif change=='key':k=Ed25519PrivateKey.generate()
    elif change=='reader':p['reader_revision']='unreviewed'
    with pytest.raises(ImageBuildError):ci.envelope(c,a,p,k)

def test_receipt_symlink_is_never_followed(tmp_path):
    b,s,c,a,p,k=setup_issuance(tmp_path)
    raw=ci.envelope(c,a,p,k)
    from pathlib import Path
    outside=tmp_path/'outside';outside.write_bytes(raw)
    (Path(a['receipt_directory'])/(s.generation+'.json')).symlink_to(outside)
    with pytest.raises(ImageBuildError):ci.publish(a['receipt_directory'],s.generation,raw)
    assert outside.read_bytes()==raw

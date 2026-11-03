"""Additional independent native evidence source negative tests (synthetic only)."""
import importlib.util
import stat
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location(
    "resident_original_fixtures",ROOT/"tests/test_resident_b_installed_evidence.py")
original=importlib.util.module_from_spec(sp);sp.loader.exec_module(original)
v=original.v

def test_python_312_executable_and_all_three_extension_outputs_are_required(tmp_path):
    root,claim,key,sign,selection,upstream=original.fixture(tmp_path)
    for name in ("usr/bin/python3.12",
                 "usr/lib/libpython3.12.so.1.0",
                 "usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so",
                 "usr/lib/python3.12/lib-dynload/_sqlite3.cpython-312-x86_64-linux-gnu.so",
                 "usr/lib/python3.12/lib-dynload/_hashlib.cpython-312-x86_64-linux-gnu.so"):
        reduced={**claim,"files":[r for r in claim["files"] if r["path"]!=name]}
        with pytest.raises(v.EvidenceDenied,match="incomplete installed inventory"):
            original.run(root,reduced,key,sign,selection,upstream)

def test_no_arbitrary_python_extension_abi(tmp_path):
    root,c,key,sign,selection,upstream=original.fixture(tmp_path)
    c["modules"]["_ssl"]="usr/lib/python3.12/lib-dynload/_ssl.cpython-315-x86_64-linux-gnu.so"
    with pytest.raises(v.EvidenceDenied,match="SOABI"):
        original.run(root,c,key,sign,selection,upstream)

def test_even_validly_signed_synthetic_wheel_cannot_substitute_metadata(tmp_path):
    root,c,key,sign,selection,upstream=original.fixture(tmp_path)
    p=root/"usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/METADATA"
    p.write_text("Metadata-Version: 2.4\nName: box-control\nVersion: 0.1.0\nRequires-Dist: host-only==1.0\n")
    with pytest.raises(v.EvidenceDenied,match="Requires-Dist"):
        original.run(root,c,key,sign,selection,upstream)

def test_entry_point_and_wheel_tag_are_part_of_checked_bytes(tmp_path):
    root,c,key,sign,selection,upstream=original.fixture(tmp_path)
    ep=root/"usr/lib/python3.12/site-packages/root_control-0.1.0.dist-info/entry_points.txt"
    ep.write_text("[console_scripts]\nroot-control = dangerous:main\n")
    with pytest.raises(v.EvidenceDenied,match="console script"):
        original.run(root,c,key,sign,selection,upstream)
    root,c,key,sign,selection,upstream=original.fixture(tmp_path/"tag")
    wheel=root/"usr/lib/python3.12/site-packages/box_control-0.1.0.dist-info/WHEEL"
    wheel.write_text("Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp315-cp315-linux_x86_64\n")
    with pytest.raises(v.EvidenceDenied,match="ABI"):
        original.run(root,c,key,sign,selection,upstream)

def test_privileged_systemd_unit_must_match_exact_source_not_just_contains_root(tmp_path):
    root,c,key,sign,selection,upstream=original.fixture(tmp_path)
    unit=root/"usr/lib/systemd/system/zog-root-control.service"
    original_bytes=unit.read_bytes()
    unit.write_bytes(original_bytes.replace(b"Restart=no",b"Restart=always"))
    with pytest.raises(v.EvidenceDenied,match="exact reviewed disabled unit"):
        original.run(root,c,key,sign,selection,upstream)

def test_synthetic_root_is_rejected_by_native_mount_gate(tmp_path):
    root,c,key,sign,selection,upstream=original.fixture(tmp_path)
    ctx={"schema":"zog-host-install-resident-b-native-mount-v1",
         "rootfs_device":root.stat().st_dev,"state_device":root.stat().st_dev+1,
         "state_volume_id":"synthetic-state-identity-0001",
         "rootfs_generation_id":"a"*64,"socket_gid":1234}
    state=tmp_path/"STATE";state.mkdir()
    with pytest.raises(v.EvidenceDenied,match="actual distinct mounted volumes"):
        v.verify_protected_mounts(root,state,protected_context=ctx)
    ctx["socket_gid"]=0
    with pytest.raises(v.EvidenceDenied,match="socket numeric group"):
        v.verify_protected_mounts(root,state,protected_context=ctx)

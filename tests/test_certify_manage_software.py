import hashlib
from pathlib import Path

import pytest

from zog.image_build.certify_manage_software import (
    APPLICATION,
    CERTBOT,
    CLOUDFLARE,
    CORE,
    LOCK_CONTRACT,
    PYTHON,
    PYTHON_VERSION,
    REVIEWED_RUNTIME_SOURCES,
    SITE,
    begin,
    finalize,
    materialize_launchers,
    validate_lock,
    verify_staging,
)
from zog.image_build.errors import ImageBuildError


def descriptor(*, libraries=None, architecture="x86_64"):
    return {
        "schema": 1,
        "mount_contract": "applications-v1",
        "architecture": architecture,
        "python": {
            "implementation": "cpython",
            "version": PYTHON_VERSION,
            "soabi": "cpython-315-x86_64-linux-gnu",
        },
        "libraries": sorted(libraries or ["libc.so.6", "libcrypto.so.4"]),
    }


def runtime_lock(profile="http-01"):
    versions = dict(CORE)
    if profile == "cloudflare-dns-01":
        versions.update(CLOUDFLARE)
    packages = []
    for name, version in sorted(versions.items()):
        packages.append(
            {
                "name": name,
                "version": version,
                "source": dict(REVIEWED_RUNTIME_SOURCES.get(name, {
                    "url": f"https://example.invalid/{name}-{version}.tar.gz",
                    "sha256": hashlib.sha256(name.encode()).hexdigest(),
                })),
                "notices": [f"share/licenses/{name}/LICENSE"],
            }
        )
    return {
        "contract": LOCK_CONTRACT,
        "profile": profile,
        "certify_manage_revision": "a" * 40,
        "compatibility": descriptor(),
        "packages": packages,
    }


def populate(root, lock):
    site = root / SITE
    site.mkdir(parents=True)
    for record in lock["packages"]:
        name = record["name"]
        dist = site / (name.replace("-", "_") + "-" + record["version"] + ".dist-info")
        dist.mkdir()
        (dist / "METADATA").write_text(
            f"Metadata-Version: 2.4\nName: {name}\nVersion: {record['version']}\n"
        )
        for notice in record["notices"]:
            path = root / notice
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{name} fixture license\n")

    modules = {
        "zog/certify_manage/__init__.py": "__version__='0.1.0'\n",
        "certbot/__init__.py": "__version__='5.8.0'\n",
        "acme/__init__.py": "__version__='5.8.0'\n",
        "cryptography/__init__.py": "__version__='50.0.2'\n",
        "cffi/__init__.py": "__version__='2.1.1'\n",
        "pycparser/__init__.py": "__version__='3.0'\n",
        "_cffi_backend.cpython-315-x86_64-linux-gnu.so": "fixture ELF\n",
        "configobj/__init__.py": "__version__='5.0.9'\n",
        "certifi/cacert.pem": "fixture CA bundle\n",
        "cryptography/hazmat/bindings/_rust.abi3.so": "fixture ELF\n",
    }
    if lock["profile"] == "cloudflare-dns-01":
        modules.update(
            {
                "certbot_dns_cloudflare/__init__.py": "__version__='5.8.0'\n",
                "cloudflare/__init__.py": "__version__='5.6.0'\n",
                "pydantic_core/_pydantic_core.cpython-315-x86_64-linux-gnu.so": "fixture ELF\n",
            }
        )
    for relative, content in modules.items():
        path = site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    materialize_launchers(root)


def prepared(tmp_path, profile="http-01"):
    state = tmp_path / "state"
    lock = runtime_lock(profile)
    operation = begin(state, "certify-a", lock)
    populate(operation.root, lock)
    return state, lock, operation


@pytest.mark.parametrize("profile", ["http-01", "cloudflare-dns-01"])
def test_exact_runtime_lock_and_immutable_publication(profile, tmp_path):
    state, lock, operation = prepared(tmp_path, profile)
    assert validate_lock(lock)["profile"] == profile
    assert verify_staging(operation.root, lock)["profile"] == profile
    rootfs = descriptor(libraries=["libc.so.6", "libcrypto.so.4", "libssl.so.4"])
    result = finalize(state, operation.operation, lock, rootfs)
    assert result["contract"] == "image-build-certify-manage-software-result-v1"
    assert result["commands"] == {"python": PYTHON, "certbot": CERTBOT}
    assert result["binding"]["application"] == APPLICATION
    assert result["binding"]["mount_point"] == "/applications/certify-manage"
    assert result["binding"]["rootfs_compatibility"] == rootfs
    assert result["binding"]["reclamation_protection"]["view"] == result["view"]
    assert result["artifact"] in result["binding"]["reclamation_protection"]["artifacts"]
    assert finalize(state, operation.operation, lock, rootfs) == result


def test_lock_rejects_missing_extra_or_changed_dependency(tmp_path):
    lock = runtime_lock()
    lock["packages"].pop()
    with pytest.raises(ImageBuildError, match="dependency closure"):
        validate_lock(lock)

    lock = runtime_lock()
    lock["packages"] = [record for record in lock["packages"] if record["name"] != "cffi"]
    with pytest.raises(ImageBuildError, match="dependency closure"):
        validate_lock(lock)

    lock = runtime_lock()
    lock["packages"][0]["version"] = "999"
    with pytest.raises(ImageBuildError, match="package version"):
        validate_lock(lock)

    lock = runtime_lock()
    lock["packages"][0]["source"]["sha256"] = "not-a-hash"
    with pytest.raises(ImageBuildError, match="source identity"):
        validate_lock(lock)

    lock = runtime_lock()
    cffi = next(record for record in lock["packages"] if record["name"] == "cffi")
    cffi["source"] = {
        "url": "https://example.invalid/cffi-2.1.1.tar.gz",
        "sha256": "0" * 64,
    }
    with pytest.raises(ImageBuildError, match="unreviewed certify-manage source identity: cffi"):
        validate_lock(lock)

    lock = runtime_lock()
    lock["compatibility"]["python"]["version"] = "3.14.7"
    with pytest.raises(ImageBuildError, match="CPython 3.15"):
        validate_lock(lock)


def test_installed_dependency_set_and_launchers_are_exact(tmp_path):
    state, lock, operation = prepared(tmp_path)
    site = operation.root / SITE
    metadata = next(site.glob("certbot-*.dist-info/METADATA"))
    metadata.write_text("Metadata-Version: 2.4\nName: certbot\nVersion: 5.9.0\n")
    with pytest.raises(ImageBuildError, match="dependency closure"):
        verify_staging(operation.root, lock)

    state, lock, operation = prepared(tmp_path / "launcher")
    (operation.root / "bin/python3").write_text("#!/bin/sh\nexit 0\n")
    with pytest.raises(ImageBuildError, match="launcher changed"):
        verify_staging(operation.root, lock)


def test_native_extensions_and_profile_selection_fail_closed(tmp_path):
    state, lock, operation = prepared(tmp_path)
    native = next((operation.root / SITE).glob("cryptography/hazmat/bindings/_rust*.so"))
    native.unlink()
    with pytest.raises(ImageBuildError, match="cryptography native extension"):
        verify_staging(operation.root, lock)

    state, lock, operation = prepared(tmp_path / "cffi-native")
    native = next((operation.root / SITE).glob("_cffi_backend*.so"))
    native.unlink()
    with pytest.raises(ImageBuildError, match="CFFI native extension"):
        verify_staging(operation.root, lock)

    state, lock, operation = prepared(tmp_path / "http-extra")
    extra = operation.root / SITE / "cloudflare"
    extra.mkdir()
    (extra / "__init__.py").write_text("unexpected\n")
    with pytest.raises(ImageBuildError, match="Cloudflare plugin"):
        verify_staging(operation.root, lock)

    state, lock, operation = prepared(tmp_path / "cloudflare", "cloudflare-dns-01")
    native = next((operation.root / SITE).glob("pydantic_core/_pydantic_core*.so"))
    native.unlink()
    with pytest.raises(ImageBuildError, match="pydantic-core native extension"):
        verify_staging(operation.root, lock)


@pytest.mark.parametrize(
    "relative",
    [
        "etc/policy.json",
        "var/lib/zog-certify-manage/privkey.pem",
        "run/zog-host/certify-policy/policy.json",
    ],
)
def test_mutable_policy_and_certificate_state_never_enter_artifact(tmp_path, relative):
    state, lock, operation = prepared(tmp_path)
    path = operation.root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("forbidden\n")
    with pytest.raises(ImageBuildError, match="mutable|secret"):
        verify_staging(operation.root, lock)


def test_missing_notice_and_rootfs_incompatibility_block_publication(tmp_path):
    state, lock, operation = prepared(tmp_path)
    notice = operation.root / lock["packages"][0]["notices"][0]
    notice.unlink()
    with pytest.raises(ImageBuildError, match="notice"):
        verify_staging(operation.root, lock)

    state, lock, operation = prepared(tmp_path / "compat")
    with pytest.raises(ImageBuildError, match="incompatible"):
        finalize(
            state,
            operation.operation,
            lock,
            descriptor(architecture="aarch64"),
        )

import json
from pathlib import Path

import pytest

from zog.image_build import ImageBuild, read_selection
from zog.image_build.accepted_image_derivation import (
    ACCEPTANCE_CONTRACT,
    CERTIFY_MANAGE_RECOVERY,
    CONTRACT,
    FIELD,
    GAP_CONTRACT,
    derive,
    operation_directory,
    validate_manifest,
)
from zog.image_build.application_data_targets import (
    FIELD as DATA_TARGET_FIELD,
    definition as data_target_definition,
)
from zog.image_build.errors import ImageBuildError
from zog.image_build.filesystem import digest, inventory
from zog.image_build.immutable_objects import report as immutable_report
from zog.image_build.rootfs_compatibility import (
    FIELD as COMPATIBILITY_FIELD,
    derive as derive_compatibility,
)


SOURCE_REVISION = "a" * 40


def fixture(tmp_path):
    state = tmp_path / "state"
    package_dir = tmp_path / "packages"
    package_dir.mkdir(parents=True)
    builder = ImageBuild(
        package_dir=package_dir,
        state_dir=state,
        maximum_generations=16,
        provenance=None,
    )
    root = tmp_path / "parent-root"
    root.mkdir()
    (root / "var").mkdir(mode=0o755)
    (root / "payload").write_bytes(b"accepted payload\n")
    outputs = inventory(root)
    compatibility = derive_compatibility(
        {"fixture": {"root": str(root), "outputs": outputs}},
        "x86_64",
    )
    base = "f" * 64
    components = {
        "alpha": str(tmp_path / "missing-alpha"),
        "beta": str(tmp_path / "missing-beta"),
    }
    inputs = {
        "schema": 2,
        "kind": "image",
        "architecture": "x86_64",
        "publication": {
            "policy": "fixture-historical-runtime",
            "base": base,
            "components": components,
        },
        COMPATIBILITY_FIELD: compatibility,
    }
    parent = builder._publish(
        root,
        inputs,
        "image",
        {
            COMPATIBILITY_FIELD: compatibility,
            "purpose": "fixture-accepted-runtime",
            "host_boot_ready": False,
        },
    )
    profile = {
        "profile": "fixture-accepted-image-recovery",
        "parent_generation": parent.generation,
        "parent_manifest_sha256": digest(parent.root.parent / "manifest.json"),
        "parent_output_count": len(parent.manifest["outputs"]),
        "missing_base_generation": base,
        "missing_component_output_count": len(components),
        "required_new_target": "/var/lib/zog-certify-manage",
        "evidence": {
            "source": "retained-review-record",
            "revision": "b" * 40,
            "path": "image-build/verification/fixture.md",
        },
    }
    return builder, parent, profile, components


def test_production_recovery_profile_binds_recorded_parent_and_gap():
    assert CERTIFY_MANAGE_RECOVERY == {
        "profile": "certify-manage-runtime-generation-recovery-2026-10-22",
        "parent_generation":
            "3805294fc8ccd9589aa75d3a6c5cb9367b7baf84b6ce131a84adafed7d34f9dc",
        "parent_manifest_sha256":
            "ebc8b392d9faf628f4264c64b011cf4f25ce1efb6f1dae74876635bff4bc2132",
        "parent_output_count": 40945,
        "missing_base_generation":
            "f07ee7f1422c04af4f1d5c5c5685bea9efc9cf046214737e6fb82e46ed063513",
        "missing_component_output_count": 54,
        "required_new_target": "/var/lib/zog-certify-manage",
        "evidence": {
            "source": "retained-review-record",
            "revision": "1347dbf3021de2cdcd07cd0ae7b69ea5362f853f",
            "path": (
                "image-build/verification/certbot-offline-wheels-2026-10-22/"
                "runtime-generation-recovery.md"
            ),
        },
    }


def test_derivation_preserves_parent_payload_and_abi_and_adds_empty_targets(tmp_path):
    builder, parent, profile, components = fixture(tmp_path)
    builder._activate(parent, "active")
    result = derive(builder, "certify-runtime", SOURCE_REVISION, profile)
    selected = read_selection(
        builder.state / "image-build" / "generations" / result["generation"]
    )

    assert selected.generation != parent.generation
    assert (builder.state / "image-build" / "active").resolve() == parent.root.parent
    assert selected.manifest[COMPATIBILITY_FIELD] == parent.manifest[COMPATIBILITY_FIELD]
    assert selected.manifest["inputs"][COMPATIBILITY_FIELD] == parent.manifest[COMPATIBILITY_FIELD]
    assert selected.manifest[DATA_TARGET_FIELD] == data_target_definition()
    assert selected.manifest["inputs"][DATA_TARGET_FIELD] == data_target_definition()
    assert selected.manifest["verification_inherited_from"] == parent.generation
    assert selected.manifest["historical_provenance_complete"] is False
    assert "build_record" not in selected.manifest

    parent_records = {row["path"]: row for row in parent.manifest["outputs"]}
    derived_records = {row["path"]: row for row in selected.manifest["outputs"]}
    for name, row in parent_records.items():
        assert derived_records[name] == row
    assert (selected.root / "payload").read_bytes() == b"accepted payload\n"

    expected_modes = {
        "var/lib": 0o755,
        "var/lib/archive-mirror": 0o755,
        "var/lib/station-access": 0o755,
        "var/lib/zog-certify-manage": 0o700,
    }
    assert set(derived_records) - set(parent_records) == set(expected_modes)
    for name, mode in expected_modes.items():
        path = selected.root / name
        assert path.is_dir() and not path.is_symlink()
        if name != "var/lib":
            assert list(path.iterdir()) == []
        assert path.stat().st_mode & 0o7777 == mode
    assert {path.name for path in (selected.root / "var/lib").iterdir()} == {
        "archive-mirror", "station-access", "zog-certify-manage"
    }

    derivation = selected.manifest[FIELD]
    assert derivation["contract"] == CONTRACT
    assert derivation["source_revision"] == SOURCE_REVISION
    assert derivation["parent"]["generation"] == parent.generation
    assert derivation["historical_provenance"] == {
        "contract": GAP_CONTRACT,
        "status": "incomplete",
        "parent_generation": parent.generation,
        "missing": {
            "inherited_base_generation": profile["missing_base_generation"],
            "component_output_roots": {
                name: components[name] for name in sorted(components)
            },
        },
        "missing_component_output_count": 2,
        "evidence": profile["evidence"],
        "claims_forbidden": [
            "historical-package-output-closure-complete",
            "historical-base-generation-available",
            "fresh-runtime-verification",
            "parent-is-toolchain",
        ],
    }
    acceptance = derivation["acceptance"]
    assert acceptance["contract"] == ACCEPTANCE_CONTRACT
    assert acceptance["preserved_parent_entries"] == len(parent_records)
    assert acceptance["parent_manifest_sha256"] == profile["parent_manifest_sha256"]
    assert acceptance["compatibility_identity"] == derivation["parent"]["compatibility_identity"]
    assert result["historical_provenance_complete"] is False
    assert derive(builder, "certify-runtime", SOURCE_REVISION, profile) == result


def test_manifest_validator_refuses_complete_provenance_or_fake_build_record(tmp_path):
    builder, _parent, profile, _components = fixture(tmp_path)
    result = derive(builder, "contract-test", SOURCE_REVISION, profile)
    selected = read_selection(
        builder.state / "image-build" / "generations" / result["generation"]
    )
    details = json.loads(json.dumps(selected.manifest))
    details["historical_provenance_complete"] = True
    with pytest.raises(ImageBuildError, match="publication claims changed"):
        validate_manifest(selected.manifest["inputs"], details)

    details = json.loads(json.dumps(selected.manifest))
    details["build_record"] = {"forged": True}
    with pytest.raises(ImageBuildError, match="publication claims changed"):
        validate_manifest(selected.manifest["inputs"], details)


def test_parent_manifest_and_payload_are_revalidated_before_derivation(tmp_path):
    builder, parent, profile, _components = fixture(tmp_path)
    manifest_path = parent.root.parent / "manifest.json"
    manifest_path.write_text(manifest_path.read_text() + "\n")
    with pytest.raises(ImageBuildError, match="manifest digest differs"):
        derive(builder, "manifest-drift", SOURCE_REVISION, profile)

    # Restore the canonical bytes through a fresh fixture for the payload test.
    builder, parent, profile, _components = fixture(tmp_path / "payload-case")
    (parent.root / "payload").write_text("changed")
    with pytest.raises(ImageBuildError, match="generation outputs changed"):
        derive(builder, "payload-drift", SOURCE_REVISION, profile)


def test_recovery_shortcut_refuses_inputs_that_have_become_available(tmp_path):
    builder, _parent, profile, components = fixture(tmp_path)
    Path(components["alpha"]).mkdir()
    with pytest.raises(ImageBuildError, match="component outputs are available"):
        derive(builder, "components-returned", SOURCE_REVISION, profile)

    builder, _parent, profile, _components = fixture(tmp_path / "base-case")
    recovered = (
        builder.state
        / "image-build"
        / "generations"
        / profile["missing_base_generation"]
    )
    recovered.mkdir(parents=True)
    with pytest.raises(ImageBuildError, match="historical base generation is available"):
        derive(builder, "base-returned", SOURCE_REVISION, profile)


def test_frozen_operation_rejects_changed_source_revision(tmp_path):
    builder, _parent, profile, _components = fixture(tmp_path)
    derive(builder, "frozen", SOURCE_REVISION, profile)
    with pytest.raises(ImageBuildError, match="frozen accepted-image derivation changed"):
        derive(builder, "frozen", "c" * 40, profile)


def test_interrupted_publication_protects_parent_and_recovers_same_operation(
    tmp_path, monkeypatch
):
    builder, parent, profile, _components = fixture(tmp_path)
    original = builder._publish

    def interrupted(*_args, **_kwargs):
        raise KeyboardInterrupt("simulated lost publication call")

    monkeypatch.setattr(builder, "_publish", interrupted)
    with pytest.raises(KeyboardInterrupt):
        derive(builder, "recoverable", SOURCE_REVISION, profile)

    operation = operation_directory(builder.state, "recoverable")
    assert (operation / "intent.json").is_file()
    assert (operation / "acceptance.json").is_file()
    assert not (operation / "result.json").exists()
    state = immutable_report(builder.state)
    parent_row = next(
        row for row in state["objects"]
        if row["kind"] == "generation" and row["id"] == parent.generation
    )
    assert {
        "source_kind": "accepted-image-derivation",
        "source_id": "recoverable",
        "relation": "parent-generation",
    } in parent_row["protected_by"]

    monkeypatch.setattr(builder, "_publish", original)
    result = derive(builder, "recoverable", SOURCE_REVISION, profile)
    assert result["phase"] == "complete"
    selected = read_selection(
        builder.state / "image-build" / "generations" / result["generation"]
    )
    assert selected.manifest[FIELD]["parent"]["generation"] == parent.generation

    state = immutable_report(builder.state)
    parent_row = next(
        row for row in state["objects"]
        if row["kind"] == "generation" and row["id"] == parent.generation
    )
    assert any(
        edge["source_kind"] == "generation"
        and edge["source_id"] == selected.generation
        and edge["relation"] == "accepted-image-parent"
        for edge in parent_row["protected_by"]
    )

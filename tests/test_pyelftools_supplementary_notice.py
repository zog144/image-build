import json
import os
import subprocess
from pathlib import Path

from zog.image_build.filesystem import digest, inventory
from zog.image_build.licensing import prepare_finalization, prepare_readability, preserve
from zog.image_build.metadata import load_packages
from zog.image_build.sources import stage
from zog.image_build.stages import stage_recipes


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
SDIST_SHA = "660d82dcbeb8e83d1702bd97f223f761625da06111c0cc988eac6b8ab0c1b61f"
CONSTRUCT_SHA = "f8d0c347a0dcc6ebe1671640dfae8d2411b6ded892e06a6764f8208b218b2af4"


def test_exact_pyelftools_sdist_and_supplementary_notice_acquire_install_and_preserve(tmp_path):
    recipes = tmp_path / "recipes"
    stage_recipes(
        PROJECT / "bootstrap/systemd-core.py",
        PROJECT / "package",
        recipes,
    )
    package = load_packages(recipes)["pyelftools-build"]
    assert [source["sha256"] for source in package.sources] == [SDIST_SHA, CONSTRUCT_SHA]

    state = tmp_path / "state"
    cache = state / "image-build" / "sources"
    source = tmp_path / "source"
    acquisitions = stage(package, source, cache)
    assert [record["transport"] for record in acquisitions] == ["upstream", "upstream"]
    assert digest(cache / SDIST_SHA) == SDIST_SHA
    assert digest(cache / CONSTRUCT_SHA) == CONSTRUCT_SHA

    archive_license = source / "upstream/pyelftools-0.33/LICENSE"
    wrongly_assumed = source / "upstream/pyelftools-0.33/elftools/construct/LICENSE"
    supplementary = source / "supplementary/pyelftools-construct/LICENSE"
    assert digest(archive_license) == (
        "ae18bf4cb82f92af7547259177bc28bc48e4fc732518bcedfe690226288d3445"
    )
    assert not wrongly_assumed.exists()
    assert digest(supplementary) == CONSTRUCT_SHA

    # This must no longer try to open the missing archive member.
    prepare_readability(package, source)

    output = tmp_path / "output"
    output.mkdir()
    environment = {
        **os.environ,
        "DESTDIR": str(output),
        "IMAGE_BUILD_SOURCE": str(source),
    }
    subprocess.run(
        package.steps["install"][0],
        cwd=source,
        env=environment,
        check=True,
    )
    installed = output / "usr/share/licenses/build-pyelftools/CONSTRUCT-LICENSE"
    assert digest(installed) == CONSTRUCT_SHA

    checkpoint = tmp_path / "license-finalization.json"
    inputs = {"recipe": package.fingerprint}
    prepare_finalization(package, output, checkpoint, inputs)
    result = preserve(package, source, output, state)
    prepare_finalization(package, output, checkpoint, inputs)

    receipt = json.loads((output / result["receipt"]).read_text())
    assert receipt["schema"] == 2
    assert len(receipt["evidence"]) == 1
    assert receipt["evidence"][0]["origin"] == "original-source-archive"
    assert receipt["evidence"][0]["path"] == "pyelftools-0.33/LICENSE"
    assert receipt["unreviewed_sources"] == []

    assert len(receipt["supplementary_notices"]) == 1
    notice = receipt["supplementary_notices"][0]
    assert notice["id"] == "pyelftools-construct-license"
    assert notice["origin"] == "independently-retrieved-upstream-notice"
    assert notice["upstream"] == {
        "repository": "https://github.com/eliben/pyelftools",
        "revision": "52ce435186022bd6b32012a998931fe86c985ec8",
        "path": "elftools/construct/LICENSE",
    }
    canonical = output / notice["installed_path"]
    assert digest(canonical) == CONSTRUCT_SHA
    assert canonical.read_bytes() == installed.read_bytes()

    # Reproduce the engine's produce-manifest acceptance boundary exactly:
    # canonical zog-packages licensing outputs are excluded, while the package's
    # own build-pyelftools notice copies remain ordinary package outputs.
    outputs = inventory(output)
    license_parent = str(Path(result["receipt"]).parent)
    license_paths = {
        record["path"]
        for record in outputs
        if record["path"].startswith(license_parent + "/")
    }
    actual = tuple(
        record["path"]
        for record in outputs
        if record["kind"] != "directory" and record["path"] not in license_paths
    )
    missing = sorted(set(package.outputs) - set(actual))
    unexpected = sorted(
        path
        for path in actual
        if not any(
            path == tree or path.startswith(tree + "/")
            for tree in package.output_trees
        )
    )
    assert missing == []
    assert unexpected == []

    assert "usr/lib/python3.15/site-packages/elftools/construct/LICENSE" not in package.outputs
    assert "usr/share/licenses/build-pyelftools/CONSTRUCT-LICENSE" in package.outputs
    assert "usr/share/licenses/build-pyelftools/LICENSE" in package.outputs
    assert "usr/lib/python3.15/site-packages/elftools/construct/LICENSE" not in actual
    assert "usr/share/licenses/build-pyelftools/CONSTRUCT-LICENSE" in actual

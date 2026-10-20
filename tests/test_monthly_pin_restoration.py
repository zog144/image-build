import ast
import hashlib
from pathlib import Path

import pytest

from zog.image_build.pins import load, snapshot


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
PIN = PROJECT / "pins" / "2026-10-01" / "commit-pin.py"
PIN_SHA256 = "d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36"
GRAPHICAL_CATALOGUE_ONLY = {
    "agreety",
    "firefox-esr",
    "greetd",
    "i3",
    "turbovnc",
    "virtualgl",
    "xorg-server",
}
TOOLCHAIN_PLANS = (
    "lfs-cross.py",
    "lfs-temporary.py",
    "lfs-native-temporary.py",
    "lfs-native-environment.py",
    "lfs-final-start.py",
    "lfs-final-math.py",
    "lfs-final-binutils.py",
    "lfs-final-gcc.py",
)


def literal(path):
    return ast.literal_eval(path.read_text())


def test_restored_october_pin_has_exact_reviewed_bytes_and_current_selection():
    assert hashlib.sha256(PIN.read_bytes()).hexdigest() == PIN_SHA256
    current = literal(PROJECT / "pins" / "current.py")
    assert current == {"date": "2026-10-01"}
    pin = load(PIN)
    assert pin["date"] == "2026-10-01"
    assert pin["corrected_on"] == "2026-10-20"
    assert len(pin["packages"]) == 133
    assert sum(len(row.get("recipes", {})) for row in pin["packages"].values()) == 139


def test_every_current_stage_recipe_equals_its_reviewed_monthly_pin():
    pin = load(PIN)
    source_files = sorted((PROJECT / "package").glob("*/stages/**/sources.py"))
    assert len(source_files) == 139
    observed = set()
    for path in source_files:
        key = path.relative_to(PROJECT / "package").as_posix().removesuffix("/sources.py")
        project = key.split("/", 1)[0]
        assert pin["packages"][project]["recipes"][key] == literal(path), key
        observed.add(key)
    pinned = {
        key
        for row in pin["packages"].values()
        for key in row.get("recipes", {})
    }
    assert pinned == observed


def test_catalogue_only_graphical_sources_are_pinned_without_executable_recipes():
    pin = load(PIN)
    top_level_sources = {
        path.parent.name: literal(path)
        for path in (PROJECT / "package").glob("*/sources.py")
    }
    assert set(top_level_sources) == GRAPHICAL_CATALOGUE_ONLY
    for name, sources in top_level_sources.items():
        row = pin["packages"][name]
        assert row["recipes"] == {}
        assert row["status"].startswith("catalogue-only-source-pin;")
        assert row["license_scope"]
        assert row["source"] == {
            "url": sources[0]["url"],
            "sha256": sources[0]["sha256"],
        }


def test_five_reviewed_drift_corrections_are_exact_current_inputs():
    pin = load(PIN)
    recipes = {
        key: row["recipes"][key]
        for row in pin["packages"].values()
        for key in row.get("recipes", {})
    }
    systemd_fixture = recipes["build-environment/stages/systemd-test"]
    assert len(systemd_fixture) == 4
    assert {item["destination"] for item in systemd_fixture} == {
        "inputs/os-release",
        "inputs/COPYRIGHT",
        "inputs/LICENSES/BSD-3-Clause.txt",
        "inputs/LICENSES/GPL-3.0-only.txt",
    }
    assert recipes["host-discover/stages/final"][0]["url"].endswith(
        "/b61197461f2fe19fd29203a1d148a66c6ce89f6d"
    )
    assert recipes["host-identify/stages/final"][0]["url"].endswith(
        "/1a5eac0b255c995022db6a3a4c0051efffa748cc"
    )
    assert recipes["host-install/stages/final"][0]["url"].endswith(
        "/f82576c4f430398bc914b3e9d56b10c366ba0eac"
    )
    maturin = recipes["python-maturin/stages/final"]
    assert len(maturin) == 513
    assert any(item["destination"].startswith("supplementary/") for item in maturin)


@pytest.mark.parametrize("plan_name", TOOLCHAIN_PLANS)
def test_toolchain_bootstrap_plans_materialize_only_reviewed_october_sources(
    tmp_path, plan_name
):
    plan = literal(PROJECT / "bootstrap" / plan_name)
    destination = tmp_path / plan_name.removesuffix(".py")
    destination.mkdir()
    record = snapshot(
        PROJECT / "package",
        plan["stages"],
        destination,
        pin_date="2026-10-01",
    )
    assert record["date"] == "2026-10-01"
    assert set(record["packages"]) == {stage["id"] for stage in plan["stages"]}
    for stage in plan["stages"]:
        materialized = record["packages"][stage["id"]]
        assert materialized["project"] == stage["project"]
        assert materialized["recipe"] == stage["recipe"]
        assert materialized["sources"] == literal(
            PROJECT / "package" / stage["project"]
            / Path(stage["recipe"]).relative_to(stage["project"])
            / "sources.py"
        )

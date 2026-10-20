import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "public_candidate_preflight.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("public_candidate_preflight", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reviewed_monthly_pin_is_accepted_by_public_preflight():
    module = load_tool()
    paths = {
        "project/pins/current.py",
        "project/pins/2026-10-01/commit-pin.py",
    }
    assert module.monthly_pin_issues(ROOT, paths) == []


def test_public_preflight_rejects_missing_unreviewed_or_tampered_monthly_pin(tmp_path):
    module = load_tool()
    current = tmp_path / "project" / "pins" / "current.py"
    current.parent.mkdir(parents=True)

    assert module.monthly_pin_issues(tmp_path, set()) == [{
        "path": "project/pins/current.py",
        "finding": "required_monthly_pin_selector_missing",
    }]

    current.write_text("{'date': '2026-11-01'}\n")
    assert module.monthly_pin_issues(
        tmp_path, {"project/pins/current.py"}
    )[0]["finding"] == "unreviewed_monthly_pin_selection"

    current.write_text("{'date': '2026-10-01'}\n")
    pin = tmp_path / "project" / "pins" / "2026-10-01" / "commit-pin.py"
    pin.parent.mkdir()
    pin.write_text("{'schema': 1, 'date': '2026-10-01', 'packages': {}}\n")
    result = module.monthly_pin_issues(
        tmp_path,
        {
            "project/pins/current.py",
            "project/pins/2026-10-01/commit-pin.py",
        },
    )
    assert result == [{
        "path": "project/pins/2026-10-01/commit-pin.py",
        "finding": "reviewed_monthly_pin_digest_mismatch",
    }]

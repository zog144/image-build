"""One held Resident B CPython/controller source selection; no native execution."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tools/verify_resident_b_consolidated_source.py"
spec = importlib.util.spec_from_file_location("resident_b_consolidated", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fresh():
    return json.loads(mod.SELECTION.read_text())


def test_existing_source_graph_is_one_reviewed_python_network_and_controller_selection():
    result = mod.verify()
    assert result["source_selection"] == "CONSOLIDATED_CP312_AND_CURRENT_CONTROLLERS"
    assert result["accepted_generation"] is None
    assert result["compiler_authorized"] is False
    assert result["service_activation_authorized"] is False
    assert result["network_outputs"] == "SOURCE_DECLARED"
    assert result["controller_wheels"] == "REVIEWED_SOURCE_PINS"


@pytest.mark.parametrize("alter", [
    lambda s: s["native_authority"].update(native_compilation_permitted=True),
    lambda s: s["native_authority"].update(accepted_generation="a"*64),
    lambda s: s["controllers"]["root-control"].update(revision="f"*40),
    lambda s: s["aggregate_installed"].update(installed_bytes_verified=True),
    lambda s: s["aggregate_installed"].update(aggregate_wheel_sha256="a"*64),
    lambda s: s["aggregate_installed"].update(installed_root_generation="f"*64),
    lambda s: s["aggregate_installed"].update(target_interpreter="/usr/bin/python3.15"),
    lambda s: s["aggregate_installed"].update(native_activation_permitted=True),
    lambda s: s["controllers"]["box-control"].update(archive_sha256="e"*64),
    lambda s: s["source_tools"].append("resident312-setuptools-final"),
    lambda s: s["python_controllers"]["build_dependencies"].remove("sqlite-final"),
    lambda s: s["python_controllers"].update(replaces_python_final=True),
    lambda s: s["resident_utilities"]["systemd-final"].remove("usr/bin/networkctl"),
    lambda s: s["resident_utilities"]["host-discover-final"].remove("usr/bin/host-discover-recovery"),
    lambda s: s["python_runtime_boundary"].update(controller_wheels="python-final"),
    lambda s: s["retained_evidence"].update(boot_a_selection_changed=True),
    lambda s: s.update(remaining_native_checks=[]),
])
def test_source_candidate_rejects_forged_controller_abi_network_or_native_claim(alter):
    selection = copy.deepcopy(fresh())
    alter(selection)
    with pytest.raises(ValueError, match="NOT READY"):
        mod.verify(selection=selection)

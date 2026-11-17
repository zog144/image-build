"""Negative tests for offline dependency closure; no native Host mutation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "offline_deps", ROOT / "tools/verify_nonresident_certbot_dependency_wheelhouse.py"
)
deps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deps)


def fake_wheel(directory, name, version="1.0", *, extra=None):
    filename = name.replace("-", "_") + "-" + version + "-py3-none-any.whl"
    wheel = directory / filename
    di = name.replace("-", "_") + "-" + version + ".dist-info"
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr(di + "/METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        z.writestr(di + "/WHEEL", "Wheel-Version: 1.0\nTag: py3-none-any\n")
        z.writestr(di + "/RECORD", "")
        if extra:
            z.writestr(extra, "replacement")
    return wheel


class OfflineDependencyClosure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in deps.REQUIREMENTS:
            fake_wheel(self.root, name)

    def test_complete_direct_set_and_exact_hash_lock(self):
        wheels = deps.inventory(self.root)
        self.assertEqual(len(wheels), 10)
        locked = self.root.parent / (self.root.name + ".lock")
        locked.write_text(deps.generated_lock(wheels))
        deps.check_lock(wheels, locked)
        changed = next(self.root.glob("dbus_next-*.whl"))
        with changed.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(deps.DependencyHold, "differ from reviewed exact lock"):
            deps.check_lock(deps.inventory(self.root), locked)

    def test_missing_direct_distribution_fails(self):
        next(self.root.glob("dbus_next-*.whl")).unlink()
        with self.assertRaisesRegex(deps.DependencyHold, "omits a declared"):
            deps.inventory(self.root)

    def test_duplicate_distribution_fails(self):
        fake_wheel(self.root, "dbus-next", "0.2")
        with self.assertRaisesRegex(deps.DependencyHold, "duplicated"):
            deps.inventory(self.root)

    def test_nonwheel_input_fails(self):
        (self.root / "unreviewed.tar.gz").write_text("not a wheel")
        with self.assertRaisesRegex(deps.DependencyHold, "non-wheel"):
            deps.inventory(self.root)

    def test_foreign_package_cannot_replace_aggregate(self):
        fake_wheel(self.root, "zog")
        with self.assertRaisesRegex(deps.DependencyHold, "unlinked regular|distribution identity|not a wheel|wheel distribution"):
            deps.inventory(self.root)

    def test_dependency_wheel_cannot_override_zog_module(self):
        next(self.root.glob("waitress-*.whl")).unlink()
        fake_wheel(self.root, "waitress", extra="zog/root_control/daemon.py")
        with self.assertRaisesRegex(deps.DependencyHold, "replace installed zog bytes"):
            deps.inventory(self.root)


if __name__ == "__main__":
    unittest.main()

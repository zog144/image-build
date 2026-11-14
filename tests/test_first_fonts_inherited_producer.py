"""Immutable first-Fonts source continuity across the identity-only revision.

The original producer is retained as historical evidence. The replacement
must retain exact first-Fonts recipe and October pin bytes, while no longer
allowing a selected execution UID/GID. This test never invokes a compiler.
"""
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git_blob(path):
    payload = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def test_original_october_pin_was_copied_byte_for_byte_not_regenerated():
    pin = ROOT / "project/pins/2026-10-01/commit-pin.py"
    assert git_blob(pin) == "ce222f7e0d7d29d018cbaae86e1c1ab3959865fc"
    assert hashlib.sha256(pin.read_bytes()).hexdigest() == (
        "d3104eeddbbbe63fe3279c58ce9807f3b5250632ecdca4826abc028bcf923b36"
    )


def test_exact_original_fonts_recipe_selection_is_unchanged():
    assert git_blob(ROOT / "project/bootstrap/graphics-fonts.py") == (
        "3c97eea9a93e20fa40bb69687f5e9613e8178e98"
    )
    selected = {
        "libpng": {
            "build.py": "24becdc4f6c9841156285c23cdc9b62c1f8f2166",
            "dependencies.py": "c6905845e9b2ff16a1a6709a682fd02986af42c7",
            "produce-manifest.py": "10d6e8fa89bceea98a1f58e582d1f7b1aaba0fdf",
        },
        "freetype": {
            "build.py": "5af75b7ac87398c9112bada4ef2deac19c0388c5",
            "dependencies.py": "111f1d565099efc29b5b5a5ef6c944a91825eb6a",
            "produce-manifest.py": "ddde93dec410c587abcb230fe779ab78326a97c5",
        },
        "fontconfig": {
            "build.py": "1fda6ea9e7eaf9aff196166ba9b94d0271d37691",
            "dependencies.py": "14984eb765eb26136b7a529f3d222658b0a0d1b7",
            "produce-manifest.py": "d8f9bedc053d5835bb3b2b968b117744bcabc358",
        },
    }
    for project, files in selected.items():
        for name, expected in files.items():
            assert git_blob(ROOT / "project/package" / project / "stages/final" / name) == expected


def test_no_compiler_identity_selection_in_runtime_and_configuration():
    for path in (
        "src/zog/image_build/box_control_adapter.py",
        "src/zog/image_build/configuration.py",
    ):
        source = (ROOT / path).read_text()
        assert "execution_user_id" not in source
        assert "execution_group_id" not in source
        assert "os.setuid" not in source and "os.setgid" not in source
        assert "runuser " not in source and "sudo " not in source

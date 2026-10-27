"""Durability helpers for caller-owned staging trees.

These helpers are allowed to change directory modes temporarily only because their
inputs are explicitly caller-owned staging trees.  They never follow symlink
directories, restore every widened mode on success or failure, and fsync restored
directory metadata before returning.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import stat

from .errors import ImageBuildError
from .filesystem import inventory as _inventory
from .filesystem import sync_directory, sync_tree as _sync_tree


def _directory_fd(path):
    flags = os.O_RDONLY | os.O_DIRECTORY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _restore_modes(changed):
    first_error = None
    for path, mode in sorted(changed, key=lambda row: len(row[0].parts), reverse=True):
        try:
            descriptor = _directory_fd(path)
            try:
                os.fchmod(descriptor, mode)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            sync_directory(path.parent)
        except BaseException as error:
            if first_error is None:
                first_error = error
    if first_error is not None:
        raise first_error


def _widen_tree(root, changed, original_modes):
    root = Path(root)
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ImageBuildError("staging root must be a real directory")
    mode = stat.S_IMODE(info.st_mode)
    relative = Path(".")
    original_modes[relative] = mode
    if mode & 0o700 != 0o700:
        changed.append((root, mode))
        root.chmod(mode | 0o700)

    def visit(directory, relative_directory):
        with os.scandir(directory) as stream:
            entries = sorted(stream, key=lambda entry: entry.name)
        for entry in entries:
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                continue
            if not stat.S_ISDIR(info.st_mode):
                continue
            path = Path(entry.path)
            relative = relative_directory / entry.name
            mode = stat.S_IMODE(info.st_mode)
            original_modes[relative] = mode
            if mode & 0o700 != 0o700:
                changed.append((path, mode))
                path.chmod(mode | 0o700)
            visit(path, relative)

    visit(root, Path("."))


@contextmanager
def accessible(root):
    """Temporarily make caller-owned staging directories owner-traversable."""
    root = Path(root)
    changed = []
    original_modes = {}
    try:
        _widen_tree(root, changed, original_modes)
    except BaseException as error:
        try:
            _restore_modes(changed)
        except BaseException as restore_error:
            if hasattr(error, "add_note"):
                error.add_note("staging mode restoration also failed: " + repr(restore_error))
        raise
    try:
        yield original_modes
    except BaseException as error:
        try:
            _restore_modes(changed)
        except BaseException as restore_error:
            if hasattr(error, "add_note"):
                error.add_note("staging mode restoration also failed: " + repr(restore_error))
        raise
    else:
        _restore_modes(changed)


def inventory(root):
    """Inventory a staging tree while reporting its original restrictive modes."""
    root = Path(root)
    with accessible(root) as original_modes:
        records = _inventory(root)
    result = []
    for record in records:
        value = dict(record)
        if value["kind"] == "directory":
            relative = Path(value["path"])
            if relative in original_modes:
                value["mode"] = original_modes[relative]
        result.append(value)
    return result


def sync(root):
    """Durably sync a staging tree and restore its exact directory modes."""
    with accessible(root):
        _sync_tree(root)


def set_directory_modes(root, modes):
    """Set reviewed final directory modes without following redirected paths."""
    root = Path(root)
    rows = []
    for name, mode in modes.items():
        relative = Path(name)
        if (
            relative.is_absolute()
            or relative == Path(".")
            or ".." in relative.parts
            or type(mode) is not int
            or not 0 <= mode <= 0o7777
        ):
            raise ImageBuildError("invalid staging directory mode request")
        path = root / relative
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ImageBuildError("staging directory mode target is redirected or absent")
        rows.append((path, mode))
    for path, mode in sorted(rows, key=lambda row: len(row[0].parts), reverse=True):
        path.chmod(mode)


def copy(source, destination, *, expected=None):
    """Copy one caller-owned staging tree, preserving restrictive directory modes."""
    source, destination = Path(source), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ImageBuildError("staging copy destination already exists")
    records = inventory(source)
    if expected is not None and records != expected:
        raise ImageBuildError("staging copy source differs from expected inventory")
    root_mode = stat.S_IMODE(source.lstat().st_mode)
    with accessible(source) as original_modes:
        shutil.copytree(source, destination, symlinks=True)
    # copytree observes temporary traversable modes. Restore the source's exact
    # directory modes on the copy before its durability barrier.
    directory_modes = {
        relative.as_posix(): mode
        for relative, mode in original_modes.items()
        if relative != Path(".")
    }
    set_directory_modes(destination, directory_modes)
    destination.chmod(root_mode)
    sync(destination)
    if inventory(destination) != records:
        raise ImageBuildError("staging copy differs after mode restoration")
    return records

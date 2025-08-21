"""Tests for `Config.validate_db_path` negative scenarios."""

import os
import stat
from pathlib import Path

import pytest

from ip_monitor.config import Config, NotifyMethod


def _base_kwargs(tmp_path: Path) -> dict:
    return {
        "notify_method": NotifyMethod.NTFY_SH,
        "ntfy": {"server": "http://s", "topic": "t"},
        "ips": [{"ip": "192.0.2.1", "description": "d"}],
    }


def test_db_path_parent_missing(tmp_path: Path) -> None:
    """Parent directory must exist."""
    missing_parent = tmp_path / "nope" / "db.sqlite"
    with pytest.raises(ValueError):
        Config(db_path=missing_parent, **_base_kwargs(tmp_path))


def test_db_path_parent_not_directory(tmp_path: Path) -> None:
    """Parent must be a directory, not a file."""
    parent_file = tmp_path / "file.txt"
    parent_file.write_text("x")
    bad_path = parent_file / "db.sqlite"  # type: ignore[operator]
    with pytest.raises(ValueError):
        Config(db_path=bad_path, **_base_kwargs(tmp_path))


@pytest.mark.skipif(
    os.name != "posix", reason="chmod semantics are POSIX-specific"
)
def test_db_path_parent_not_writable(tmp_path: Path) -> None:
    """Parent directory must be writable when creating the DB file."""
    parent = tmp_path / "no_write"
    parent.mkdir()
    (parent / "keep").write_text("x")
    parent.chmod(stat.S_IREAD | stat.S_IEXEC)  # 0o500
    try:
        with pytest.raises(ValueError):
            Config(db_path=parent / "db.sqlite", **_base_kwargs(tmp_path))
    finally:
        # Restore to allow tmp cleanup on some systems
        parent.chmod(0o700)


@pytest.mark.skipif(
    os.name != "posix", reason="chmod semantics are POSIX-specific"
)
def test_db_path_file_exists_but_not_writable(tmp_path: Path) -> None:
    """Existing DB file must be writable by the process."""
    db_file = tmp_path / "db.sqlite"
    db_file.write_text("")
    db_file.chmod(stat.S_IREAD)  # 0o400
    try:
        with pytest.raises(ValueError):
            Config(db_path=db_file, **_base_kwargs(tmp_path))
    finally:
        db_file.chmod(0o600)

"""Tests for platformdirs-backed default paths and discovery order."""

from pathlib import Path

import pytest

from ip_monitor import config as mod
from ip_monitor.config import Config, NotifyMethod, guess_default_config_path


class _PD:
    """Stub PlatformDirs-like object."""

    def __init__(self, ucfg: Path, scfg: Path, udata: Path):
        self.user_config_dir = str(ucfg)
        self.site_config_dir = str(scfg)
        self.user_data_dir = str(udata)


@pytest.mark.asyncio
async def test_guess_config_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """IPM_CONFIG overrides all other discovery locations."""
    cfg = tmp_path / "env.yaml"
    monkeypatch.setenv("IPM_CONFIG", str(cfg))

    # Ensure CWD and dirs are irrelevant
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_DIRS", "")

    # Patch PlatformDirs used inside module
    monkeypatch.setattr(
        mod,
        "PlatformDirs",
        lambda *a, **k: _PD(tmp_path / "uc", tmp_path / "sc", tmp_path / "ud"),
    )

    got = mod.guess_default_config_path()
    assert Path(got) == cfg.resolve()


@pytest.mark.asyncio
async def test_guess_config_cwd_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CWD config.yaml is preferred when present."""
    cwd = tmp_path / "wd"
    cwd.mkdir()
    (cwd / "config.yaml").write_text(
        "db_path: x\nnotify_method: ntfy\nntfy:\n  server: http://s\n  topic: t\nips: []\nurls: [{url: u, description: d}]\n"
    )

    monkeypatch.chdir(cwd)

    monkeypatch.setenv("IPM_CONFIG", "")
    monkeypatch.setattr(
        mod,
        "PlatformDirs",
        lambda *a, **k: _PD(tmp_path / "uc", tmp_path / "sc", tmp_path / "ud"),
    )

    got = guess_default_config_path()
    assert Path(got) == (cwd / "config.yaml")


@pytest.mark.asyncio
async def test_guess_config_site_when_user_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pick site_config_dir when user and CWD candidates are absent."""
    cwd = tmp_path / "empty"
    cwd.mkdir()
    scfg = tmp_path / "scfg"
    (scfg).mkdir()
    (scfg / "config.yaml").write_text(
        "db_path: x\nnotify_method: ntfy\nntfy:\n  server: http://s\n  topic: t\nips: []\nurls: [{url: u, description: d}]\n"
    )

    monkeypatch.chdir(cwd)
    monkeypatch.setenv("IPM_CONFIG", "")
    monkeypatch.setattr(
        mod,
        "PlatformDirs",
        lambda *a, **k: _PD(tmp_path / "ucfg_not_exist", scfg, tmp_path / "ud"),
    )

    got = mod.guess_default_config_path()
    assert Path(got) == (scfg / "config.yaml")


def test_default_db_path_uses_user_data_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When db_path is absent, default uses user_data_dir/ipmonitor.db."""
    udata = tmp_path / "udata"

    monkeypatch.setattr(
        mod,
        "PlatformDirs",
        lambda *a, **k: _PD(tmp_path / "uc", tmp_path / "sc", udata),
    )

    cfg = Config(
        notify_method=NotifyMethod.NTFY_SH,
        ntfy={"server": "http://s", "topic": "t"},  # type: ignore[arg-type]
        ips=[{"ip": "192.0.2.1", "description": "d"}],  # type: ignore[list-item]
    )
    # Parent directory should be created and db_path assigned
    assert cfg.db_path == udata / "ipmonitor.db"
    assert (udata).exists()

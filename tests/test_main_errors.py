"""Tests for error handling paths in main()."""

import sys
from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_main_config_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit with code 1 and print path when config is missing."""
    missing = "/tmp/does/not/exist/config.yaml"
    monkeypatch.setattr(sys, "argv", ["ip-monitor", "-c", missing])

    with pytest.raises(SystemExit) as exc:
        await main()
    assert exc.value.code == 1
    assert missing in capsys.readouterr().err


@pytest.mark.asyncio
async def test_main_config_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit with code 1 when config exists but is unreadable."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"db_path: {tmp_path}/db.sqlite\nnotify_method: ntfy\nntfy:\n  server: http://s\n  topic: t\nips:\n  - ip: 192.0.2.1\n    description: d\n"
    )
    # Remove read permission
    cfg.chmod(0)

    monkeypatch.setattr(sys, "argv", ["ip-monitor", "-c", str(cfg)])

    with pytest.raises(SystemExit) as exc:
        await main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "permission" in err.lower()


@pytest.mark.asyncio
async def test_main_precheck_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Handle unexpected precheck error and print user-friendly message."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
ips:
  - ip: 192.0.2.1
    description: d
"""
    )

    monkeypatch.setattr(sys, "argv", ["ip-monitor", "-c", str(cfg)])

    async def boom(_: str) -> bool:
        raise RuntimeError("precheck fail")

    monkeypatch.setattr("ip_monitor.monitoring.ping", boom)

    await main()
    out = capsys.readouterr().out
    assert "Pas de connexion à Internet." in out

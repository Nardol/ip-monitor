"""Ensure exceptions in spawned tasks are caught and logged by main."""

from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_task_exception_is_caught(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Crash a task and ensure main completes without raising."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
urls:
  - url: example.org
    description: site
precheck_enabled: false
"""
    )

    # Replace check_url_status with a crashing coroutine
    async def boom(*args, **kwargs):
        raise RuntimeError("task failed")

    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg)])
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", boom)

    # Avoid notifications
    async def noop_notify(session, config, message):
        return None

    monkeypatch.setattr("ip_monitor.notify.notify", noop_notify)

    await main()
    out = capsys.readouterr().out
    assert "Pas de connexion à Internet." not in out

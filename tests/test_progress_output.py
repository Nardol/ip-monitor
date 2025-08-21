"""Progress printing tests (default verbose and quiet)."""

from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_progress_default_prints_tasks_and_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """By default, print config line, task starts, and summary."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
ips:
  - ip: 192.0.2.3
    description: test
urls:
  - url: example.org
    description: site
precheck_enabled: false
"""
    )

    # Avoid real work
    async def noop(*a, **k):
        return None

    monkeypatch.setattr("ip_monitor.monitoring.check_ip", noop)
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", noop)
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg)])

    await main()
    out = capsys.readouterr().out
    assert "Config:" in out
    assert "IPs: 1, URLs: 1" in out
    assert "IP 192.0.2.3" in out and "démarré" in out
    assert "URL example.org" in out and "démarré" in out
    assert "Terminé:" in out and "0 down, 0 up" in out


@pytest.mark.asyncio
async def test_quiet_suppresses_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """When --quiet is set, suppress progress prints."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
ips:
  - ip: 192.0.2.3
    description: test
precheck_enabled: false
"""
    )

    async def noop(*a, **k):
        return None

    monkeypatch.setattr("ip_monitor.monitoring.check_ip", noop)
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", noop)
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("sys.argv", ["ip-monitor", "--quiet", "-c", str(cfg)])

    await main()
    out = capsys.readouterr().out
    assert "Config:" not in out
    assert "démarré" not in out
    assert "Terminé:" not in out

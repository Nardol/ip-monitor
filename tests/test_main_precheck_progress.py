"""Integration-like test for precheck progress printing in main()."""

from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_main_prints_precheck_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """With precheck enabled and ping OK, print 'Vérification Internet … OK'."""
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
"""
    )

    # Mock ping to succeed and avoid real work for checks
    async def ping_ok(_ip: str) -> bool:
        return True

    async def noop(*a, **k):
        return None

    monkeypatch.setattr("ip_monitor.monitoring.ping", ping_ok)
    monkeypatch.setattr("ip_monitor.monitoring.check_ip", noop)
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", noop)
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg)])

    await main()
    out = capsys.readouterr().out
    assert "Vérification Internet" in out and "OK" in out
    assert "Config:" in out
    assert "Terminé:" in out

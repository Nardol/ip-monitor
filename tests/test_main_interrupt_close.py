"""Tests around interruption and DB close behavior."""

from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_main_keyboardinterrupt_on_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Propagate KeyboardInterrupt raised during init (expected)."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
ips:
  - ip: 192.0.2.9
    description: d
precheck_enabled: false
"""
    )

    async def boom_init_db(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("ip_monitor.monitoring.init_db", boom_init_db)
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg)])

    with pytest.raises(KeyboardInterrupt):
        await main()


@pytest.mark.asyncio
async def test_main_close_exception_is_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not raise when DB close fails; error is only logged."""
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
ips:
  - ip: 192.0.2.8
    description: d
precheck_enabled: false
"""
    )

    class StubConn:
        async def execute(self, *a, **k):
            return None

        async def commit(self):
            return None

        async def close(self):
            raise RuntimeError("close failed")

    async def fake_init_db(*args, **kwargs):
        return StubConn()

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr("ip_monitor.monitoring.init_db", fake_init_db)
    monkeypatch.setattr("ip_monitor.monitoring.check_ip", noop)
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", noop)
    monkeypatch.setattr("ip_monitor.monitoring.notify", noop)
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg)])

    # Should not raise even if close() fails; error is logged
    await main()

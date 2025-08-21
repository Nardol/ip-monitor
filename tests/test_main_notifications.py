"""Notification behavior (down/up messages) tests."""

import sys
from pathlib import Path

import pytest

from ip_monitor.monitoring import init_db, main, update_status


@pytest.mark.asyncio
async def test_main_sends_down_notification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Send a 'down' notification when a monitored IP fails ping."""
    cfg_path = tmp_path / "conf.yaml"
    db_path = tmp_path / "ipmonitor.db"
    cfg_path.write_text(
        f"""
db_path: {db_path}
notify_method: ntfy
ntfy:
  server: http://ntfy.local
  topic: t
ips:
  - ip: 192.0.2.10
    description: test-ip
precheck_enabled: false
"""
    )

    # Capture notifications
    messages: list[str] = []

    async def fake_notify(session, config, message: str):
        messages.append(message)

    # Force ping failure to mark IP as down
    async def ping_fail(_ip: str) -> bool:
        return False

    monkeypatch.setattr("ip_monitor.monitoring.ping", ping_fail)
    monkeypatch.setattr("ip_monitor.monitoring.notify", fake_notify)
    monkeypatch.setattr(sys, "argv", ["ip-monitor", "-c", str(cfg_path)])

    await main()

    assert messages, "Aucune notification reçue alors qu'une IP est down"
    assert "Erreur monitoring sur" in messages[0]


@pytest.mark.asyncio
async def test_main_sends_up_notification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Send an 'up' notification when a previously down IP recovers."""
    cfg_path = tmp_path / "conf.yaml"
    db_path = tmp_path / "ipmonitor.db"
    ip = "192.0.2.11"
    cfg_path.write_text(
        f"""
db_path: {db_path}
notify_method: ntfy
ntfy:
  server: http://ntfy.local
  topic: t
ips:
  - ip: {ip}
    description: test-up
precheck_enabled: false
"""
    )

    # Seed DB with this IP as down
    conn = await init_db(db_path)
    try:
        await update_status(conn, "IP", ip, 1)
        await conn.commit()
    finally:
        await conn.close()

    # Capture notifications
    messages: list[str] = []

    async def fake_notify(session, config, message: str):
        messages.append(message)

    # Force ping success so the IP transitions from down to up
    async def ping_ok(_ip: str) -> bool:
        return True

    monkeypatch.setattr("ip_monitor.monitoring.ping", ping_ok)
    monkeypatch.setattr("ip_monitor.monitoring.notify", fake_notify)
    monkeypatch.setattr(sys, "argv", ["ip-monitor", "-c", str(cfg_path)])

    await main()

    assert messages, "Aucune notification reçue alors qu'une IP repasse up"
    assert "de nouveau up" in messages[0]

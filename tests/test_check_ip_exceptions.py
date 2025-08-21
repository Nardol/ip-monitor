"""Tests that check_ip handles timeouts and exceptions robustly."""

import asyncio
from pathlib import Path

import pytest

from ip_monitor.config import IpInfo
from ip_monitor.monitoring import check_ip, init_db


@pytest.mark.asyncio
async def test_check_ip_handles_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout ping and treat the target as down."""
    conn = await init_db(Path(":memory:"))
    try:
        ipi = IpInfo(ip="192.0.2.200", description="timeout-ip")
        down: list[str] = []
        up: list[str] = []

        async def slow(_: str) -> bool:
            await asyncio.sleep(10)
            return True

        # wait_for should timeout and exception is caught, treated as down
        monkeypatch.setattr("ip_monitor.monitoring.ping", slow)
        await check_ip(conn, ipi, down, up, ping_timeout=0.01)
        assert down == ["timeout-ip"]
        assert up == []
    finally:
        await conn.close()

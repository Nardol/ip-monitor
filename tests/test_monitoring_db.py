"""Database init, update, status, and cleanup tests."""

from pathlib import Path

import pytest

from ip_monitor.monitoring import (
    check_status,
    init_db,
    remove_old_entries,
    update_status,
)


@pytest.mark.asyncio
async def test_init_update_check_status() -> None:
    """Insert and update status rows, then verify via check_status."""
    conn = await init_db(Path(":memory:"))
    try:
        # Initially no status
        assert not await check_status(conn, "IP", "192.0.2.10")

        # Mark as down
        await update_status(conn, "IP", "192.0.2.10", 1)
        await conn.commit()
        assert await check_status(conn, "IP", "192.0.2.10")

        # Mark as up
        await update_status(conn, "IP", "192.0.2.10", 0)
        await conn.commit()
        assert not await check_status(conn, "IP", "192.0.2.10")
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_remove_old_entries() -> None:
    """Remove obsolete IP/URL entries, keep only current ones, then purge."""
    conn = await init_db(Path(":memory:"))
    try:
        # Seed database with a mix of IPs and URLs
        for addr in [
            ("IP", "192.0.2.1"),
            ("IP", "192.0.2.2"),
            ("URL", "a.example"),
            ("URL", "b.example"),
        ]:
            await update_status(conn, addr[0], addr[1], 1)
        await conn.commit()

        # Keep only 192.0.2.2 and b.example
        await remove_old_entries(conn, {"192.0.2.2"}, {"b.example"})
        await conn.commit()

        # Verify deletions
        async with conn.execute(
            "SELECT type, address FROM status ORDER BY type, address"
        ) as cur:
            rows = await cur.fetchall()
        assert rows == [("IP", "192.0.2.2"), ("URL", "b.example")]

        # If sets are empty, delete all of that type
        await remove_old_entries(conn, set(), set())
        await conn.commit()
        async with conn.execute("SELECT COUNT(*) FROM status") as cur:
            c = (await cur.fetchone())[0]
        assert c == 0
    finally:
        await conn.close()

"""Unit tests for individual check helpers (IP ping, URL checks)."""

import asyncio
from http import client as http_client
from pathlib import Path
from typing import Any

import pytest

from ip_monitor.config import IpInfo, UrlInfo
from ip_monitor.monitoring import (
    check_ip,
    check_url,
    check_url_status,
    init_db,
    ping,
)


class _RespCtx:
    def __init__(self, status: int):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionStub:
    def __init__(
        self, head_status: int | None = None, get_status: int | None = None
    ):
        self._head_status = head_status
        self._get_status = get_status

    def head(self, *args: Any, **kwargs: Any) -> _RespCtx:  # type: ignore[override]
        assert self._head_status is not None
        return _RespCtx(self._head_status)

    def get(self, *args: Any, **kwargs: Any) -> _RespCtx:  # type: ignore[override]
        assert self._get_status is not None
        return _RespCtx(self._get_status)


@pytest.mark.asyncio
async def test_check_ip_down_then_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flip an IP from down to up and track notifications lists."""
    conn = await init_db(Path(":memory:"))
    try:
        down: list[str] = []
        up: list[str] = []
        ipinfo = IpInfo(ip="192.0.2.55", description="my-ip")

        # First: simulate down
        monkeypatch.setattr(
            "ip_monitor.monitoring.ping",
            lambda ip: asyncio.sleep(0, result=False),
        )
        await check_ip(conn, ipinfo, down, up, ping_timeout=0.5)
        assert down == ["my-ip"]
        assert up == []

        # Then: simulate up
        down.clear()
        monkeypatch.setattr(
            "ip_monitor.monitoring.ping",
            lambda ip: asyncio.sleep(0, result=True),
        )
        await check_ip(conn, ipinfo, down, up, ping_timeout=0.5)
        assert up == ["my-ip"]
        assert down == []
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_check_url_status_down_then_up() -> None:
    """Transition URL status and update down/up lists accordingly."""
    conn = await init_db(Path(":memory:"))
    try:
        url = UrlInfo(url="example.local", description="site")
        down: list[str] = []
        up: list[str] = []

        # First down (HEAD 404 and GET 404)
        session = _SessionStub(
            head_status=http_client.NOT_FOUND, get_status=http_client.NOT_FOUND
        )
        await check_url_status(conn, session, url, down, up)
        assert down == ["site"] and up == []

        # Then up (HEAD 200)
        down.clear()
        up.clear()
        session_ok = _SessionStub(
            head_status=http_client.OK, get_status=http_client.OK
        )
        await check_url_status(conn, session_ok, url, down, up)
        assert up == ["site"] and down == []
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_check_url_tries_get_if_head_not_ok() -> None:
    """Fall back to GET when HEAD is not OK and succeed on 200."""
    # HEAD 404 then GET 200 should return True
    session = _SessionStub(
        head_status=http_client.NOT_FOUND, get_status=http_client.OK
    )
    ok = await check_url(session, "example.local")
    assert ok is True


@pytest.mark.asyncio
async def test_ping_uses_returncode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return True when ping returncode=0; False otherwise."""

    class _Proc:
        returncode = 0

        async def communicate(self):
            return (b"", b"")

    async def fake_create(*args, **kwargs):
        return _Proc()

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create)
    assert await ping("192.0.2.1") is True

    # Non-zero returncode means False
    class _Proc2:
        returncode = 1

        async def communicate(self):
            return (b"", b"")

    monkeypatch.setattr(
        "asyncio.create_subprocess_exec",
        lambda *a, **kw: asyncio.sleep(0, result=_Proc2()),
    )
    assert await ping("192.0.2.2") is False

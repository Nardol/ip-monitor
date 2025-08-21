"""Tests for error paths in check_url (HTTP client failures)."""

import pytest
from aiohttp import ClientError

from ip_monitor.monitoring import check_url


class _ErroringSession:
    def head(self, *a, **k):  # type: ignore[override]
        raise ClientError("head boom")

    def get(self, *a, **k):  # type: ignore[override]
        raise ClientError("get boom")


@pytest.mark.asyncio
async def test_check_url_returns_false_on_client_error() -> None:
    """Return False when both HEAD and GET raise ClientError."""
    assert await check_url(_ErroringSession(), "example.org") is False

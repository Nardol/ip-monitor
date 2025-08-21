"""Tests for notify exception paths (ntfy/smsbox)."""

import pytest
from aiontfy.exceptions import NtfyException
from pysmsboxnet import exceptions as smsbox_exceptions

from ip_monitor.config import NtfyConfig, SMSBoxConfig
from ip_monitor.notify import notify_ntfy, notify_smsbox


class _Session:
    pass


@pytest.mark.asyncio
async def test_notify_ntfy_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handle Ntfy publish error without raising exceptions."""

    class StubMessage:
        def __init__(self, *a, **k):
            pass

    class StubNtfy:
        def __init__(self, *a, **k):
            pass

        async def publish(self, *a, **k):
            raise NtfyException("boom")

    monkeypatch.setattr("ip_monitor.notify.Message", StubMessage)
    monkeypatch.setattr("ip_monitor.notify.Ntfy", StubNtfy)

    # Should not raise
    await notify_ntfy(_Session(), NtfyConfig(server="http://s", topic="t"), "m")


@pytest.mark.asyncio
async def test_notify_smsbox_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handle SMSBox send error without raising exceptions."""

    class StubClient:
        def __init__(self, *a, **k):
            pass

        async def send(self, *a, **k):
            raise smsbox_exceptions.SMSBoxException("x")

    monkeypatch.setattr("ip_monitor.notify.Client", StubClient)

    # Should not raise
    await notify_smsbox(
        _Session(), SMSBoxConfig(api_key="k", recipient="r"), "m"
    )

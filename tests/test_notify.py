"""Tests for notify backends: ntfy and smsbox."""

from pathlib import Path

import pytest

from ip_monitor.config import Config, NotifyMethod, NtfyConfig, SMSBoxConfig
from ip_monitor.notify import notify, notify_ntfy, notify_smsbox


class _Session:
    pass


@pytest.mark.asyncio
async def test_notify_ntfy_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publish a message with Ntfy backend using stub classes."""
    published: list[dict] = []

    class StubMessage:
        def __init__(self, topic: str, title: str, message: str, priority: int):
            self.topic = topic
            self.title = title
            self.message = message
            self.priority = priority

    class StubNtfy:
        def __init__(self, server: str, session: _Session) -> None:
            self.server = server
            self.session = session

        async def publish(self, msg: StubMessage) -> None:
            published.append(
                {
                    "server": self.server,
                    "topic": msg.topic,
                    "title": msg.title,
                    "message": msg.message,
                    "priority": msg.priority,
                }
            )

    monkeypatch.setattr("ip_monitor.notify.Message", StubMessage)
    monkeypatch.setattr("ip_monitor.notify.Ntfy", StubNtfy)

    session = _Session()
    cfg = NtfyConfig(server="http://ntfy.local", topic="hello")
    await notify_ntfy(session, cfg, "hi there", title="T", priority=5)

    assert published == [
        {
            "server": "http://ntfy.local/",
            "topic": "hello",
            "title": "T",
            "message": "hi there",
            "priority": 5,
        }
    ]


@pytest.mark.asyncio
async def test_notify_smsbox_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Send an SMS via SMSBox backend using a stub client."""
    sent: list[tuple] = []

    class StubClient:
        def __init__(self, session: _Session, host: str, api_key: str):
            self.host = host
            self.api_key = api_key

        async def send(
            self, recipient: str, message: str, sender: str, options: dict
        ) -> None:
            sent.append((recipient, message, sender, options))

    monkeypatch.setattr("ip_monitor.notify.Client", StubClient)

    cfg = SMSBoxConfig(api_key="k", recipient="+3312345")
    await notify_smsbox(_Session(), cfg, "coucou")

    assert sent == [
        ("+3312345", "coucou", "expert", {"strategy": "2", "id": "1"})
    ]


@pytest.mark.asyncio
async def test_notify_dispatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Dispatch to the proper backend based on notify_method."""
    calls: list[str] = []

    async def f_ntfy(session: _Session, cfg: NtfyConfig, message: str):
        calls.append(f"ntfy:{message}")

    async def f_sms(session: _Session, cfg: SMSBoxConfig, message: str):
        calls.append(f"sms:{message}")

    monkeypatch.setattr("ip_monitor.notify.notify_ntfy", f_ntfy)
    monkeypatch.setattr("ip_monitor.notify.notify_smsbox", f_sms)

    session = _Session()
    cfg_ntfy = Config(
        db_path=tmp_path / "x.db",
        notify_method=NotifyMethod.NTFY_SH,
        ntfy={"server": "http://s", "topic": "t"},  # type: ignore[arg-type]
        ips=[{"ip": "1.1.1.1", "description": "d"}],  # type: ignore[list-item]
    )
    await notify(session, cfg_ntfy, "A")

    cfg_sms = Config(
        db_path=tmp_path / "y.db",
        notify_method=NotifyMethod.SMSBOX,
        smsbox={"api_key": "k", "recipient": "r"},  # type: ignore[arg-type]
        ips=[{"ip": "1.1.1.1", "description": "d"}],  # type: ignore[list-item]
    )
    await notify(session, cfg_sms, "B")

    assert calls == ["ntfy:A", "sms:B"]

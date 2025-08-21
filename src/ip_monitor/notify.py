"""Notify module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import ClientSession
from aiontfy import Message, Ntfy
from aiontfy.exceptions import NtfyException
from pysmsboxnet import exceptions
from pysmsboxnet.api import Client

from .config import NotifyMethod

if TYPE_CHECKING:
    from .config import Config, NtfyConfig, SMSBoxConfig


async def notify_ntfy(
    session: ClientSession,
    ntfy_config: NtfyConfig,
    message: str,
    title: str = "IP Monitor",
    priority: int = 4,
) -> None:
    """Envoie une notification en utilisant ntfy.sh."""
    try:
        ntfy = Ntfy(str(ntfy_config.server), session)
        ntfy_message = Message(
            topic=ntfy_config.topic,
            title=title,
            message=message,
            priority=priority,
        )
        await ntfy.publish(ntfy_message)
    except NtfyException:
        logging.exception("Erreur d'envoie de la notification via Ntfy")


async def notify_smsbox(
    session: ClientSession, config: SMSBoxConfig, message: str
) -> None:
    """Envoie une notification en utilisant smsbox.net."""
    sms: Client = Client(session, "api.smsbox.pro", config.api_key)
    try:
        await sms.send(
            config.recipient, message, "expert", {"strategy": "2", "id": "1"}
        )
    except exceptions.SMSBoxException:
        logging.exception("Erreur d'envoie du SMS'")


async def notify(session: ClientSession, config: Config, message: str) -> None:
    """Envoie une notification."""
    if config.notify_method == NotifyMethod.NTFY_SH:
        assert config.ntfy is not None
        await notify_ntfy(session, config.ntfy, message)
    elif config.notify_method == NotifyMethod.SMSBOX:
        assert config.smsbox is not None
        await notify_smsbox(session, config.smsbox, message)

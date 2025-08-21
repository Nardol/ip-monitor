"""IP-Monitor configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

import aiofiles
import yaml
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

# Fichier de configuration par défaut
DEFAULT_CONFIG_PATH: str = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "config.yaml"
)


class NotifyMethod(StrEnum):
    """Méthodes de notification possibles."""

    NTFY_SH = "ntfy"
    SMSBOX = "smsbox"


@dataclass
class UrlInfo:
    """Informations pour une URL."""

    url: str
    description: str


@dataclass
class IpInfo:
    """Informations pour une IP."""

    ip: str
    description: str


class SMSBoxConfig(BaseModel):
    """Configuration SMSBox."""

    api_key: str
    recipient: str


class NtfyConfig(BaseModel):
    """Configuration Ntfy.sh."""

    server: HttpUrl
    topic: str


class Config(BaseModel):
    """Configuration principale."""

    db_path: Path
    notify_method: NotifyMethod
    ntfy: NtfyConfig | None = Field(default=None)
    smsbox: SMSBoxConfig | None = Field(default=None)
    ips: list[IpInfo] = Field(default_factory=list)
    urls: list[UrlInfo] = Field(default_factory=list)
    precheck_enabled: bool = Field(default=True)
    # Paramètres de performance (valeurs par défaut sûres)
    precheck_timeout: float = Field(default=10.0, gt=0)
    ping_timeout: float = Field(default=15.0, gt=0)
    http_timeout: float = Field(default=7.0, gt=0)
    http_connector_limit: int = Field(default=50, gt=0)
    concurrency: int = Field(default=20, gt=0)

    @field_validator("db_path")
    @classmethod
    def validate_db_path(cls: type[Config], value: Path) -> Path:
        """Vérifie que le parent de db_path existe."""
        if not value.parent.exists():
            raise ValueError(f"{value.parent} does not exists")
        elif not value.parent.is_dir():
            raise ValueError(f"{value.parent} is not a directory")
        elif not os.access(value.parent, os.W_OK):
            raise ValueError(f"No write permission in {value.parent}")
        elif value.exists() and not os.access(value, os.W_OK):
            raise ValueError(f"No write permission in {value}")
        return value

    @model_validator(mode="after")
    def validate_ntfy(self: Self) -> Self:
        """S'assure que la configuration ntfy est bien spécifiée si ntfy.sh est utilisé."""
        if self.notify_method == "ntfy" and self.ntfy is None:
            raise ValueError(
                'ntfy configuration must be provided if notify_method is "ntfy"'
            )
        return self

    @model_validator(mode="after")
    def validate_smsbox(self: Self) -> Self:
        """S'assure que la clé d'API et le numéro sont bien spécifiées si smsbox est utilisé."""
        if self.notify_method == "smsbox" and self.smsbox is None:
            raise ValueError(
                'smsbox configuration must be provided if notify_method is "smsbox"'
            )
        return self

    @model_validator(mode="after")
    def check_ips_and_urls(self: Self) -> Self:
        """S'assure' qu'il y a bien au moins une IP ou une URL à surveiller."""
        if not self.ips and not self.urls:
            raise ValueError(
                'One of "ips" or "urls" must have at least one entry'
            )
        return self


async def load_config(config_file: str) -> Config:
    """Charge la configuration à partir de config.yaml."""
    async with aiofiles.open(config_file) as f:
        content: str = await f.read()
        logging.debug("Configuration file loaded.")
        raw_config = yaml.safe_load(content)
        raw_config["ips"] = [
            IpInfo(**ip_data) for ip_data in raw_config.get("ips", [])
        ]
        raw_config["urls"] = [
            UrlInfo(**url_data) for url_data in raw_config.get("urls", [])
        ]
        return Config.model_validate(raw_config)

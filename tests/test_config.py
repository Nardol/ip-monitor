"""Tests for configuration loading and validators (Pydantic)."""

from pathlib import Path

import pytest

from ip_monitor.config import (
    Config,
    IpInfo,
    NotifyMethod,
    UrlInfo,
    load_config,
)


@pytest.mark.asyncio
async def test_load_config_valid(tmp_path: Path) -> None:
    """Load a valid YAML file and map fields to models."""
    cfg_path = tmp_path / "conf.yaml"
    db_path = tmp_path / "ipmonitor.db"
    cfg_path.write_text(
        f"""
db_path: {db_path}
notify_method: ntfy
ntfy:
  server: http://ntfy.example.local
  topic: test-topic
ips:
  - ip: 192.0.2.1
    description: test-ip
urls:
  - url: example.local
    description: test-url
"""
    )

    cfg = await load_config(str(cfg_path))

    assert cfg.db_path == db_path
    assert cfg.notify_method == NotifyMethod.NTFY_SH
    assert (
        cfg.ntfy is not None
        and str(cfg.ntfy.server).rstrip("/") == "http://ntfy.example.local"
    )
    assert cfg.ntfy.topic == "test-topic"
    assert cfg.ips == [IpInfo(ip="192.0.2.1", description="test-ip")]
    assert cfg.urls == [UrlInfo(url="example.local", description="test-url")]


def test_config_validators_missing_ntfy(tmp_path: Path) -> None:
    """Ensure ntfy settings are required when notify_method is ntfy."""
    db_path = tmp_path / "db.sqlite"
    with pytest.raises(ValueError):
        Config(
            db_path=db_path,
            notify_method=NotifyMethod.NTFY_SH,
            ips=[IpInfo(ip="192.0.2.1", description="ip")],
        )


def test_config_validators_missing_smsbox(tmp_path: Path) -> None:
    """Ensure smsbox settings are required when notify_method is smsbox."""
    db_path = tmp_path / "db.sqlite"
    with pytest.raises(ValueError):
        Config(
            db_path=db_path,
            notify_method=NotifyMethod.SMSBOX,
            ips=[IpInfo(ip="192.0.2.1", description="ip")],
        )


def test_config_requires_ips_or_urls(tmp_path: Path) -> None:
    """Require at least one entry in ips or urls."""
    db_path = tmp_path / "db.sqlite"
    with pytest.raises(ValueError):
        Config(
            db_path=db_path,
            notify_method=NotifyMethod.NTFY_SH,
            ntfy={"server": "http://ntfy", "topic": "t"},  # type: ignore[arg-type]
        )

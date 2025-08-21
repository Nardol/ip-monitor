"""Tests for `_resolve_params` priority: CLI > ENV > YAML."""

import argparse
from pathlib import Path

import pytest

from ip_monitor.config import Config, NotifyMethod
from ip_monitor.monitoring import _resolve_params


def _base_config(tmp_path: Path) -> Config:
    return Config(
        db_path=tmp_path / "db.sqlite",
        notify_method=NotifyMethod.NTFY_SH,
        ntfy={"server": "http://s", "topic": "t"},  # type: ignore[arg-type]
        ips=[{"ip": "192.0.2.1", "description": "d"}],  # type: ignore[list-item]
    )


@pytest.mark.asyncio
async def test_resolve_params_cli_over_env_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI options override both ENV and YAML values."""
    cfg = _base_config(tmp_path).model_copy(
        update={
            "precheck_timeout": 9.9,
            "ping_timeout": 9.9,
            "http_timeout": 9.9,
            "http_connector_limit": 99,
            "concurrency": 99,
            "precheck_enabled": False,
        }
    )

    # ENV values that should be ignored because CLI is provided
    monkeypatch.setenv("IPM_PRECHECK_TIMEOUT", "1.1")
    monkeypatch.setenv("IPM_PING_TIMEOUT", "1.1")
    monkeypatch.setenv("IPM_HTTP_TIMEOUT", "1.1")
    monkeypatch.setenv("IPM_HTTP_CONNECTOR_LIMIT", "11")
    monkeypatch.setenv("IPM_CONCURRENCY", "11")
    monkeypatch.setenv("IPM_PRECHECK_ENABLED", "0")

    args = argparse.Namespace(
        precheck_timeout=0.5,
        ping_timeout=0.6,
        http_timeout=0.7,
        http_connector_limit=7,
        concurrency=8,
        precheck_enabled=True,
    )

    pto, p, ht, hcl, conc, pre = _resolve_params(args, cfg)
    assert (pto, p, ht, hcl, conc, pre) == (0.5, 0.6, 0.7, 7, 8, True)


@pytest.mark.asyncio
async def test_resolve_params_env_over_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ENV variables override YAML when CLI is not provided."""
    cfg = _base_config(tmp_path).model_copy(
        update={
            "precheck_timeout": 5.0,
            "ping_timeout": 6.0,
            "http_timeout": 7.0,
            "http_connector_limit": 50,
            "concurrency": 20,
            "precheck_enabled": True,
        }
    )

    # Set ENV so they should be used
    monkeypatch.setenv("IPM_PRECHECK_TIMEOUT", "1.2")
    monkeypatch.setenv("IPM_PING_TIMEOUT", "1.3")
    monkeypatch.setenv("IPM_HTTP_TIMEOUT", "1.4")
    monkeypatch.setenv("IPM_HTTP_CONNECTOR_LIMIT", "12")
    monkeypatch.setenv("IPM_CONCURRENCY", "13")
    monkeypatch.setenv("IPM_PRECHECK_ENABLED", "off")

    args = argparse.Namespace(
        precheck_timeout=None,
        ping_timeout=None,
        http_timeout=None,
        http_connector_limit=None,
        concurrency=None,
        precheck_enabled=None,
    )

    pto, p, ht, hcl, conc, pre = _resolve_params(args, cfg)
    assert (pto, p, ht, hcl, conc, pre) == (1.2, 1.3, 1.4, 12, 13, False)


@pytest.mark.asyncio
async def test_resolve_params_yaml_when_no_cli_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback to YAML values when CLI and ENV are absent."""
    # Ensure ENV is clear
    for k in [
        "IPM_PRECHECK_TIMEOUT",
        "IPM_PING_TIMEOUT",
        "IPM_HTTP_TIMEOUT",
        "IPM_HTTP_CONNECTOR_LIMIT",
        "IPM_CONCURRENCY",
        "IPM_PRECHECK_ENABLED",
    ]:
        monkeypatch.delenv(k, raising=False)

    cfg = _base_config(tmp_path).model_copy(
        update={
            "precheck_timeout": 2.5,
            "ping_timeout": 3.5,
            "http_timeout": 4.5,
            "http_connector_limit": 45,
            "concurrency": 15,
            "precheck_enabled": False,
        }
    )

    args = argparse.Namespace(
        precheck_timeout=None,
        ping_timeout=None,
        http_timeout=None,
        http_connector_limit=None,
        concurrency=None,
        precheck_enabled=None,
    )

    pto, p, ht, hcl, conc, pre = _resolve_params(args, cfg)
    assert (pto, p, ht, hcl, conc, pre) == (2.5, 3.5, 4.5, 45, 15, False)

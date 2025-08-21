"""Tests for invalid environment variables being ignored gracefully."""

from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_invalid_env_vars_are_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback to YAML defaults when ENV values are invalid."""
    # Minimal valid config with precheck disabled to avoid ICMP
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(
        f"""
db_path: {tmp_path / "db.sqlite"}
notify_method: ntfy
ntfy:
  server: http://s
  topic: t
ips:
  - ip: 192.0.2.3
    description: d
precheck_enabled: false
"""
    )

    # Invalid env values should be ignored and fall back to YAML defaults
    monkeypatch.setenv("IPM_PRECHECK_TIMEOUT", "not-a-float")
    monkeypatch.setenv("IPM_PING_TIMEOUT", "x")
    monkeypatch.setenv("IPM_HTTP_TIMEOUT", "y")
    monkeypatch.setenv("IPM_HTTP_CONNECTOR_LIMIT", "NaN")
    monkeypatch.setenv("IPM_CONCURRENCY", "oops")
    monkeypatch.setenv("IPM_PRECHECK_ENABLED", "maybe")

    # Avoid doing any real work
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr("ip_monitor.monitoring.check_ip", noop)
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", noop)
    monkeypatch.setattr("ip_monitor.monitoring.notify", noop)
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg)])

    await main()

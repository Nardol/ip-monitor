"""Tests for environment variable overrides in main()."""

import asyncio
from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_env_override_precheck_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use IPM_PRECHECK_TIMEOUT to override precheck timeout value."""
    # Prepare minimal valid config
    cfg_path = tmp_path / "conf.yaml"
    db_path = tmp_path / "db.sqlite"
    cfg_path.write_text(
        f"""
db_path: {db_path}
notify_method: ntfy
ntfy:
  server: http://ntfy.local
  topic: t
ips:
  - ip: 192.0.2.3
    description: test
"""
    )

    # Point argv to this config
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg_path)])

    # Set ENV override for precheck timeout
    monkeypatch.setenv("IPM_PRECHECK_TIMEOUT", "0.123")

    # Fake ping (returns False) so main exits after precheck
    async def fake_ping(_: str) -> bool:
        return False

    monkeypatch.setattr("ip_monitor.monitoring.ping", fake_ping)

    # Patch asyncio.wait_for to capture the timeout used for the precheck
    orig_wait_for = asyncio.wait_for
    seen_timeout: list[float] = []

    def stub_wait_for(awaitable, timeout=None):  # type: ignore[override]
        # Capture the timeout when awaiting our fake ping coroutine
        if (
            hasattr(awaitable, "cr_code")
            and awaitable.cr_code.co_name == "fake_ping"
        ):
            seen_timeout.append(timeout)
        return orig_wait_for(awaitable, timeout=timeout)

    monkeypatch.setattr(asyncio, "wait_for", stub_wait_for)

    await main()
    assert seen_timeout and abs(seen_timeout[0] - 0.123) < 1e-9  # noqa: PLR2004


@pytest.mark.asyncio
async def test_env_disable_precheck(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Disable precheck via IPM_PRECHECK_ENABLED=0 and skip ping call."""
    # Prepare minimal valid config
    cfg_path = tmp_path / "conf.yaml"
    db_path = tmp_path / "db.sqlite"
    cfg_path.write_text(
        f"""
db_path: {db_path}
notify_method: ntfy
ntfy:
  server: http://ntfy.local
  topic: t
ips:
  - ip: 192.0.2.3
    description: test
"""
    )

    # Point argv to this config
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("sys.argv", ["ip-monitor", "-c", str(cfg_path)])

    # Disable precheck via ENV
    monkeypatch.setenv("IPM_PRECHECK_ENABLED", "0")

    # Ensure precheck ping is not called
    async def ping_called(
        _: str,
    ) -> bool:  # pragma: no cover - test should intercept before this
        raise AssertionError("precheck ping should not be called when disabled")

    monkeypatch.setattr("ip_monitor.monitoring.ping", ping_called)

    # Avoid doing real work: stub the check functions
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr("ip_monitor.monitoring.check_ip", noop)
    monkeypatch.setattr("ip_monitor.monitoring.check_url_status", noop)

    await main()
    out = capsys.readouterr().out
    assert "Pas de connexion à Internet." not in out

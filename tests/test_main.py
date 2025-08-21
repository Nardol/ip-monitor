"""Main flow tests (precheck and exit conditions)."""

import sys
from pathlib import Path

import pytest

from ip_monitor.monitoring import main


@pytest.mark.asyncio
async def test_main_exits_when_no_internet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit early and print message when precheck fails."""
    # Build a minimal valid config file
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

    # Simulate args: ip-monitor -c <cfg>
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr(sys, "argv", ["ip-monitor", "-c", str(cfg_path)])

    # Force pre-check ping("1.1.1.1") to fail
    async def fake_ping(ip: str) -> bool:
        return False

    monkeypatch.setattr("ip_monitor.monitoring.ping", fake_ping)

    await main()
    captured = capsys.readouterr()
    assert "Pas de connexion à Internet." in captured.out

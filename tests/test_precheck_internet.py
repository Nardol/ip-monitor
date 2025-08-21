"""Direct tests for _precheck_internet helper to exercise branches."""

import pytest

from ip_monitor import monitoring


@pytest.mark.asyncio
async def test_precheck_internet_ok(monkeypatch: pytest.MonkeyPatch, capsys):
    """Do not print error and return True when ping succeeds."""

    async def ok(_ip: str) -> bool:
        return True

    monkeypatch.setattr(monitoring, "ping", ok)
    assert await monitoring._precheck_internet(0.01) is True
    out = capsys.readouterr().out
    assert "Vérification Internet" in out and "OK" in out
    assert "Pas de connexion" not in out


@pytest.mark.asyncio
async def test_precheck_internet_fail(monkeypatch: pytest.MonkeyPatch, capsys):
    """Print user-facing message and return False when ping fails."""

    async def nok(_ip: str) -> bool:
        return False

    monkeypatch.setattr(monitoring, "ping", nok)
    assert await monitoring._precheck_internet(0.01) is False
    out = capsys.readouterr().out
    assert "Pas de connexion" in out

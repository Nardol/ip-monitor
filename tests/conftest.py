# ruff: noqa: D100
import sys
from pathlib import Path
from types import ModuleType

# Ensure src layout is importable without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _install_dummy_aiontfy() -> None:
    if "aiontfy" in sys.modules:
        return
    aiontfy = ModuleType("aiontfy")
    aiontfy_ex = ModuleType("aiontfy.exceptions")

    class Ntfy:  # type: ignore[override]
        def __init__(self, server: str, session):
            self.server = server
            self.session = session

        async def publish(self, message):
            return None

    class Message:  # type: ignore[override]
        def __init__(self, topic: str, title: str, message: str, priority: int):
            self.topic = topic
            self.title = title
            self.message = message
            self.priority = priority

    class NtfyException(Exception):  # noqa: N818 - keep library-compatible name
        pass

    aiontfy.Ntfy = Ntfy  # type: ignore[attr-defined]
    aiontfy.Message = Message  # type: ignore[attr-defined]
    aiontfy_ex.NtfyException = NtfyException  # type: ignore[attr-defined]

    sys.modules["aiontfy"] = aiontfy
    sys.modules["aiontfy.exceptions"] = aiontfy_ex


def _install_dummy_smsbox() -> None:
    if "pysmsboxnet" in sys.modules:
        return
    smsbox_pkg = ModuleType("pysmsboxnet")
    smsbox_api = ModuleType("pysmsboxnet.api")
    smsbox_ex = ModuleType("pysmsboxnet.exceptions")

    class Client:  # type: ignore[override]
        def __init__(self, session, host: str, api_key: str):
            self.session = session
            self.host = host
            self.api_key = api_key

        async def send(
            self, recipient: str, message: str, sender: str, options: dict
        ):
            return None

    class SMSBoxException(Exception):  # noqa: N818 - keep library-compatible name
        pass

    smsbox_api.Client = Client  # type: ignore[attr-defined]
    smsbox_ex.SMSBoxException = SMSBoxException  # type: ignore[attr-defined]

    sys.modules["pysmsboxnet"] = smsbox_pkg
    sys.modules["pysmsboxnet.api"] = smsbox_api
    sys.modules["pysmsboxnet.exceptions"] = smsbox_ex


# Provide dummies for optional third-party modules used in notify
_install_dummy_aiontfy()
_install_dummy_smsbox()

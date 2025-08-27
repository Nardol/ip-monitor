"""Init file which only contains entry point."""
# PYTHON_ARGCOMPLETE_OK

from __future__ import annotations

import platform
import sys

from .monitoring import main


def entry_point() -> None:  # pragma: no cover - testé via main(), pas via CLI
    """Run CLI; refuse proprement sur Windows."""
    if platform.system() == "Windows":  # pragma: no cover
        print(  # pragma: no cover
            "Windows n'est pas pris en charge (iputils ping requis).",
            file=sys.stderr,
        )
        sys.exit(1)  # pragma: no cover

    try:
        import uvloop  # noqa: PLC0415
    except Exception:  # pragma: no cover - dépendance système manquante
        print(
            "uvloop n'est pas disponible alors qu'il est requis.",
            file=sys.stderr,
        )
        sys.exit(1)

    uvloop.run(main())  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    entry_point()  # pragma: no cover

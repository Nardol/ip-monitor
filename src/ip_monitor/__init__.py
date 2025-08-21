"""Init file which only contains entry point."""
# PYTHON_ARGCOMPLETE_OK

import uvloop

from .monitoring import main


def entry_point() -> None:
    """Run async main function."""
    uvloop.run(main())


if __name__ == "__main__":  # pragma: no cover
    uvloop.run(main())  # pragma: no cover

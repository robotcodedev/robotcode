import sys
from pathlib import Path

__file__ = str(Path(__file__).absolute())
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

if __name__ == "__main__" and __package__ is None or __package__ == "":
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[2]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    try:
        sys.path.remove(str(parent))
    except ValueError:
        pass

    __package__ = "robotcode.language_server"

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

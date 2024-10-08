import sys
from typing import List

from ..__version__ import __version__


class Repl:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = __version__

    def repl(self) -> None:
        pass

    def exit(self, exit_code: int = 0) -> None:
        sys.exit(exit_code)

    def keywords(self) -> List[str]:
        return ["repl", "exit"]

import sys

from ..__version__ import __version__


class Repl:
    """Marker library backing the RobotCode REPL/debugger integration.

    ``Breakpoint`` is the one keyword meant for use in your own suites (to pause
    into the debug prompt under ``robotcode robot-debug``); ``Repl`` and ``Exit``
    are used internally by ``robotcode repl`` and aren't normally called by hand.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = __version__

    def repl(self) -> None:
        """Internal marker keyword that opens the interactive REPL prompt.

        Called by the synthetic suite ``robotcode repl`` runs; not meant to be
        used directly in your own tests.
        """

    def breakpoint(self) -> None:
        """No-op marker keyword: the RobotCode debugger pauses here when attached.

        Place ``Breakpoint`` in a suite (after ``Library    robotcode.repl.Repl``)
        to drop into the debug prompt at that point under ``robotcode robot-debug``;
        in a normal ``robot`` run it does nothing.
        """

    def exit(self, exit_code: int = 0) -> None:
        sys.exit(exit_code)

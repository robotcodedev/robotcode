import sys

from robot.errors import ExecutionFailures

from ..__version__ import __version__
from ..base_interpreter import take_active_interpreter


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
        used directly in your own tests. Once the prompt is left, it fails with
        the failures ``robotcode repl`` recorded during the session, so the
        session test reflects them.
        """
        # The prompt loop ran while this keyword started; its body runs after it.
        interpreter = take_active_interpreter()
        if interpreter is not None and interpreter.failures:
            raise ExecutionFailures(interpreter.failures)

    def breakpoint(self) -> None:
        """No-op marker keyword: the RobotCode debugger pauses here when attached.

        Place ``Breakpoint`` in a suite (after ``Library    robotcode.repl.Repl``)
        to drop into the debug prompt at that point under ``robotcode robot-debug``;
        in a normal ``robot`` run it does nothing.
        """

    def exit(self, exit_code: int = 0) -> None:
        sys.exit(exit_code)

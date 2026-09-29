"""Click options and commands that RobotCode offers only from a certain
Robot Framework version on.

The version is declared once, with `since`: before it, `--help` hides the
option or command; `scripts/create_cmdline_doc.py` marks it with the version
in the generated CLI reference. `--help` itself carries no note, since it only
lists the option where the installed version has it.
"""

from typing import Any, Tuple

import click

from robotcode.robot.utils import RF_VERSION


class RobotVersionOption(click.Option):
    def __init__(self, *args: Any, since: Tuple[int, int], **kwargs: Any) -> None:
        kwargs["hidden"] = RF_VERSION < since
        super().__init__(*args, **kwargs)
        self.since = since


class RobotVersionCommand(click.Command):
    def __init__(self, *args: Any, since: Tuple[int, int], **kwargs: Any) -> None:
        kwargs["hidden"] = RF_VERSION < since
        super().__init__(*args, **kwargs)
        self.since = since

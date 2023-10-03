from typing import List

import click
from robotcode.plugin import hookimpl

from .cli import discover, libdoc, rebot, robot, testdoc


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [robot, rebot, libdoc, testdoc, discover]

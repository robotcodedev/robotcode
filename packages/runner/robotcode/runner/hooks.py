from typing import List

import click

from robotcode.plugin import hookimpl

from .cli import libdoc, rebot, robot


@hookimpl
def hatch_register_cli_commands() -> List[click.Command]:
    return [robot, rebot, libdoc]

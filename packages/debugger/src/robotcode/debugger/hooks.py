from typing import List

import click
from robotcode.plugin import hookimpl

from .cli import debug
from .launcher.cli import debug_launch


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [debug, debug_launch]

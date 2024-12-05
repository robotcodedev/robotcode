from typing import List

import click

from robotcode.plugin import hookimpl

from .cli import repl_server


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [repl_server]

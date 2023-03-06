from typing import List

import click

from robotcode.plugin import hookimpl

from .cli import run


@hookimpl
def hatch_register_cli_commands() -> List[click.Command]:
    return [run]

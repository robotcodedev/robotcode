from typing import List

import click

from robotcode.plugin import hookimpl

from .config.cli import config


@hookimpl
def hatch_register_cli_commands() -> List[click.Command]:
    return [config]

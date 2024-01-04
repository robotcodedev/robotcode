from typing import List

import click

from robotcode.plugin import hookimpl

from .cli import language_server


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [language_server]

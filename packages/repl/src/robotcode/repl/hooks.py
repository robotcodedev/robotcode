from typing import List

import click

from robotcode.plugin import hookimpl

from .cli import repl, robot_debug
from .doc_cli import doc
from .session_cli import session


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [repl, robot_debug, doc, session]

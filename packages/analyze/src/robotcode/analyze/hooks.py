from typing import Any, List, Tuple, Type

import click
from robotcode.plugin import hookimpl

from .cli import analyze
from .config import AnalyzerConfig


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [analyze]


@hookimpl
def register_config_classes() -> List[Tuple[str, Type[Any]]]:
    return [("tool.robotcode-analyze", AnalyzerConfig)]

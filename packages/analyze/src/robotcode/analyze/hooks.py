from typing import List

import click

from robotcode.plugin import hookimpl
from robotcode.plugin.specs import ToolConfig

from .cli import analyze
from .config import AnalyzeConfig


@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [analyze]


@hookimpl
def register_tool_config_classes() -> List[ToolConfig]:
    return [ToolConfig("robotcode-analyze", AnalyzeConfig)]

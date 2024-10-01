from typing import Any, Callable, List, NamedTuple, Type, TypeVar, cast

import click
import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("robotcode"))


@hookspec
def register_cli_commands() -> List[click.Command]:  # type: ignore
    """Register new command for the commandline."""


class ToolConfig(NamedTuple):
    tool_name: str
    config_class: Type[Any]


@hookspec
def register_tool_config_classes() -> List[ToolConfig]:  # type: ignore
    """Registers a class that gives information about a tool configuration."""

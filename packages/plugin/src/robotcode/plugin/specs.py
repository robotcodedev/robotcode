from typing import Any, Callable, List, Tuple, Type, TypeVar, cast

import click
import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("robotcode"))


@hookspec
def register_cli_commands() -> List[click.Command]:  # type: ignore
    """Register new command for the commandline."""


TConfigClass = TypeVar("TConfigClass")


@hookspec
def register_config_classes() -> List[Tuple[str, Type[TConfigClass]]]:  # type: ignore
    """Registers a class that gives information about a configuration."""

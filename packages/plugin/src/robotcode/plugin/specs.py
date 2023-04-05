from typing import Any, Callable, List, TypeVar, cast

import click
import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("robotcode"))


@hookspec
def hatch_register_cli_commands() -> List[click.Command]:  # type: ignore
    """Register new command for the commandline."""

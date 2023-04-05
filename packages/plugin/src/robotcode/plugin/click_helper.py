from enum import Enum
from typing import Any, Callable, Type, Union

import click


class EnumChoice(click.Choice):
    """A click.Choice that accepts Enum values."""

    def __init__(self, choices: Type[Enum], case_sensitive: bool = True) -> None:
        super().__init__(choices, case_sensitive)  # type: ignore


FC = Union[Callable[..., Any], click.Command]


def add_options(*options: FC) -> FC:
    def _add_options(func: FC) -> FC:
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options

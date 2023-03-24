from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Optional, TypeVar, cast

import click
import pluggy

__all__ = ["hookimpl", "ClickCommonConfig", "pass_common_config"]

F = TypeVar("F", bound=Callable[..., Any])
hookimpl = cast(Callable[[F], F], pluggy.HookimplMarker("robotcode"))


class ColoredOutput(str, Enum):
    AUTO = "auto"
    YES = "yes"
    NO = "no"


@dataclass
class ClickCommonConfig:
    config_file: Optional[Path] = None
    profiles: Optional[List[str]] = None
    dry: bool = False
    verbose: bool = False
    colored_output: ColoredOutput = ColoredOutput.AUTO


pass_common_config = click.make_pass_decorator(ClickCommonConfig, ensure=True)

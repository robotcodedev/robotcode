from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, TypeVar, cast

import click
import pluggy

__all__ = ["hookimpl", "CommonConfig", "pass_common_config"]

F = TypeVar("F", bound=Callable[..., Any])
hookimpl = cast(Callable[[F], F], pluggy.HookimplMarker("robotcode"))


@dataclass
class CommonConfig:
    config_file: Optional[Path] = None
    profiles: Optional[List[str]] = None
    dry: bool = False
    verbose: bool = False


pass_common_config = click.make_pass_decorator(CommonConfig, ensure=True)

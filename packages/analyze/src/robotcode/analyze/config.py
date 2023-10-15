# ruff: noqa: RUF009
from dataclasses import dataclass
from typing import List, Optional, Union

from robotcode.robot.config.model import BaseOptions, field


@dataclass
class Dummy:
    some_field: Optional[str] = field(default="some value", description="Some field")


@dataclass
class AnalyzerConfig(BaseOptions):
    select: Optional[List[Union[str, Dummy]]] = field(description="Selects which rules are run.")
    extend_select: Optional[List[Union[str, Dummy]]] = field(description="Extends the rules which are run.")
    ignore: Optional[List[str]] = field(description="Defines which rules are ignored.")
    extend_ignore: Optional[List[str]] = field(description="Extends the rules which are ignored.")

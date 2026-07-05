"""Data models emitted by `robotcode discover`.

All models inherit from `CamelSnakeMixin` so the JSON output uses
camelCase keys (`fullName`, `relSource`, `supportsParseInclude`, …)
consistent with the `results` family. Editor integrations and CI
recipes rely on that shape.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from robotcode.core.lsp.types import Diagnostic, DocumentUri, Range
from robotcode.core.utils.dataclasses import CamelSnakeMixin


@dataclass
class TestItem(CamelSnakeMixin):
    type: str
    id: str
    name: str
    longname: str
    lineno: Optional[int] = None
    uri: Optional[DocumentUri] = None
    rel_source: Optional[str] = None
    source: Optional[str] = None
    children: Optional[List["TestItem"]] = None
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None
    rpa: Optional[bool] = None


@dataclass
class ResultItem(CamelSnakeMixin):
    items: List[TestItem]
    diagnostics: Optional[Dict[str, List[Diagnostic]]] = None
    filters_applied: Optional[Dict[str, str]] = None
    supports_parse_include: bool = False


@dataclass
class Statistics(CamelSnakeMixin):
    suites: int = 0
    suites_with_tests: int = 0
    suites_with_tasks: int = 0
    tests: int = 0
    tasks: int = 0


@dataclass
class TagsResult(CamelSnakeMixin):
    tags: Dict[str, List[TestItem]]
    filters_applied: Optional[Dict[str, str]] = None


@dataclass
class Info(CamelSnakeMixin):
    robot_version_string: str
    robot_env: Dict[str, str]
    robotcode_version_string: str
    python_version_string: str
    executable: str
    machine: str
    processor: str
    platform: str
    system: str
    system_version: str

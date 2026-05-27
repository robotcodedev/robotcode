"""Minimal SARIF 2.1.0 object model for `robotcode analyze code`.

Only the subset of SARIF that we actually emit is modelled. All classes inherit
from `CamelSnakeMixin`, which turns snake_case fields into the camelCase keys
SARIF expects (`ruleId`, `physicalLocation`, `startLine`, …). Fields that are
not valid Python identifiers (`$schema`) use a `field(metadata={"alias": ...})`.

Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from robotcode.core.utils.dataclasses import CamelSnakeMixin

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


@dataclass
class Message(CamelSnakeMixin):
    text: str


@dataclass
class ArtifactLocation(CamelSnakeMixin):
    uri: str
    uri_base_id: Optional[str] = None


@dataclass
class Region(CamelSnakeMixin):
    # SARIF regions are 1-based for both line and column.
    start_line: int
    start_column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None


@dataclass
class PhysicalLocation(CamelSnakeMixin):
    artifact_location: ArtifactLocation
    region: Optional[Region] = None


@dataclass
class Location(CamelSnakeMixin):
    physical_location: Optional[PhysicalLocation] = None
    message: Optional[Message] = None


@dataclass
class ReportingDescriptor(CamelSnakeMixin):
    """A rule definition (tool.driver.rules[])."""

    id: str
    name: Optional[str] = None


@dataclass
class Result(CamelSnakeMixin):
    rule_id: str
    message: Message
    level: str = "warning"  # error | warning | note | none
    rule_index: Optional[int] = None
    locations: Optional[List[Location]] = None
    related_locations: Optional[List[Location]] = None
    partial_fingerprints: Optional[Dict[str, str]] = None


@dataclass
class ToolComponent(CamelSnakeMixin):
    name: str
    version: Optional[str] = None
    information_uri: Optional[str] = None
    rules: Optional[List[ReportingDescriptor]] = None


@dataclass
class Tool(CamelSnakeMixin):
    driver: ToolComponent


@dataclass
class Run(CamelSnakeMixin):
    tool: Tool
    results: List[Result] = field(default_factory=list)


@dataclass
class SarifLog(CamelSnakeMixin):
    runs: List[Run] = field(default_factory=list)
    version: str = SARIF_VERSION
    schema: str = field(default=SARIF_SCHEMA, metadata={"alias": "$schema"})

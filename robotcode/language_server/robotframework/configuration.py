from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..common.parts.workspace import ConfigBase, config_section


@config_section("robotcode.languageServer")
@dataclass
class LanguageServerConfig(ConfigBase):
    mode: str = "stdio"
    tcp_port: int = 0
    args: Tuple[str, ...] = field(default_factory=tuple)


@config_section("robotcode.robot")
@dataclass
class RobotConfig(ConfigBase):
    args: Tuple[str, ...] = field(default_factory=tuple)
    python_path: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    output_dir: Optional[str] = None
    output_file: Optional[str] = None
    log_file: Optional[str] = None
    debug_file: Optional[str] = None
    log_level: Optional[str] = None


@config_section("robotcode.syntax")
@dataclass
class SyntaxConfig(ConfigBase):
    section_style: str = "*** {name}s ***"


@config_section("robotcode.robocop")
@dataclass
class RoboCopConfig(ConfigBase):
    enabled: bool = True
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    configurations: List[str] = field(default_factory=list)


@config_section("robotcode.robotidy")
@dataclass
class RoboTidyConfig(ConfigBase):
    enabled: bool = True


@config_section("robotcode.workspace")
@dataclass
class WorkspaceConfig(ConfigBase):
    exclude_patterns: List[str] = field(default_factory=list)


@config_section("robotcode")
@dataclass
class RobotCodeConfig(ConfigBase):
    language_server: LanguageServerConfig = field(default_factory=LanguageServerConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    syntax: SyntaxConfig = field(default_factory=SyntaxConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)

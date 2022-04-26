from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..common.parts.diagnostics import DiagnosticsMode
from ..common.parts.workspace import ConfigBase, config_section


@config_section("robotcode.languageServer")
@dataclass
class LanguageServerConfig(ConfigBase):
    mode: str = "stdio"
    tcp_port: int = 0
    args: Tuple[str, ...] = field(default_factory=tuple)


class RpaMode(Enum):
    DEFAULT = "default"
    RPA = "rpa"
    NORPA = "norpa"


@config_section("robotcode.robot")
@dataclass
class RobotConfig(ConfigBase):
    args: Tuple[str, ...] = field(default_factory=tuple)
    python_path: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    variable_files: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    output_dir: Optional[str] = None
    output_file: Optional[str] = None
    log_file: Optional[str] = None
    debug_file: Optional[str] = None
    log_level: Optional[str] = None
    mode: Optional[RpaMode] = None

    def get_rpa_mode(self) -> Optional[bool]:
        if self.mode == RpaMode.RPA:
            return True
        elif self.mode == RpaMode.NORPA:
            return False
        return None


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


class AnalysisProgressMode(Enum):
    SIMPLE = "simple"
    DETAILED = "detailed"


@config_section("robotcode.analysis")
@dataclass
class AnalysisConfig(ConfigBase):
    diagnostic_mode: DiagnosticsMode = DiagnosticsMode.OPENFILESONLY
    progress_mode: AnalysisProgressMode = AnalysisProgressMode.SIMPLE
    max_project_file_count: int = 1000
    references_code_lens: bool = True


@config_section("robotcode")
@dataclass
class RobotCodeConfig(ConfigBase):
    language_server: LanguageServerConfig = field(default_factory=LanguageServerConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    syntax: SyntaxConfig = field(default_factory=SyntaxConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)

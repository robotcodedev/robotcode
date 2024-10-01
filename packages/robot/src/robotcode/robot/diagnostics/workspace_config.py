from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from robotcode.core.workspace import ConfigBase, config_section


class RpaMode(Enum):
    DEFAULT = "default"
    RPA = "rpa"
    NORPA = "norpa"


@config_section("robotcode.robot")
@dataclass
class RobotConfig(ConfigBase):
    args: List[str] = field(default_factory=list)
    python_path: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    variable_files: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    output_dir: Optional[str] = None
    output_file: Optional[str] = None
    log_file: Optional[str] = None
    debug_file: Optional[str] = None
    log_level: Optional[str] = None
    mode: Optional[RpaMode] = None
    languages: Optional[List[str]] = None
    parsers: Optional[List[str]] = None

    def get_rpa_mode(self) -> Optional[bool]:
        if self.mode == RpaMode.RPA:
            return True
        if self.mode == RpaMode.NORPA:
            return False
        return None


class CacheSaveLocation(Enum):
    WORKSPACE_FOLDER = "workspaceFolder"
    WORKSPACE_STORAGE = "workspaceStorage"


@config_section("robotcode.analysis.cache")
@dataclass
class CacheConfig(ConfigBase):
    save_location: CacheSaveLocation = CacheSaveLocation.WORKSPACE_STORAGE
    ignored_libraries: List[str] = field(default_factory=list)
    ignored_variables: List[str] = field(default_factory=list)
    ignore_arguments_for_library: List[str] = field(default_factory=list)


@config_section("robotcode.analysis.robot")
@dataclass
class AnalysisRobotConfig(ConfigBase):
    global_library_search_order: List[str] = field(default_factory=list)


@config_section("robotcode.analysis.diagnosticModifiers")
@dataclass
class AnalysisDiagnosticModifiersConfig(ConfigBase):
    ignore: List[str] = field(default_factory=list)
    error: List[str] = field(default_factory=list)
    warning: List[str] = field(default_factory=list)
    information: List[str] = field(default_factory=list)
    hint: List[str] = field(default_factory=list)


@dataclass
class WorkspaceAnalysisConfig:
    cache: CacheConfig = field(default_factory=CacheConfig)
    robot: AnalysisRobotConfig = field(default_factory=AnalysisRobotConfig)
    modifiers: AnalysisDiagnosticModifiersConfig = field(default_factory=AnalysisDiagnosticModifiersConfig)

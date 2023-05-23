from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from robotcode.language_server.common.parts.diagnostics import AnalysisProgressMode, DiagnosticsMode
from robotcode.language_server.common.parts.workspace import ConfigBase, config_section


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


class CacheSaveLocation(Enum):
    WORKSPACE_FOLDER = "workspaceFolder"
    WORKSPACE_STORAGE = "workspaceStorage"


@config_section("robotcode.robot")
@dataclass
class RobotConfig(ConfigBase):
    args: List[str] = field(default_factory=list)
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
    languages: Optional[List[str]] = None
    parsers: Optional[List[str]] = None

    def get_rpa_mode(self) -> Optional[bool]:
        if self.mode == RpaMode.RPA:
            return True
        if self.mode == RpaMode.NORPA:
            return False
        return None


@config_section("robotcode.completion")
@dataclass
class CompletionConfig(ConfigBase):
    filter_default_language: bool = False
    header_style: Optional[str] = None


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
    ignore_git_dir: bool = False
    config: Optional[str] = None


@config_section("robotcode.workspace")
@dataclass
class WorkspaceConfig(ConfigBase):
    exclude_patterns: List[str] = field(default_factory=list)


@config_section("robotcode.analysis.cache")
@dataclass
class Cache(ConfigBase):
    save_location: CacheSaveLocation = CacheSaveLocation.WORKSPACE_STORAGE
    ignored_libraries: List[str] = field(default_factory=list)
    ignored_variables: List[str] = field(default_factory=list)


@config_section("robotcode.analysis")
@dataclass
class AnalysisConfig(ConfigBase):
    diagnostic_mode: DiagnosticsMode = DiagnosticsMode.OPENFILESONLY
    progress_mode: AnalysisProgressMode = AnalysisProgressMode.OFF
    max_project_file_count: int = 5000
    references_code_lens: bool = False
    find_unused_references: bool = False
    cache: Cache = field(default_factory=Cache)


@config_section("robotcode.documentationServer")
@dataclass
class DocumentationServerConfig(ConfigBase):
    start_port: int = 3100
    end_port: int = 3199


@config_section("robotcode.inlayHints")
@dataclass
class InlayHintsConfig(ConfigBase):
    parameter_names: bool = True
    namespaces: bool = True


@config_section("robotcode")
@dataclass
class RobotCodeConfig(ConfigBase):
    language_server: LanguageServerConfig = field(default_factory=LanguageServerConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    syntax: CompletionConfig = field(default_factory=CompletionConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    documentation_server: DocumentationServerConfig = field(default_factory=DocumentationServerConfig)
    inlay_hints: InlayHintsConfig = field(default_factory=InlayHintsConfig)

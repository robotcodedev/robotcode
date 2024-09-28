from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from robotcode.core.workspace import ConfigBase, config_section
from robotcode.language_server.common.parts.diagnostics import AnalysisProgressMode, DiagnosticsMode
from robotcode.robot.diagnostics.workspace_config import (
    AnalysisDiagnosticModifiersConfig,
    AnalysisRobotConfig,
    CacheConfig,
    RobotConfig,
)


@config_section("robotcode.languageServer")
@dataclass
class LanguageServerConfig(ConfigBase):
    mode: str = "stdio"
    tcp_port: int = 0
    args: Tuple[str, ...] = field(default_factory=tuple)


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


@config_section("robotcode.documentationServer")
@dataclass
class DocumentationServerConfig(ConfigBase):
    start_port: int = 3100
    end_port: int = 3199
    start_on_demand: bool = True


@config_section("robotcode.inlayHints")
@dataclass
class InlayHintsConfig(ConfigBase):
    parameter_names: bool = True
    namespaces: bool = True


@config_section("robotcode.analysis")
@dataclass
class AnalysisConfig(ConfigBase):
    diagnostic_mode: DiagnosticsMode = DiagnosticsMode.OPENFILESONLY
    progress_mode: AnalysisProgressMode = AnalysisProgressMode.OFF
    references_code_lens: bool = False
    find_unused_references: bool = False
    cache: CacheConfig = field(default_factory=CacheConfig)
    robot: AnalysisRobotConfig = field(default_factory=AnalysisRobotConfig)
    modifiers: AnalysisDiagnosticModifiersConfig = field(default_factory=AnalysisDiagnosticModifiersConfig)


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

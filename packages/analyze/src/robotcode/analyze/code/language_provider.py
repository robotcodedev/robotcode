from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from robotcode.analyze.code.diagnostics_context import DiagnosticsContext
from robotcode.core.ignore_spec import DEFAULT_SPEC_RULES, GIT_IGNORE_FILE, ROBOT_IGNORE_FILE, IgnoreSpec, iter_files
from robotcode.core.language import LanguageDefinition
from robotcode.core.workspace import WorkspaceFolder
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceConfig


class LanguageProvider(ABC):
    def __init__(self, diagnostics_context: DiagnosticsContext) -> None:
        self.diagnostics_context = diagnostics_context

        self.verbose_callback: Optional[Callable[[str], None]] = None

    @classmethod
    @abstractmethod
    def get_language_definitions(cls, profile: RobotBaseProfile, root: Path) -> List[LanguageDefinition]: ...

    @abstractmethod
    def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]: ...

    def iter_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
        """The files of a workspace folder, without the excluded and ignored ones."""
        config = self.diagnostics_context.workspace.get_configuration(WorkspaceConfig, folder.uri)

        exclude_patterns = [
            *self.diagnostics_context.analysis_config.exclude_patterns,
            *(config.exclude_patterns or []),
        ]
        return iter_files(
            folder.uri.to_path(),
            ignore_files=[ROBOT_IGNORE_FILE, GIT_IGNORE_FILE],
            include_hidden=False,
            parent_spec=IgnoreSpec.from_list(
                [*DEFAULT_SPEC_RULES, *exclude_patterns],
                folder.uri.to_path(),
            ),
            verbose_callback=self.verbose_callback,
            verbose_trace=False,
        )

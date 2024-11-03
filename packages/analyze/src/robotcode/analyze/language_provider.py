from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from robotcode.analyze.diagnostics_context import DiagnosticsContext
from robotcode.core.language import LanguageDefinition
from robotcode.core.workspace import WorkspaceFolder


class LanguageProvider(ABC):
    def __init__(self, diagnostics_context: DiagnosticsContext) -> None:
        self.diagnostics_context = diagnostics_context

        self.verbose_callback: Optional[Callable[[str], None]] = None

    @classmethod
    @abstractmethod
    def get_language_definitions(cls) -> List[LanguageDefinition]: ...

    @abstractmethod
    def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]: ...

from abc import ABC, abstractmethod
from typing import List, Optional, Union

from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import Diagnostic
from robotcode.core.text_document import TextDocument
from robotcode.core.workspace import Workspace, WorkspaceFolder
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig


class DiagnosticHandlers:
    @event
    def document_analyzers(sender, document: TextDocument) -> Optional[List[Diagnostic]]: ...
    @event
    def folder_initializers(sender, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]: ...

    @event
    def collectors(sender, document: TextDocument) -> Optional[List[Diagnostic]]: ...

    def initialize_folder(self, folder: WorkspaceFolder) -> List[Union[List[Diagnostic], BaseException, None]]:
        return self.folder_initializers(
            self,
            folder,
            return_exceptions=True,
        )

    def analyze_document(self, document: TextDocument) -> List[Union[List[Diagnostic], BaseException, None]]:
        return self.document_analyzers(
            self,
            document,
            callback_filter=language_id_filter(document),
            return_exceptions=True,
        )

    def collect_diagnostics(self, document: TextDocument) -> List[Union[List[Diagnostic], BaseException, None]]:
        return self.collectors(
            self,
            document,
            callback_filter=language_id_filter(document),
            return_exceptions=True,
        )


class DiagnosticsContext(ABC):
    @property
    @abstractmethod
    def analysis_config(self) -> WorkspaceAnalysisConfig: ...

    @property
    @abstractmethod
    def profile(self) -> RobotBaseProfile: ...

    @property
    @abstractmethod
    def workspace(self) -> Workspace: ...

    @property
    @abstractmethod
    def diagnostics(self) -> DiagnosticHandlers: ...

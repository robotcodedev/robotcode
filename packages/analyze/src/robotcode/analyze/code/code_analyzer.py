from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Union

from robotcode.core.ignore_spec import IgnoreSpec
from robotcode.core.lsp.types import Diagnostic
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.path import normalized_path
from robotcode.core.workspace import Workspace, WorkspaceFolder
from robotcode.plugin import Application
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig

from .diagnostics_context import DiagnosticHandlers, DiagnosticsContext
from .robot_framework_language_provider import RobotFrameworkLanguageProvider


@dataclass
class DocumentDiagnosticReport:
    document: TextDocument
    items: List[Diagnostic]


@dataclass
class FolderDiagnosticReport:
    folder: WorkspaceFolder
    items: List[Diagnostic]


class CodeAnalyzer(DiagnosticsContext):
    def __init__(
        self,
        app: Application,
        analysis_config: WorkspaceAnalysisConfig,
        robot_profile: RobotBaseProfile,
        root_folder: Optional[Path],
    ):
        self.app = app
        self._analysis_config = analysis_config or WorkspaceAnalysisConfig()

        self._robot_profile = robot_profile
        self._root_folder = root_folder if root_folder is not None else Path.cwd()

        self._workspace = Workspace(
            Uri.from_path(self.root_folder), [WorkspaceFolder(self.root_folder.name, Uri.from_path(self.root_folder))]
        )

        self._dispatcher = DiagnosticHandlers()

        self.language_handler_types = {RobotFrameworkLanguageProvider}
        self.workspace.documents.languages.extend(RobotFrameworkLanguageProvider.get_language_definitions())
        self.language_handlers = [cls(self) for cls in self.language_handler_types]
        if app.config.verbose:
            app.verbose(
                f"Registered language handlers: {', '.join(type(t).__qualname__ for t in self.language_handlers)}"
            )
            for handler in self.language_handlers:
                handler.verbose_callback = app.verbose

    @property
    def analysis_config(self) -> WorkspaceAnalysisConfig:
        return self._analysis_config

    @property
    def profile(self) -> RobotBaseProfile:
        return self._robot_profile

    @property
    def root_folder(self) -> Path:
        return self._root_folder

    @property
    def workspace(self) -> Workspace:
        return self._workspace

    @property
    def diagnostics(self) -> DiagnosticHandlers:
        return self._dispatcher

    def run(
        self, paths: Iterable[Path] = {}, filter: Iterable[str] = {}
    ) -> Iterable[Union[DocumentDiagnosticReport, FolderDiagnosticReport]]:
        for folder in self.workspace.workspace_folders:
            self.app.verbose(f"Initialize folder {folder.uri.to_path()}")
            initialize_result = self.diagnostics.initialize_folder(folder)
            if initialize_result is not None:
                diagnostics: List[Diagnostic] = []
                for item in initialize_result:
                    if item is None:
                        continue
                    elif isinstance(item, BaseException):
                        self.app.error(f"Error analyzing {folder.uri.to_path()}: {item}")
                    else:
                        diagnostics.extend(item)

                yield FolderDiagnosticReport(folder, diagnostics)

            documents = self.collect_documents(folder, paths=paths, filter=filter)

            self.app.verbose(f"Analyzing {len(documents)} documents")
            for document in documents:
                analyze_result = self.diagnostics.analyze_document(document)
                if analyze_result is not None:
                    diagnostics = []
                    for item in analyze_result:
                        if item is None:
                            continue
                        elif isinstance(item, BaseException):
                            self.app.error(f"Error analyzing {document.uri.to_path()}: {item}")
                        else:
                            diagnostics.extend(item)

                    yield DocumentDiagnosticReport(document, diagnostics)

            self.app.verbose(f"Collect Diagnostics for {len(documents)} documents")
            for document in documents:
                analyze_result = self.diagnostics.collect_diagnostics(document)
                if analyze_result is not None:
                    diagnostics = []
                    for item in analyze_result:
                        if item is None:
                            continue
                        elif isinstance(item, BaseException):
                            self.app.error(f"Error collecting diagnostics for {document.uri.to_path()}: {item}")
                        else:
                            diagnostics.extend(item)

                    yield DocumentDiagnosticReport(document, diagnostics)

    def collect_documents(
        self, folder: WorkspaceFolder, paths: Iterable[Path] = {}, filter: Iterable[str] = {}
    ) -> List[TextDocument]:
        folder_root = folder.uri.to_path()
        full_paths = [normalized_path(p).as_posix() for p in paths]

        ignore_spec = IgnoreSpec.from_list(filter, folder_root)

        documents: List[TextDocument] = []

        self.app.verbose(f"Collecting files in workspace folder '{folder.uri.to_path()}'")
        for handler in self.language_handlers:
            for file in handler.collect_workspace_folder_files(folder):
                try:
                    document = self.workspace.documents.get_or_open_document(file)
                    document_path = normalized_path(document.uri.to_path()).as_posix()
                    if full_paths and not any(document_path.startswith(p) for p in full_paths):
                        continue

                    if ignore_spec.rules and not ignore_spec.matches(document.uri.to_path()):
                        continue

                    documents.append(document)

                except (SystemExit, KeyboardInterrupt):
                    raise
                except Exception as e:
                    self.app.error(f"Error reading {file}: {e}")
                    continue

        return documents

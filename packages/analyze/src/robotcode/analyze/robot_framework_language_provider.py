import glob
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional

from robot.utils import FileReader

from robotcode.analyze.diagnostics_context import DiagnosticsContext
from robotcode.core.filewatcher import FileWatcherManagerDummy
from robotcode.core.ignore_spec import DEFAULT_SPEC_RULES, GIT_IGNORE_FILE, ROBOT_IGNORE_FILE, IgnoreSpec, iter_files
from robotcode.core.language import LanguageDefinition, language_id
from robotcode.core.lsp.types import Diagnostic
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper
from robotcode.robot.diagnostics.workspace_config import WorkspaceConfig

from .language_provider import LanguageProvider

ROBOTFRAMEWORK_LANGUAGE_ID = "robotframework"


class RobotFrameworkLanguageProvider(LanguageProvider):
    LANGUAGE_DEFINITION = LanguageDefinition(
        id=ROBOTFRAMEWORK_LANGUAGE_ID,
        extensions=[".robot", ".resource"],
        extensions_ignore_case=True,
        aliases=["Robot Framework", "robotframework"],
    )

    @classmethod
    def get_language_definitions(cls) -> List[LanguageDefinition]:
        return [cls.LANGUAGE_DEFINITION]

    def __init__(self, diagnostics_context: DiagnosticsContext) -> None:
        super().__init__(diagnostics_context)

        self._update_python_path()

        self._document_cache = DocumentsCacheHelper(
            self.diagnostics_context.workspace,
            self.diagnostics_context.workspace.documents,
            FileWatcherManagerDummy(),
            self.diagnostics_context.profile,
            self.diagnostics_context.analysis_config,
        )

        self.diagnostics_context.workspace.documents.on_read_document_text.add(self.on_read_document_text)
        self.diagnostics_context.diagnostics.folder_initializers.add(self.analyze_folder)
        self.diagnostics_context.diagnostics.document_analyzers.add(self.analyze_document)

    def _update_python_path(self) -> None:
        if self.diagnostics_context.workspace.root_uri is not None:
            for p in self.diagnostics_context.profile.python_path or []:
                pa = Path(str(p))
                if not pa.is_absolute():
                    pa = Path(self.diagnostics_context.workspace.root_uri.to_path(), pa)

                absolute_path = str(pa.absolute())
                for f in glob.glob(absolute_path):
                    if Path(f).is_dir() and f not in sys.path:
                        sys.path.insert(0, f)

    @language_id("robotframework")
    def on_read_document_text(self, sender: Any, uri: Uri) -> str:
        with FileReader(uri.to_path()) as reader:
            return str(reader.read())

    def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
        config = self.diagnostics_context.workspace.get_configuration(WorkspaceConfig, folder.uri)

        extensions = self.LANGUAGE_DEFINITION.extensions

        exclude_patterns = [
            *self.diagnostics_context.analysis_config.exclude_patterns,
            *(config.exclude_patterns or []),
        ]
        return filter(
            lambda f: f.suffix.lower() in extensions,
            iter_files(
                folder.uri.to_path(),
                ignore_files=[ROBOT_IGNORE_FILE, GIT_IGNORE_FILE],
                include_hidden=False,
                parent_spec=IgnoreSpec.from_list(
                    [*DEFAULT_SPEC_RULES, *exclude_patterns],
                    folder.uri.to_path(),
                ),
                verbose_callback=self.verbose_callback,
                verbose_trace=False,
            ),
        )

    def analyze_document(self, sender: Any, document: TextDocument) -> Optional[List[Diagnostic]]:
        namespace = self._document_cache.get_namespace(document)

        namespace.analyze()

        return self._document_cache.get_diagnostic_modifier(document).modify_diagnostics(namespace.get_diagnostics())

    def analyze_folder(self, sender: Any, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]:
        imports_manager = self._document_cache.get_imports_manager_for_workspace_folder(folder)

        return imports_manager.diagnostics

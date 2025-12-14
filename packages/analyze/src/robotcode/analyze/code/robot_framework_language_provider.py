import glob
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional

from robot.utils import FileReader

from robotcode.analyze.code.diagnostics_context import DiagnosticsContext
from robotcode.core.filewatcher import FileWatcherManagerDummy
from robotcode.core.ignore_spec import DEFAULT_SPEC_RULES, GIT_IGNORE_FILE, ROBOT_IGNORE_FILE, IgnoreSpec, iter_files
from robotcode.core.language import LanguageDefinition, language_id
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, DiagnosticTag
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper
from robotcode.robot.diagnostics.entities import (
    ArgumentDefinition,
    VariableDefinitionType,
)
from robotcode.robot.diagnostics.namespace import DocumentType
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

    SOURCE_NAME = "robotcode.diagnostics"

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
        self.diagnostics_context.diagnostics.folder_analyzers.add(self.analyze_folder)
        self.diagnostics_context.diagnostics.document_analyzers.add(self.analyze_document)
        self.diagnostics_context.diagnostics.document_collectors.add(self.collect_diagnostics)
        # self.diagnostics_context.diagnostics.document_collectors.add(self.collect_unused_keywords)
        # self.diagnostics_context.diagnostics.document_collectors.add(self.collect_unused_variables)

    def _update_python_path(self) -> None:
        root_path = (
            self.diagnostics_context.workspace.root_uri.to_path()
            if self.diagnostics_context.workspace.root_uri is not None
            else None
        )

        for p in self.diagnostics_context.profile.python_path or []:
            pa = Path(str(p))
            if root_path is not None and not pa.is_absolute():
                pa = Path(root_path, pa)

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

    def analyze_folder(self, sender: Any, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]:
        imports_manager = self._document_cache.get_imports_manager_for_workspace_folder(folder)

        return imports_manager.diagnostics

    def analyze_document(self, sender: Any, document: TextDocument) -> Optional[List[Diagnostic]]:
        namespace = self._document_cache.get_namespace(document)

        namespace.analyze()

        return None

    def collect_diagnostics(self, sender: Any, document: TextDocument) -> Optional[List[Diagnostic]]:
        namespace = self._document_cache.get_namespace(document)

        return self._document_cache.get_diagnostic_modifier(document).modify_diagnostics(namespace.get_diagnostics())

    def collect_unused_keywords(self, sender: Any, document: TextDocument) -> Optional[List[Diagnostic]]:
        namespace = self._document_cache.get_namespace(document)

        documents = (
            [document]
            if self._document_cache.get_document_type(document) != DocumentType.RESOURCE
            else self.diagnostics_context.workspace.documents.documents
        )

        result: List[Diagnostic] = []

        for kw in (namespace.get_library_doc()).keywords.values():
            has_reference = False
            for doc in documents:
                refs = self._document_cache.get_namespace(doc).get_keyword_references()
                if refs.get(kw):
                    has_reference = True
                    break
            if not has_reference:
                result.append(
                    Diagnostic(
                        range=kw.name_range,
                        message=f"Keyword '{kw.name}' is not used.",
                        severity=DiagnosticSeverity.WARNING,
                        source=self.SOURCE_NAME,
                        code="KeywordNotUsed",
                        tags=[DiagnosticTag.UNNECESSARY],
                    )
                )

        return result

    def collect_unused_variables(self, sender: Any, document: TextDocument) -> Optional[List[Diagnostic]]:
        result: List[Diagnostic] = []

        namespace = self._document_cache.get_namespace(document)

        for var, locations in (namespace.get_variable_references()).items():
            if var.type in (
                VariableDefinitionType.LIBRARY_ARGUMENT,
                VariableDefinitionType.ENVIRONMENT_VARIABLE,
                VariableDefinitionType.GLOBAL_VARIABLE,
            ):
                continue

            if var.source != namespace.source:
                continue

            has_reference = len(locations) > 0

            if (
                not has_reference
                and var.type
                not in (
                    VariableDefinitionType.ARGUMENT,
                    VariableDefinitionType.LOCAL_VARIABLE,
                )
                and self._document_cache.get_document_type(document) == DocumentType.RESOURCE
            ):
                if self.verbose_callback is not None:
                    self.verbose_callback(f"Checking variable '{var.name}' {var.type} for usage. {document.uri}")
                    self.verbose_callback(
                        f"Searching references in {len(self.diagnostics_context.workspace.documents)} documents."
                    )

                has_reference = any(
                    len(self._document_cache.get_namespace(doc).get_variable_references().get(var, set())) > 0
                    for doc in self.diagnostics_context.workspace.documents.documents
                )

            if not has_reference:
                result.append(
                    Diagnostic(
                        range=var.name_range,
                        message=f"{'Argument' if isinstance(var, ArgumentDefinition) else 'Variable'}"
                        f" '{var.name}' is not used.",
                        severity=DiagnosticSeverity.WARNING,
                        source=self.SOURCE_NAME,
                        code="VariableNotUsed",
                        tags=[DiagnosticTag.UNNECESSARY],
                    )
                )

        return result

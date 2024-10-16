from __future__ import annotations

import ast
import io
import threading
import weakref
from logging import CRITICAL
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from robot.parsing.lexer.tokens import Token
from robotcode.core.documents_manager import DocumentsManager
from robotcode.core.event import event
from robotcode.core.filewatcher import FileWatcherManagerBase
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.workspace import Workspace, WorkspaceFolder
from robotcode.robot.diagnostics.diagnostics_modifier import DiagnosticModifiersConfig, DiagnosticsModifier

from ..config.model import RobotBaseProfile
from ..utils import get_robot_version
from ..utils.stubs import Languages
from .imports_manager import ImportsManager
from .library_doc import LibraryDoc
from .namespace import DocumentType, Namespace
from .workspace_config import (
    AnalysisDiagnosticModifiersConfig,
    AnalysisRobotConfig,
    CacheConfig,
    RobotConfig,
    WorkspaceAnalysisConfig,
)


class UnknownFileTypeError(Exception):
    pass


class _CacheEntry:
    pass


class DocumentsCacheHelper:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        workspace: Workspace,
        documents_manager: DocumentsManager,
        file_watcher_manager: FileWatcherManagerBase,
        robot_profile: Optional[RobotBaseProfile],
        analysis_config: Optional[WorkspaceAnalysisConfig],
    ) -> None:
        self.INITIALIZED_NAMESPACE = _CacheEntry()

        self.workspace = workspace
        self.documents_manager = documents_manager
        self.file_watcher_manager = file_watcher_manager

        self.robot_profile = robot_profile or RobotBaseProfile()
        self.analysis_config = analysis_config or WorkspaceAnalysisConfig()

        self._imports_managers_lock = threading.RLock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None
        self._workspace_languages: weakref.WeakKeyDictionary[WorkspaceFolder, Optional[Languages]] = (
            weakref.WeakKeyDictionary()
        )

    def get_languages_for_document(self, document_or_uri: Union[TextDocument, Uri, str]) -> Optional[Languages]:
        if get_robot_version() < (6, 0):
            return None

        from robot.conf.languages import (
            Languages as RobotLanguages,
        )

        uri: Union[Uri, str]

        if isinstance(document_or_uri, TextDocument):
            uri = document_or_uri.uri
        else:
            uri = document_or_uri

        folder = self.workspace.get_workspace_folder(uri)

        if folder is None:
            return None

        if folder in self._workspace_languages:
            return self._workspace_languages[folder]

        self._logger.debug(lambda: f"Get language config for {uri} in workspace {folder.uri}")
        config = self.workspace.get_configuration(RobotConfig, folder.uri)

        languages = [str(v) for v in self.robot_profile.languages or []]
        languages += config.languages or []

        if not languages:
            self._workspace_languages[folder] = None
            return None

        result = RobotLanguages()
        for lang in languages:
            try:
                result.add_language(lang)
            except ValueError as e:
                ex = e
                self._logger.exception(
                    lambda: f"Language configuration is not valid: {ex}",
                    exc_info=ex,
                    level=CRITICAL,
                )

        self._workspace_languages[folder] = result

        return cast(Languages, RobotLanguages(result.languages))

    def build_languages_from_model(
        self, document: TextDocument, model: ast.AST
    ) -> Tuple[Optional[Languages], Optional[Languages]]:
        if get_robot_version() < (6, 0):
            return (None, None)

        from robot.conf.languages import (
            Languages as RobotLanguages,
        )

        # pyright: ignore[reportMissingImports]
        from robot.parsing.model.blocks import File

        workspace_langs = self.get_languages_for_document(document)

        return (
            cast(
                Languages,
                RobotLanguages(
                    [
                        *(workspace_langs.languages if workspace_langs else []),
                        *(model.languages if isinstance(model, File) else []),
                    ]
                ),
            ),
            workspace_langs,
        )

    def get_document_type(self, document: TextDocument) -> DocumentType:
        return document.get_cache(self.__get_document_type)

    def __get_document_type(self, document: TextDocument) -> DocumentType:
        path = document.uri.to_path()
        suffix = path.suffix.lower()

        if path.name == "__init__.robot":
            return DocumentType.INIT
        if suffix == ".robot":
            return DocumentType.GENERAL
        if suffix == ".resource":
            return DocumentType.RESOURCE

        return DocumentType.UNKNOWN

    def get_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_tokens_data_only)
        return document.get_cache(self.__get_tokens)

    def __get_tokens_data_only(self, document: TextDocument) -> List[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.get_init_tokens(document, True)
        if document_type == DocumentType.GENERAL:
            return self.get_general_tokens(document, True)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_tokens(document, True)

        raise UnknownFileTypeError(str(document.uri))

    def __get_tokens(self, document: TextDocument) -> List[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.get_init_tokens(document)
        if document_type == DocumentType.GENERAL:
            return self.get_general_tokens(document)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_tokens(document)

        raise UnknownFileTypeError(str(document.uri))

    def get_general_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_general_tokens_data_only)
        return document.get_cache(self.__get_general_tokens)

    def __internal_get_tokens(
        self,
        source: Any,
        data_only: bool = False,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_tokens(
                source,
                data_only=data_only,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __internal_get_resource_tokens(
        self,
        source: Any,
        data_only: bool = False,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_resource_tokens(
                source,
                data_only=data_only,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_resource_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __internal_get_init_tokens(
        self,
        source: Any,
        data_only: bool = False,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_init_tokens(
                source,
                data_only=data_only,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_init_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __get_general_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_general_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_tokens_internal(self, document: TextDocument, get: Callable[[str], List[Token]]) -> List[Token]:
        return get(document.text())

    def get_resource_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_resource_tokens_data_only)

        return document.get_cache(self.__get_resource_tokens)

    def __get_resource_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_resource_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def get_init_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_init_tokens_data_only)
        return document.get_cache(self.__get_init_tokens)

    def __get_init_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_init_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def get_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        document_type = self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return self.get_init_model(document, data_only)
        if document_type == DocumentType.GENERAL:
            return self.get_general_model(document, data_only)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_model(document, data_only)

        raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

    def __get_model(
        self,
        document: TextDocument,
        tokens: Iterable[Any],
        document_type: DocumentType,
    ) -> ast.AST:
        from robot.parsing.parser.parser import _get_model

        def get_tokens(source: str, data_only: bool = False, lang: Any = None) -> Iterator[Token]:
            for t in tokens:
                yield t

        if get_robot_version() >= (6, 0):
            model = _get_model(get_tokens, document.uri.to_path(), False, None, None)
        else:
            model = _get_model(get_tokens, document.uri.to_path(), False, None)

        model.source = str(document.uri.to_path())
        model.model_type = document_type

        return cast(ast.AST, model)

    def get_general_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return document.get_cache(
                self.__get_general_model_data_only,
                self.get_general_tokens(document, True),
            )
        return document.get_cache(self.__get_general_model, self.get_general_tokens(document))

    def __get_general_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    def __get_general_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    def get_resource_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return document.get_cache(
                self.__get_resource_model_data_only,
                self.get_resource_tokens(document, True),
            )

        return document.get_cache(self.__get_resource_model, self.get_resource_tokens(document))

    def __get_resource_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.RESOURCE)

    def __get_resource_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.RESOURCE)

    def get_init_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return document.get_cache(
                self.__get_init_model_data_only,
                self.get_init_tokens(document, True),
            )
        return document.get_cache(self.__get_init_model, self.get_init_tokens(document))

    def __get_init_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    def __get_init_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    def get_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_namespace)

    def __get_namespace(self, document: TextDocument) -> Namespace:
        document_type = self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return self.get_init_namespace(document)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_namespace(document)
        if document_type == DocumentType.GENERAL:
            return self.get_general_namespace(document)

        return self.__get_namespace_for_document_type(document, document_type)

    def get_resource_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_resource_namespace)

    def __get_resource_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, DocumentType.RESOURCE)

    def get_init_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_init_namespace)

    def __get_init_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, DocumentType.INIT)

    def get_general_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_general_namespace)

    def __get_general_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, DocumentType.GENERAL)

    @event
    def namespace_initialized(sender, namespace: Namespace) -> None: ...

    @event
    def namespace_invalidated(sender, namespace: Namespace) -> None: ...

    def __invalidate_namespace(self, sender: Namespace) -> None:
        document = sender.document
        if document is not None:
            document.remove_cache_entry(self.__get_general_namespace)
            document.remove_cache_entry(self.__get_init_namespace)
            document.remove_cache_entry(self.__get_resource_namespace)
            document.remove_cache_entry(self.__get_namespace)

            self.namespace_invalidated(self, sender)

    def __namespace_initialized(self, sender: Namespace) -> None:
        if sender.document is not None:
            sender.document.set_data(self.INITIALIZED_NAMESPACE, sender)
            self.namespace_initialized(self, sender)

    def get_initialized_namespace(self, document: TextDocument) -> Namespace:
        result: Optional[Namespace] = document.get_data(self.INITIALIZED_NAMESPACE)
        if result is None:
            self._logger.debug(lambda: f"There is no initialized Namespace: {document.uri if document else None}")
            result = self.get_namespace(document)
        return result

    def get_only_initialized_namespace(self, document: TextDocument) -> Optional[Namespace]:
        return cast(Optional[Namespace], document.get_data(self.INITIALIZED_NAMESPACE))

    def __get_namespace_for_document_type(
        self, document: TextDocument, document_type: Optional[DocumentType]
    ) -> Namespace:
        if document_type is not None and document_type == DocumentType.INIT:
            model = self.get_init_model(document)
        elif document_type is not None and document_type == DocumentType.RESOURCE:
            model = self.get_resource_model(document)
        elif document_type is not None and document_type == DocumentType.GENERAL:
            model = self.get_general_model(document)
        else:
            model = self.get_model(document)

        imports_manager = self.get_imports_manager(document)

        languages, workspace_languages = self.build_languages_from_model(document, model)

        result = Namespace(
            imports_manager,
            model,
            str(document.uri.to_path()),
            document,
            document_type,
            languages,
            workspace_languages,
        )
        result.has_invalidated.add(self.__invalidate_namespace)
        result.has_initialized.add(self.__namespace_initialized)

        return result

    def create_imports_manager(self, root_uri: Uri) -> ImportsManager:
        cache_base_path = self.calc_cache_path(root_uri)

        robot_config = self.workspace.get_configuration(RobotConfig, root_uri)

        cache_config = self.workspace.get_configuration(CacheConfig, root_uri)
        environment = {k: str(v) for k, v in (self.robot_profile.env or {}).items()}
        if robot_config.env:
            environment.update(robot_config.env)

        variables = {
            **{k1: str(v1) for k1, v1 in (self.robot_profile.variables or {}).items()},
            **robot_config.variables,
        }
        variable_files = [
            *(str(k) for k in self.robot_profile.variable_files or []),
            *robot_config.variable_files,
        ]

        analysis_config = self.workspace.get_configuration(AnalysisRobotConfig, root_uri)
        result = ImportsManager(
            self.documents_manager,
            self.file_watcher_manager,
            self,
            root_uri.to_path(),
            variables,
            variable_files,
            environment,
            self.analysis_config.cache.ignored_libraries + cache_config.ignored_libraries,
            self.analysis_config.cache.ignored_variables + cache_config.ignored_variables,
            self.analysis_config.cache.ignore_arguments_for_library + cache_config.ignore_arguments_for_library,
            self.analysis_config.robot.global_library_search_order + analysis_config.global_library_search_order,
            cache_base_path,
        )

        result.libraries_changed.add(self._on_libraries_changed)
        result.resources_changed.add(self._on_resources_changed)
        result.variables_changed.add(self._on_variables_changed)

        return result

    @event
    def libraries_changed(sender, libraries: List[LibraryDoc]) -> None: ...

    @event
    def resources_changed(sender, resources: List[LibraryDoc]) -> None: ...

    @event
    def variables_changed(sender, variables: List[LibraryDoc]) -> None: ...

    def _on_libraries_changed(self, sender: ImportsManager, libraries: List[LibraryDoc]) -> None:
        self.libraries_changed(self, libraries)

    def _on_resources_changed(self, sender: ImportsManager, resources: List[LibraryDoc]) -> None:
        self.resources_changed(self, resources)

    def _on_variables_changed(self, sender: ImportsManager, variables: List[LibraryDoc]) -> None:
        self.variables_changed(self, variables)

    def default_imports_manager(self) -> ImportsManager:
        with self._imports_managers_lock:
            if self._default_imports_manager is None:
                self._default_imports_manager = self.create_imports_manager(
                    self.workspace.root_uri
                    if self.workspace.root_uri is not None
                    else Uri.from_path(Path(".").absolute())
                )

            return self._default_imports_manager

    def get_imports_manager(self, document: TextDocument) -> ImportsManager:
        return self.get_imports_manager_for_uri(document.uri)

    def get_imports_manager_for_uri(self, uri: Uri) -> ImportsManager:
        return self.get_imports_manager_for_workspace_folder(self.workspace.get_workspace_folder(uri))

    def get_imports_manager_for_workspace_folder(self, folder: Optional[WorkspaceFolder]) -> ImportsManager:
        if folder is None:
            if len(self.workspace.workspace_folders) == 1:
                folder = self.workspace.workspace_folders[0]
            else:
                return self.default_imports_manager()

        with self._imports_managers_lock:
            if folder not in self._imports_managers:
                self._imports_managers[folder] = self.create_imports_manager(folder.uri)

            return self._imports_managers[folder]

    def calc_cache_path(self, folder_uri: Uri) -> Path:
        # TODO: cache path should be configurable, save cache in vscode workspace folder or in robotcode cache folder
        return folder_uri.to_path()

    def get_diagnostic_modifier(self, document: TextDocument) -> DiagnosticsModifier:
        return document.get_cache(self.__get_diagnostic_modifier)

    def __get_diagnostic_modifier(self, document: TextDocument) -> DiagnosticsModifier:
        modifiers_config = self.workspace.get_configuration(AnalysisDiagnosticModifiersConfig, document.uri)
        return DiagnosticsModifier(
            self.get_model(document, False),
            DiagnosticModifiersConfig(
                ignore=self.analysis_config.modifiers.ignore + modifiers_config.ignore,
                error=self.analysis_config.modifiers.error + modifiers_config.error,
                warning=self.analysis_config.modifiers.warning + modifiers_config.warning,
                information=self.analysis_config.modifiers.information + modifiers_config.information,
                hint=self.analysis_config.modifiers.hint + modifiers_config.hint,
            ),
        )

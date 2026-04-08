from __future__ import annotations

import ast
import io
import threading
import weakref
from logging import CRITICAL
from pathlib import Path
from typing import (
    Any,
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
from robotcode.robot.diagnostics.diagnostics_modifier import (
    DiagnosticModifiersConfig,
    DiagnosticsModifier,
    text_contains_diagnostic_modifier,
)

from ..config.model import RobotBaseProfile
from ..utils import RF_VERSION
from ..utils.stubs import Languages
from .data_cache import CacheSection
from .imports_manager import ImportsManager, NamespaceMetaData
from .library_doc import LibraryDoc
from .namespace import (
    DocumentType,
    Namespace,
    NamespaceBuilder,
    NamespaceData,
)
from .project_index import ProjectIndex
from .workspace_config import (
    AnalysisDiagnosticModifiersConfig,
    AnalysisRobotConfig,
    CacheConfig,
    ExperimentalConfig,
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
        self._workspace_languages_lock = threading.RLock()
        self._workspace_languages: weakref.WeakKeyDictionary[WorkspaceFolder, Optional[Languages]] = (
            weakref.WeakKeyDictionary()
        )
        self._project_indexes_lock = threading.RLock()
        self._project_indexes: weakref.WeakKeyDictionary[WorkspaceFolder, ProjectIndex] = weakref.WeakKeyDictionary()
        self._default_project_index: Optional[ProjectIndex] = None

    def get_project_index(self, document: TextDocument) -> ProjectIndex:
        return self.get_project_index_for_uri(document.uri)

    def get_project_index_for_uri(self, uri: Uri) -> ProjectIndex:
        return self.get_project_index_for_workspace_folder(self.workspace.get_workspace_folder(uri))

    def get_project_index_for_workspace_folder(self, folder: Optional[WorkspaceFolder]) -> ProjectIndex:
        if folder is None:
            if len(self.workspace.workspace_folders) == 1:
                folder = self.workspace.workspace_folders[0]
            else:
                return self.default_project_index()

        with self._project_indexes_lock:
            if folder not in self._project_indexes:
                self._project_indexes[folder] = ProjectIndex()
            return self._project_indexes[folder]

    def default_project_index(self) -> ProjectIndex:
        with self._project_indexes_lock:
            if self._default_project_index is None:
                self._default_project_index = ProjectIndex()
            return self._default_project_index

    def get_languages_for_document(self, document_or_uri: Union[TextDocument, Uri, str]) -> Optional[Languages]:
        if RF_VERSION < (6, 0):
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

        with self._workspace_languages_lock:
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
        if RF_VERSION < (6, 0):
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

    def get_tokens(self, document: TextDocument) -> List[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.__get_init_tokens(document)
        if document_type == DocumentType.GENERAL:
            return self.__get_general_tokens(document)
        if document_type == DocumentType.RESOURCE:
            return self.__get_resource_tokens(document)

        raise UnknownFileTypeError(str(document.uri))

    def __internal_get_tokens(
        self,
        source: Any,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if RF_VERSION >= (6, 0):
            return robot.api.get_tokens(
                source,
                data_only=False,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_tokens(source, data_only=False, tokenize_variables=tokenize_variables)

    def __internal_get_resource_tokens(
        self,
        source: Any,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if RF_VERSION >= (6, 0):
            return robot.api.get_resource_tokens(
                source,
                data_only=False,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_resource_tokens(source, data_only=False, tokenize_variables=tokenize_variables)

    def __internal_get_init_tokens(
        self,
        source: Any,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if RF_VERSION >= (6, 0):
            return robot.api.get_init_tokens(
                source,
                data_only=False,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_init_tokens(source, data_only=False, tokenize_variables=tokenize_variables)

    def __get_general_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)
        with io.StringIO(document.text()) as content:
            return [e for e in self.__internal_get_tokens(content, lang=lang)]

    def __get_resource_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)
        with io.StringIO(document.text()) as content:
            return [e for e in self.__internal_get_resource_tokens(content, lang=lang)]

    def __get_init_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_languages_for_document(document)
        with io.StringIO(document.text()) as content:
            return [e for e in self.__internal_get_init_tokens(content, lang=lang)]

    def get_model(self, document: TextDocument) -> ast.AST:
        document_type = self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return self.get_init_model(document)
        if document_type == DocumentType.GENERAL:
            return self.get_general_model(document)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_model(document)

        return self.get_general_model(document)

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

        if RF_VERSION >= (6, 0):
            model = _get_model(get_tokens, document.uri.to_path(), False, None, None)
        else:
            model = _get_model(get_tokens, document.uri.to_path(), False, None)

        if not hasattr(model, "source"):
            model.source = str(document.uri.to_path())
        model.model_type = document_type

        return cast(ast.AST, model)

    def get_general_model(self, document: TextDocument) -> ast.AST:
        if document.version is None:
            return self.__get_general_model(document)

        return document.get_cache(self.__get_general_model)

    def __get_general_model(self, document: TextDocument) -> ast.AST:
        return self.__get_model(document, self.__get_general_tokens(document), DocumentType.GENERAL)

    def get_resource_model(self, document: TextDocument) -> ast.AST:
        if document.version is None:
            return self.__get_resource_model(document)

        return document.get_cache(self.__get_resource_model)

    def __get_resource_model(self, document: TextDocument) -> ast.AST:
        return self.__get_model(document, self.__get_resource_tokens(document), DocumentType.RESOURCE)

    def get_init_model(self, document: TextDocument) -> ast.AST:
        if document.version is None:
            return self.__get_init_model(document)

        return document.get_cache(self.__get_init_model)

    def __get_init_model(self, document: TextDocument) -> ast.AST:
        return self.__get_model(document, self.__get_init_tokens(document), DocumentType.INIT)

    def get_namespace(self, document: TextDocument) -> Namespace:
        document_type = self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return self.get_init_namespace(document)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_namespace(document)

        return self.get_general_namespace(document)

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

    def _invalidate_namespace(self, sender: Namespace) -> None:
        if sender.document is not None:
            self.get_project_index(sender.document).remove_file(sender.source)

        document = sender.document
        if document is not None:
            document.remove_cache_entry(self.__get_general_namespace)
            document.remove_cache_entry(self.__get_init_namespace)
            document.remove_cache_entry(self.__get_resource_namespace)

            self.namespace_invalidated(self, sender)

    def __namespace_initialized(self, namespace: Namespace) -> None:
        if namespace.document is not None:
            namespace.document.set_data(self.INITIALIZED_NAMESPACE, namespace)
            self.namespace_initialized(self, namespace)

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
        source = str(document.uri.to_path())
        imports_manager = self.get_imports_manager(document)

        # --- Try disk cache (cold-start acceleration) ---
        cache_namespaces = self.analysis_config.cache.cache_namespaces
        if cache_namespaces and document.version is None:
            result = self._try_load_cached_namespace(source, document, document_type, imports_manager)
            if result is not None:
                return result

        # --- Cache miss: full build ---
        if document_type is not None and document_type == DocumentType.INIT:
            model = self.get_init_model(document)
        elif document_type is not None and document_type == DocumentType.RESOURCE:
            model = self.get_resource_model(document)
        elif document_type is not None and document_type == DocumentType.GENERAL:
            model = self.get_general_model(document)
        else:
            model = self.get_model(document)

        languages, workspace_languages = self.build_languages_from_model(document, model)
        experimental_config = self.workspace.get_configuration(ExperimentalConfig, document.uri)

        builder = NamespaceBuilder(
            imports_manager,
            model,
            source,
            document,
            document_type,
            languages,
            workspace_languages,
        )
        builder.set_semantic_model_enabled(self.analysis_config.semantic_model or experimental_config.semantic_model)

        result = builder.build()

        # Save to disk cache
        if cache_namespaces:
            self._save_namespace_to_cache(source, result, imports_manager)

        # Update the folder-scoped reference index
        self.get_project_index(document).update_file(result.source, result)

        # When the namespace detects dependency changes, evict the
        # document cache entry so it gets rebuilt on next access.
        result.invalidated.add(self._invalidate_namespace)

        # Mark as initialized for consumers that need early access
        self.__namespace_initialized(result)

        return result

    def _try_load_cached_namespace(
        self,
        source: str,
        document: TextDocument,
        document_type: Optional[DocumentType],
        imports_manager: ImportsManager,
    ) -> Optional[Namespace]:
        """Attempt to load a Namespace from the disk cache.

        Returns None on cache miss or validation failure.
        """
        data_cache = imports_manager.data_cache

        # Check source file exists before attempting cache lookup
        if not Path(source).exists():
            return None

        try:
            entry = data_cache.read_entry(CacheSection.NAMESPACE, source, NamespaceMetaData, NamespaceData)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            ex = e
            self._logger.debug(
                lambda: f"Failed to read namespace cache for {source}: {ex}",
                context_name="import",
            )
            return None

        if entry is None or entry.meta is None:
            self._logger.debug(
                lambda: f"Cache miss for {source}: no cached entry found",
                context_name="cache",
            )
            return None

        if not imports_manager.validate_namespace_meta(entry.meta):
            self._logger.debug(
                lambda: f"Cache miss for {source}: cached entry is stale, re-analyzing",
                context_name="cache",
            )
            return None

        # Meta is valid — load the full NamespaceData (lazy deserialization)
        try:
            namespace_data = entry.data
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            ex = e
            self._logger.debug(
                lambda: f"Failed to read namespace data for {source}: {ex}",
                context_name="import",
            )
            return None

        # Reconstruct the Namespace from cached data.
        # Try to get the file's ResourceDoc from the RESOURCE disk cache first
        # (avoids parsing the model if already cached). Falls back to parsing.
        try:
            library_doc = imports_manager.get_resource_doc_from_document(document)
            result = Namespace.from_data(namespace_data, imports_manager, library_doc, document)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            ex = e
            self._logger.debug(
                lambda: f"Failed to reconstruct namespace from cache for {source}: {ex}",
                context_name="import",
            )
            return None

        self._logger.debug(
            lambda: f"Loaded namespace from disk cache for {source}",
            context_name="import",
        )

        # Update the folder-scoped reference index
        self.get_project_index(document).update_file(result.source, result)

        result.invalidated.add(self._invalidate_namespace)
        self.__namespace_initialized(result)

        return result

    def _save_namespace_to_cache(
        self,
        source: str,
        namespace: Namespace,
        imports_manager: ImportsManager,
    ) -> None:
        """Save a Namespace to the disk cache."""
        try:
            meta = imports_manager.build_namespace_meta(source, namespace)
            data = namespace.to_data()

            data_cache = imports_manager.data_cache
            data_cache.save_entry(CacheSection.NAMESPACE, source, meta, data)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            ex = e
            self._logger.debug(
                lambda: f"Failed to save namespace cache for {source}: {ex}",
                context_name="import",
            )

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
            load_library_timeout=(
                analysis_config.load_library_timeout
                if analysis_config.load_library_timeout is not None
                else self.analysis_config.robot.load_library_timeout
            ),
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
        from .data_cache import resolve_cache_base_path

        return resolve_cache_base_path(folder_uri.to_path())

    def get_diagnostic_modifier(self, document: TextDocument) -> DiagnosticsModifier:
        return document.get_cache(self.__get_diagnostic_modifier)

    def __get_diagnostic_modifier(self, document: TextDocument) -> DiagnosticsModifier:
        modifiers_config = self.workspace.get_configuration(AnalysisDiagnosticModifiersConfig, document.uri)

        has_modifier = text_contains_diagnostic_modifier(document.text())

        if has_modifier:
            self._logger.debug(
                lambda: f"Document {document.uri} contains diagnostic modifier comment, analyzing model for it"
            )

        return DiagnosticsModifier(
            self.get_model(document) if has_modifier else None,
            DiagnosticModifiersConfig(
                ignore=self.analysis_config.modifiers.ignore + modifiers_config.ignore,
                error=self.analysis_config.modifiers.error + modifiers_config.error,
                warning=self.analysis_config.modifiers.warning + modifiers_config.warning,
                information=self.analysis_config.modifiers.information + modifiers_config.information,
                hint=self.analysis_config.modifiers.hint + modifiers_config.hint,
            ),
        )

from __future__ import annotations

import ast
import hashlib
import io
import sys
import threading
import weakref
from logging import CRITICAL
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
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
from .data_cache import CacheSection
from .entities import VariableDefinition
from .imports_manager import ImportsManager
from .library_doc import KeywordDoc, LibraryDoc
from .namespace import DocumentType, Namespace, NamespaceCacheData, NamespaceMetaData
from .workspace_config import (
    AnalysisDiagnosticModifiersConfig,
    AnalysisRobotConfig,
    CacheConfig,
    RobotConfig,
    WorkspaceAnalysisConfig,
)

# Interval for cleaning up stale entries in dependency maps
_DEPENDENCY_CLEANUP_INTERVAL = 100


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
        robot_profile: RobotBaseProfile | None,
        analysis_config: WorkspaceAnalysisConfig | None,
    ) -> None:
        self.INITIALIZED_NAMESPACE = _CacheEntry()

        self.workspace = workspace
        self.documents_manager = documents_manager
        self.file_watcher_manager = file_watcher_manager

        self.robot_profile = robot_profile or RobotBaseProfile()
        self.analysis_config = analysis_config or WorkspaceAnalysisConfig()

        # Lock ordering (to prevent deadlocks when acquiring multiple locks):
        # 1. _imports_managers_lock
        # 2. _importers_lock
        # 3. _library_users_lock
        # 4. _variables_users_lock
        # Always acquire in this order if multiple locks are needed in the same operation.

        self._imports_managers_lock = threading.RLock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: ImportsManager | None = None
        self._workspace_languages: weakref.WeakKeyDictionary[WorkspaceFolder, Languages | None] = (
            weakref.WeakKeyDictionary()
        )

        # Reverse dependency map: source path -> set of documents that import it
        self._importers_lock = threading.RLock()
        self._importers: dict[str, weakref.WeakSet[TextDocument]] = {}

        # Reverse dependency maps for libraries and variables (by source path for stable lookup)
        # Using source path instead of id() because Python can reuse object IDs after GC
        self._library_users_lock = threading.RLock()
        self._library_users: dict[str, weakref.WeakSet[TextDocument]] = {}

        self._variables_users_lock = threading.RLock()
        self._variables_users: dict[str, weakref.WeakSet[TextDocument]] = {}

        # Reference tracking for O(1) lookup of keyword/variable usages
        # Uses (source, name) tuples as keys for stability across cache invalidation
        self._ref_tracking_lock = threading.RLock()
        self._keyword_ref_users: dict[tuple[str, str], weakref.WeakSet[TextDocument]] = {}
        self._variable_ref_users: dict[tuple[str, str], weakref.WeakSet[TextDocument]] = {}
        self._doc_keyword_refs: weakref.WeakKeyDictionary[
            TextDocument, set[tuple[str, str]]
        ] = weakref.WeakKeyDictionary()
        self._doc_variable_refs: weakref.WeakKeyDictionary[
            TextDocument, set[tuple[str, str]]
        ] = weakref.WeakKeyDictionary()

        # Counter for periodic cleanup of stale dependency map entries
        self._track_count = 0

    def get_languages_for_document(self, document_or_uri: TextDocument | Uri | str) -> Languages | None:
        if get_robot_version() < (6, 0):
            return None

        from robot.conf.languages import (
            Languages as RobotLanguages,
        )

        uri: Uri | str

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
    ) -> tuple[Languages | None, Languages | None]:
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

    def get_tokens(self, document: TextDocument, data_only: bool = False) -> list[Token]:
        if data_only:
            return self.__get_tokens_data_only(document)
        return self.__get_tokens(document)

    def __get_tokens_data_only(self, document: TextDocument) -> list[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.get_init_tokens(document, True)
        if document_type == DocumentType.GENERAL:
            return self.get_general_tokens(document, True)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_tokens(document, True)

        raise UnknownFileTypeError(str(document.uri))

    def __get_tokens(self, document: TextDocument) -> list[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.get_init_tokens(document)
        if document_type == DocumentType.GENERAL:
            return self.get_general_tokens(document)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_tokens(document)

        raise UnknownFileTypeError(str(document.uri))

    def get_general_tokens(self, document: TextDocument, data_only: bool = False) -> list[Token]:
        if document.version is None:
            if data_only:
                return self.__get_general_tokens_data_only(document)

            return self.__get_general_tokens(document)

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

    def __get_general_tokens_data_only(self, document: TextDocument) -> list[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> list[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_general_tokens(self, document: TextDocument) -> list[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> list[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_tokens_internal(self, document: TextDocument, get: Callable[[str], list[Token]]) -> list[Token]:
        return get(document.text())

    def get_resource_tokens(self, document: TextDocument, data_only: bool = False) -> list[Token]:
        if document.version is None:
            if data_only:
                return self.__get_resource_tokens_data_only(document)

            return self.__get_resource_tokens(document)

        if data_only:
            return document.get_cache(self.__get_resource_tokens_data_only)

        return document.get_cache(self.__get_resource_tokens)

    def __get_resource_tokens_data_only(self, document: TextDocument) -> list[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> list[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_resource_tokens(self, document: TextDocument) -> list[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> list[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def get_init_tokens(self, document: TextDocument, data_only: bool = False) -> list[Token]:
        if document.version is None:
            if data_only:
                return self.__get_init_tokens_data_only(document)

            return self.__get_init_tokens(document)

        if data_only:
            return document.get_cache(self.__get_init_tokens_data_only)
        return document.get_cache(self.__get_init_tokens)

    def __get_init_tokens_data_only(self, document: TextDocument) -> list[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> list[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_init_tokens(self, document: TextDocument) -> list[Token]:
        lang = self.get_languages_for_document(document)

        def get(text: str) -> list[Token]:
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

        return self.get_general_model(document, data_only)

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
        if document.version is None:
            if data_only:
                return self.__get_general_model_data_only(document, self.get_general_tokens(document, True))

            return self.__get_general_model(document, self.get_general_tokens(document))

        if data_only:
            return document.get_cache(self.__get_general_model_data_only, self.get_general_tokens(document, True))

        return document.get_cache(self.__get_general_model, self.get_general_tokens(document))

    def __get_general_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    def __get_general_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    def get_resource_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if document.version is None:
            if data_only:
                return self.__get_resource_model_data_only(document, self.get_resource_tokens(document, True))

            return self.__get_resource_model(document, self.get_resource_tokens(document))

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
        if document.version is None:
            if data_only:
                return self.__get_init_model_data_only(document, self.get_init_tokens(document, True))

            return self.__get_init_model(document, self.get_init_tokens(document))

        if data_only:
            return document.get_cache(self.__get_init_model_data_only, self.get_init_tokens(document, True))

        return document.get_cache(self.__get_init_model, self.get_init_tokens(document))

    def __get_init_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    def __get_init_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

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

    def __invalidate_namespace(self, sender: Namespace) -> None:
        document = sender.document
        if document is not None:
            document.remove_cache_entry(self.__get_general_namespace)
            document.remove_cache_entry(self.__get_init_namespace)
            document.remove_cache_entry(self.__get_resource_namespace)

            self.namespace_invalidated(self, sender)

    def __namespace_initialized(self, sender: Namespace) -> None:
        if sender.document is not None:
            sender.document.set_data(self.INITIALIZED_NAMESPACE, sender)

            # Track reverse dependencies: record that this document imports its resources
            self._track_imports(sender.document, sender)

            # Save to disk cache for faster restart (initial save without analysis data)
            imports_manager = self.get_imports_manager(sender.document)
            self._save_namespace_to_cache(sender, imports_manager)

            self.namespace_initialized(self, sender)

    def __namespace_analysed(self, sender: Namespace) -> None:
        """Re-save namespace to cache after analysis to include diagnostics and analysis results."""
        if sender.document is not None:
            self._track_references(sender.document, sender)

            imports_manager = self.get_imports_manager(sender.document)
            self._save_namespace_to_cache(sender, imports_manager)

    def _track_imports(self, document: TextDocument, namespace: Namespace) -> None:
        """Update the reverse dependency map for a namespace's imports."""
        with self._importers_lock:
            # Track resource imports
            for source in namespace.get_resources().keys():
                if source not in self._importers:
                    self._importers[source] = weakref.WeakSet()
                self._importers[source].add(document)

        # Track library users (by source path for stable lookup)
        with self._library_users_lock:
            for entry in namespace.get_libraries().values():
                lib_key = entry.library_doc.source or entry.library_doc.name
                if lib_key and lib_key not in self._library_users:
                    self._library_users[lib_key] = weakref.WeakSet()
                if lib_key:
                    self._library_users[lib_key].add(document)

        # Track variables users (by source path for stable lookup)
        with self._variables_users_lock:
            for entry in namespace.get_variables_imports().values():
                var_key = entry.library_doc.source or entry.library_doc.name
                if var_key and var_key not in self._variables_users:
                    self._variables_users[var_key] = weakref.WeakSet()
                if var_key:
                    self._variables_users[var_key].add(document)

        # Periodically cleanup stale entries
        self._track_count += 1
        if self._track_count >= _DEPENDENCY_CLEANUP_INTERVAL:
            self._track_count = 0
            self._cleanup_stale_dependency_maps()

    def get_importers(self, source: str) -> list[TextDocument]:
        """Get all documents that import a given source file (O(1) lookup)."""
        with self._importers_lock:
            if source in self._importers:
                return list(self._importers[source])
            return []

    def clear_importers(self, source: str) -> None:
        """Clear the importers set for a source (called when source is modified)."""
        with self._importers_lock:
            if source in self._importers:
                del self._importers[source]

    def get_library_users(self, library_doc: LibraryDoc) -> list[TextDocument]:
        """Get all documents that use a given library (O(1) lookup by source path)."""
        with self._library_users_lock:
            lib_key = library_doc.source or library_doc.name
            if lib_key and lib_key in self._library_users:
                return list(self._library_users[lib_key])
            return []

    def get_variables_users(self, variables_doc: LibraryDoc) -> list[TextDocument]:
        """Get all documents that use a given variables file (O(1) lookup by source path)."""
        with self._variables_users_lock:
            var_key = variables_doc.source or variables_doc.name
            if var_key and var_key in self._variables_users:
                return list(self._variables_users[var_key])
            return []

    def get_keyword_ref_users(self, kw_doc: KeywordDoc) -> list[TextDocument]:
        """Get documents that reference a keyword."""
        with self._ref_tracking_lock:
            key = (kw_doc.source or "", kw_doc.name)
            if key in self._keyword_ref_users:
                return list(self._keyword_ref_users[key])
            return []

    def get_variable_ref_users(self, var_def: VariableDefinition) -> list[TextDocument]:
        """Get documents that reference a variable."""
        with self._ref_tracking_lock:
            key = (var_def.source or "", var_def.name)
            if key in self._variable_ref_users:
                return list(self._variable_ref_users[key])
            return []

    def _cleanup_stale_dependency_maps(self) -> None:
        """Remove entries with empty WeakSets from dependency maps.

        Called periodically to prevent memory accumulation from stale entries
        where the object IDs have been reused after garbage collection.
        """
        with self._importers_lock:
            stale_importer_keys = [k for k, v in self._importers.items() if len(v) == 0]
            for key in stale_importer_keys:
                del self._importers[key]

        with self._library_users_lock:
            stale_lib_keys = [k for k, v in self._library_users.items() if len(v) == 0]
            for lib_key in stale_lib_keys:
                del self._library_users[lib_key]

        with self._variables_users_lock:
            stale_var_keys = [k for k, v in self._variables_users.items() if len(v) == 0]
            for var_key in stale_var_keys:
                del self._variables_users[var_key]

        with self._ref_tracking_lock:
            stale_kw_ref_keys = [k for k, v in self._keyword_ref_users.items() if len(v) == 0]
            for kw_ref_key in stale_kw_ref_keys:
                del self._keyword_ref_users[kw_ref_key]

            stale_var_ref_keys = [k for k, v in self._variable_ref_users.items() if len(v) == 0]
            for var_ref_key in stale_var_ref_keys:
                del self._variable_ref_users[var_ref_key]

    def _track_references(self, document: TextDocument, namespace: Namespace) -> None:
        """Track keyword/variable references.

        Uses diff-based updates: compares current references against previous
        to handle documents that stop referencing items after edits.
        """
        with self._ref_tracking_lock:
            self._update_keyword_refs(document, namespace)
            self._update_variable_refs(document, namespace)

    def _update_keyword_refs(self, document: TextDocument, namespace: Namespace) -> None:
        """Update reverse index for keyword references."""
        keyword_refs = namespace.get_keyword_references()
        new_keys = {(kw.source or "", kw.name) for kw in keyword_refs}
        old_keys = self._doc_keyword_refs.get(document, set())

        for key in old_keys - new_keys:
            if key in self._keyword_ref_users:
                self._keyword_ref_users[key].discard(document)

        for key in new_keys - old_keys:
            if key not in self._keyword_ref_users:
                self._keyword_ref_users[key] = weakref.WeakSet()
            self._keyword_ref_users[key].add(document)

        self._doc_keyword_refs[document] = new_keys

    def _update_variable_refs(self, document: TextDocument, namespace: Namespace) -> None:
        """Update reverse index for variable references."""
        variable_refs = namespace.get_variable_references()
        new_keys = {(var.source or "", var.name) for var in variable_refs}
        old_keys = self._doc_variable_refs.get(document, set())

        for key in old_keys - new_keys:
            if key in self._variable_ref_users:
                self._variable_ref_users[key].discard(document)

        for key in new_keys - old_keys:
            if key not in self._variable_ref_users:
                self._variable_ref_users[key] = weakref.WeakSet()
            self._variable_ref_users[key].add(document)

        self._doc_variable_refs[document] = new_keys

    def get_initialized_namespace(self, document: TextDocument) -> Namespace:
        result: Namespace | None = document.get_data(self.INITIALIZED_NAMESPACE)
        if result is None:
            self._logger.debug(lambda: f"There is no initialized Namespace: {document.uri if document else None}")
            result = self.get_namespace(document)
        return result

    def get_only_initialized_namespace(self, document: TextDocument) -> Namespace | None:
        return cast(Namespace | None, document.get_data(self.INITIALIZED_NAMESPACE))

    def _try_load_namespace_from_cache(
        self,
        document: TextDocument,
        model: ast.AST,
        imports_manager: ImportsManager,
        document_type: DocumentType | None,
        languages: Languages | None,
        workspace_languages: Languages | None,
    ) -> Namespace | None:
        """Attempt to load namespace from disk cache."""
        source = str(document.uri.to_path())
        source_path = Path(source)

        if not source_path.exists():
            return None

        try:
            source_stat = source_path.stat()
            current_mtime = source_stat.st_mtime_ns
            current_size = source_stat.st_size
        except OSError:
            return None

        # Build cache filename using SHA256 for collision resistance
        normalized = str(source_path.resolve())
        cache_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        cache_file = cache_key + ".cache"

        # Check if cache file exists
        if not imports_manager.data_cache.cache_data_exists(CacheSection.NAMESPACE, cache_file):
            return None

        # Load cache data (single file contains (meta, spec) tuple)
        try:
            saved_meta, cache_data = imports_manager.data_cache.read_cache_data(
                CacheSection.NAMESPACE, cache_file, tuple
            )
        except Exception:
            self._logger.debug(lambda: f"Failed to read namespace cache for {source}", context_name="import")
            return None

        # Type check the loaded data
        if not isinstance(saved_meta, NamespaceMetaData) or not isinstance(cache_data, NamespaceCacheData):
            self._logger.debug(lambda: f"Namespace cache type mismatch for {source}", context_name="import")
            return None

        # Validate source file mtime
        if saved_meta.mtime != current_mtime:
            self._logger.debug(lambda: f"Namespace cache mtime mismatch for {source}", context_name="import")
            return None

        # Fast path: if mtime AND size both match, skip expensive content hash computation
        if saved_meta.file_size != current_size:
            # Size changed - need content hash to validate
            try:
                _, current_hash = Namespace._compute_content_hash(source_path)
            except OSError:
                return None

            if saved_meta.content_hash != current_hash:
                self._logger.debug(
                    lambda: f"Namespace cache content hash mismatch for {source}", context_name="import"
                )
                return None

        # Validate environment identity (detects venv changes, PYTHONPATH changes, etc.)
        if saved_meta.python_executable != sys.executable:
            self._logger.debug(
                lambda: f"Namespace cache Python executable mismatch for {source}", context_name="import"
            )
            return None

        current_sys_path_hash = hashlib.sha256("\n".join(sys.path).encode("utf-8")).hexdigest()[:16]
        if saved_meta.sys_path_hash != current_sys_path_hash:
            self._logger.debug(lambda: f"Namespace cache sys.path hash mismatch for {source}", context_name="import")
            return None

        # Validate all library source mtimes
        for lib_source, lib_mtime in saved_meta.library_sources_mtimes:
            lib_path = Path(lib_source)
            try:
                if not lib_path.exists() or lib_path.stat().st_mtime_ns != lib_mtime:
                    self._logger.debug(
                        lambda: f"Namespace cache library mtime mismatch for {lib_source}", context_name="import"
                    )
                    return None
            except OSError:
                return None

        # Validate all resource source mtimes
        for res_source, res_mtime in saved_meta.resource_sources_mtimes:
            res_path = Path(res_source)
            try:
                if not res_path.exists() or res_path.stat().st_mtime_ns != res_mtime:
                    self._logger.debug(
                        lambda: f"Namespace cache resource mtime mismatch for {res_source}", context_name="import"
                    )
                    return None
            except OSError:
                return None

        # Validate all variables source mtimes
        for var_source, var_mtime in saved_meta.variables_sources_mtimes:
            var_path = Path(var_source)
            try:
                if not var_path.exists() or var_path.stat().st_mtime_ns != var_mtime:
                    self._logger.debug(
                        lambda: f"Namespace cache variables mtime mismatch for {var_source}", context_name="import"
                    )
                    return None
            except OSError:
                return None

        # Create namespace from cache data
        result = Namespace.from_cache_data(
            cache_data=cache_data,
            imports_manager=imports_manager,
            model=model,
            source=source,
            document=document,
            document_type=document_type,
            languages=languages,
            workspace_languages=workspace_languages,
        )

        if result is not None:
            self._logger.debug(lambda: f"Loaded namespace from cache for {source}", context_name="import")

        return result

    def _save_namespace_to_cache(self, namespace: Namespace, imports_manager: ImportsManager) -> None:
        """Save initialized namespace to disk cache.

        Uses single-file format with atomic writes for consistency.
        The cache file contains a (meta, spec) tuple.
        """
        if not namespace._initialized:
            return

        meta = namespace.get_cache_metadata()
        if meta is None:
            return

        cache_data = namespace.to_cache_data()

        # Build cache filename using SHA256 for collision resistance
        source_path = Path(namespace.source)
        normalized = str(source_path.resolve())
        cache_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        cache_file = cache_key + ".cache"

        # Save as single tuple (meta, spec) - atomic and consistent
        try:
            imports_manager.data_cache.save_cache_data(
                CacheSection.NAMESPACE, cache_file, (meta, cache_data)
            )
            self._logger.debug(lambda: f"Saved namespace to cache for {namespace.source}", context_name="import")
        except OSError:
            self._logger.debug(lambda: f"Failed to save namespace cache for {namespace.source}", context_name="import")

    def __get_namespace_for_document_type(
        self, document: TextDocument, document_type: DocumentType | None
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

        # Try loading from disk cache first
        cached = self._try_load_namespace_from_cache(
            document, model, imports_manager, document_type, languages, workspace_languages
        )
        if cached is not None:
            cached.has_invalidated.add(self.__invalidate_namespace)
            cached.has_initialized.add(self.__namespace_initialized)
            cached.has_analysed.add(self.__namespace_analysed)
            # Mark as initialized in document data and track imports
            document.set_data(self.INITIALIZED_NAMESPACE, cached)
            self._track_imports(document, cached)
            return cached

        # Cache miss - create new namespace
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
        result.has_analysed.add(self.__namespace_analysed)

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
    def libraries_changed(sender, libraries: list[LibraryDoc]) -> None: ...

    @event
    def resources_changed(sender, resources: list[LibraryDoc]) -> None: ...

    @event
    def variables_changed(sender, variables: list[LibraryDoc]) -> None: ...

    def _on_libraries_changed(self, sender: ImportsManager, libraries: list[LibraryDoc]) -> None:
        self.libraries_changed(self, libraries)

    def _on_resources_changed(self, sender: ImportsManager, resources: list[LibraryDoc]) -> None:
        self.resources_changed(self, resources)

    def _on_variables_changed(self, sender: ImportsManager, variables: list[LibraryDoc]) -> None:
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

    def get_imports_manager_for_workspace_folder(self, folder: WorkspaceFolder | None) -> ImportsManager:
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

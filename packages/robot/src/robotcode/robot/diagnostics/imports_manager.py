import ast
import multiprocessing as mp
import os
import shutil
import sys
import threading
import weakref
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    final,
)

from robot.errors import RobotError
from robot.libraries import STDLIBS
from robot.utils.text import split_args_from_name_or_path
from robotcode.core.concurrent import RLock, run_as_task
from robotcode.core.documents_manager import DocumentsManager
from robotcode.core.event import event
from robotcode.core.filewatcher import FileWatcherEntry, FileWatcherManagerBase, FileWatcherManagerDummy
from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    DocumentUri,
    FileChangeType,
    FileEvent,
    Location,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.caching import SimpleLRUCache
from robotcode.core.utils.glob_path import Pattern
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.path import normalized_path, path_is_relative_to

from ..__version__ import __version__
from ..utils import get_robot_version, get_robot_version_str
from ..utils.robot_path import find_file_ex
from ..utils.variables import contains_variable
from .data_cache import CacheSection
from .data_cache import SqliteDataCache as DefaultDataCache
from .entities import (
    CommandLineVariableDefinition,
    VariableDefinition,
)
from .library_doc import (
    ROBOT_LIBRARY_PACKAGE,
    CompleteResult,
    LibraryDoc,
    ModuleSpec,
    ResourceDoc,
    VariablesDoc,
    complete_library_import,
    complete_resource_import,
    complete_variables_import,
    find_file,
    find_library,
    find_variables,
    get_library_doc,
    get_model_doc,
    get_module_spec,
    get_variables_doc,
    is_library_by_path,
    is_variables_by_path,
    replace_variables_scalar,
    resolve_args,
    resolve_variable,
)

if TYPE_CHECKING:
    from .document_cache_helper import DocumentsCacheHelper
    from .namespace import Namespace


RESOURCE_EXTENSIONS = (
    {".resource", ".robot", ".txt", ".tsv", ".rst", ".rest", ".json", ".rsrc"}
    if get_robot_version() >= (6, 1)
    else {".resource", ".robot", ".txt", ".tsv", ".rst", ".rest"}
)
REST_EXTENSIONS = (".rst", ".rest")


DEFAULT_LOAD_LIBRARY_TIMEOUT: int = 10
ENV_LOAD_LIBRARY_TIMEOUT_VAR = "ROBOTCODE_LOAD_LIBRARY_TIMEOUT"
COMPLETE_LIBRARY_IMPORT_TIMEOUT = COMPLETE_RESOURCE_IMPORT_TIMEOUT = COMPLETE_VARIABLES_IMPORT_TIMEOUT = 5


@dataclass(frozen=True, slots=True)
class _LibrariesEntryKey:
    name: str
    args: Tuple[Any, ...]


class _ImportEntry(ABC):
    def __init__(self, parent: "ImportsManager") -> None:
        self.parent = parent
        self.references: weakref.WeakSet[Any] = weakref.WeakSet()
        self.file_watchers: List[FileWatcherEntry] = []
        self._lock = RLock(default_timeout=120, name="ImportEntryLock")

    def _remove_file_watcher(self) -> None:
        if self.file_watchers:
            for watcher in self.file_watchers:
                try:
                    self.parent.file_watcher_manager.remove_file_watcher_entry(watcher)
                except RuntimeError:
                    pass
            self.file_watchers.clear()

    @abstractmethod
    def check_file_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]: ...

    @final
    def invalidate(self) -> None:
        with self._lock:
            self._invalidate()

    @abstractmethod
    def _invalidate(self) -> None: ...

    @abstractmethod
    def _update(self) -> None: ...

    @abstractmethod
    def is_valid(self) -> bool: ...


class _LibrariesEntry(_ImportEntry):
    def __init__(
        self,
        parent: "ImportsManager",
        name: str,
        args: Tuple[Any, ...],
        working_dir: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
        ignore_reference: bool = False,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self.args = args
        self.working_dir = working_dir
        self.base_dir = base_dir
        self.variables = variables
        self._lib_doc: Optional[LibraryDoc] = None
        self._meta: Optional[LibraryMetaData] = None
        self.ignore_reference = ignore_reference

    def __repr__(self) -> str:
        return (
            f"{type(self).__qualname__}(name={self.name!r}, "
            f"args={self.args!r}, file_watchers={self.file_watchers!r}, id={id(self)!r}"
        )

    def check_file_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]:
        with self._lock:
            if self._lib_doc is None:
                return None

            for change in changes:
                uri = Uri(change.uri)
                if uri.scheme != "file":
                    continue

                path = uri.to_path()
                if self._lib_doc is not None and (
                    (
                        self._lib_doc.module_spec is not None
                        and self._lib_doc.module_spec.submodule_search_locations is not None
                        and any(
                            path_is_relative_to(path, normalized_path(Path(e)))
                            for e in self._lib_doc.module_spec.submodule_search_locations
                        )
                    )
                    or (
                        self._lib_doc.module_spec is not None
                        and self._lib_doc.module_spec.origin is not None
                        and path_is_relative_to(path, Path(self._lib_doc.module_spec.origin).parent)
                    )
                    or (self._lib_doc.source and path_is_relative_to(path, Path(self._lib_doc.source).parent))
                    or (
                        self._lib_doc.module_spec is None
                        and not self._lib_doc.source
                        and self._lib_doc.python_path
                        and any(path_is_relative_to(path, normalized_path(Path(e))) for e in self._lib_doc.python_path)
                    )
                ):
                    self._invalidate()

                    return change.type

            return None

    @property
    def meta(self) -> Optional["LibraryMetaData"]:
        return self._meta

    def _update(self) -> None:
        self._lib_doc, self._meta = self.parent._get_library_libdoc(
            self.name,
            self.args,
            self.working_dir,
            self.base_dir,
            self.variables,
        )

        source_or_origin = (
            self._lib_doc.source
            if self._lib_doc.source is not None
            else self._lib_doc.module_spec.origin
            if self._lib_doc.module_spec is not None
            else None
        )

        # we are a module, so add the module path into file watchers
        if self._lib_doc.module_spec is not None and self._lib_doc.module_spec.submodule_search_locations is not None:
            self.file_watchers.append(
                self.parent.file_watcher_manager.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [
                        str(normalized_path(Path(location)).joinpath("**"))
                        for location in self._lib_doc.module_spec.submodule_search_locations
                    ],
                )
            )

            if source_or_origin is not None and Path(source_or_origin).parent in [
                normalized_path(Path(loc)) for loc in self._lib_doc.module_spec.submodule_search_locations
            ]:
                return

        # we are a file, so put the parent path to filewatchers
        if source_or_origin is not None:
            self.file_watchers.append(
                self.parent.file_watcher_manager.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(Path(source_or_origin).parent.joinpath("**"))],
                )
            )

            return

        # we are not found, so put the pythonpath to filewatchers
        if self._lib_doc.python_path is not None:
            self.file_watchers.append(
                self.parent.file_watcher_manager.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(Path(s).joinpath("**")) for s in self._lib_doc.python_path],
                )
            )

    def _invalidate(self) -> None:
        if self._lib_doc is None and len(self.file_watchers) == 0:
            return

        self._remove_file_watcher()
        self._lib_doc = None
        self._meta = None

    def is_valid(self) -> bool:
        with self._lock:
            return self._lib_doc is not None

    def get_libdoc(self) -> LibraryDoc:
        with self._lock:
            if self._lib_doc is None:
                self._update()

            assert self._lib_doc is not None

            return self._lib_doc


@dataclass(frozen=True, slots=True)
class _ResourcesEntryKey:
    name: str


class _ResourcesEntry(_ImportEntry):
    def __init__(
        self,
        name: str,
        parent: "ImportsManager",
        source_path: Path,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self.source_path = source_path
        self._document: Optional[TextDocument] = None
        self._lib_doc: Optional[ResourceDoc] = None
        self._meta: Optional[RobotFileMeta] = None

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(name={self.name!r}, file_watchers={self.file_watchers!r}, id={id(self)!r}"

    def check_file_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]:
        with self._lock:
            if self._document is None:
                return None

            for change in changes:
                uri = Uri(change.uri)
                if uri.scheme != "file":
                    continue

                path = uri.to_path()
                try:
                    is_same = path.samefile(self._document.uri.to_path())
                except OSError:
                    is_same = not self._document.uri.to_path().exists()
                if is_same:
                    self._invalidate()

                    return change.type

            return None

    @property
    def meta(self) -> Optional["RobotFileMeta"]:
        return self._meta

    def _update(self) -> None:
        self.parent._logger.debug(
            lambda: f"Load resource {self.name} from source {self.source_path}", context_name="import"
        )

        extension = self.source_path.suffix
        if extension.lower() not in RESOURCE_EXTENSIONS:
            raise ImportError(
                f"Invalid resource file extension '{extension}'. "
                f"Supported extensions are {', '.join(repr(s) for s in RESOURCE_EXTENSIONS)}."
            )

        self._document = self.parent.documents_manager.get_or_open_document(self.source_path)
        self._meta = ImportsManager.get_resource_meta(str(self.source_path))

        if self._document._version is None:
            self.file_watchers.append(
                self.parent.file_watcher_manager.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(self._document.uri.to_path())],
                )
            )

    def _invalidate(self) -> None:
        if self._document is None and len(self.file_watchers) == 0:
            return

        self._remove_file_watcher()

        self._document = None
        self._lib_doc = None
        self._meta = None

    def is_valid(self) -> bool:
        with self._lock:
            return self._document is not None

    def get_document(self) -> TextDocument:
        with self._lock:
            self._get_document()

        assert self._document is not None

        return self._document

    def _get_document(self) -> TextDocument:
        if self._document is None:
            self._update()

        assert self._document is not None

        return self._document

    def get_namespace(self) -> "Namespace":
        with self._lock:
            return self._get_namespace()

    def _get_namespace(self) -> "Namespace":
        return self.parent.get_namespace_for_resource(self._get_document())

    def get_resource_doc(self) -> ResourceDoc:
        with self._lock:
            if self._lib_doc is None:
                self._lib_doc = self.parent.get_resource_doc_from_document(self._get_document())

            return self._lib_doc

    def get_libdoc(self) -> ResourceDoc:
        return self.get_resource_doc()


@dataclass(frozen=True, slots=True)
class _VariablesEntryKey:
    name: str
    args: Tuple[Any, ...]


class _VariablesEntry(_ImportEntry):
    def __init__(
        self,
        name: str,
        args: Tuple[Any, ...],
        working_dir: str,
        base_dir: str,
        parent: "ImportsManager",
        variables: Optional[Dict[str, Any]] = None,
        resolve_variables: bool = True,
        resolve_command_line_vars: bool = True,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self.args = args
        self.working_dir = working_dir
        self.base_dir = base_dir
        self.variables = variables
        self.resolve_variables = resolve_variables
        self.resolve_command_line_vars = resolve_command_line_vars
        self._lib_doc: Optional[VariablesDoc] = None
        self._meta: Optional[LibraryMetaData] = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__qualname__}(name={self.name!r}, "
            f"args={self.args!r}, file_watchers={self.file_watchers!r}, id={id(self)!r}"
        )

    def check_file_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]:
        with self._lock:
            if self._lib_doc is None:
                return None

            for change in changes:
                uri = Uri(change.uri)
                if uri.scheme != "file":
                    continue

                path = uri.to_path()
                if self._lib_doc.source:
                    try:
                        is_same = path.samefile(Path(self._lib_doc.source))
                    except OSError:
                        is_same = not Path(self._lib_doc.source).exists()
                    if is_same:
                        self._invalidate()

                        return change.type

            return None

    @property
    def meta(self) -> Optional["LibraryMetaData"]:
        return self._meta

    def _update(self) -> None:
        self._lib_doc, self._meta = self.parent._get_variables_libdoc(
            self.name,
            self.args,
            self.working_dir,
            self.base_dir,
            self.variables,
            self.resolve_variables,
            self.resolve_command_line_vars,
        )

        if self._lib_doc is not None:
            self.file_watchers.append(
                self.parent.file_watcher_manager.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(self._lib_doc.source)],
                )
            )

    def _invalidate(self) -> None:
        if self._lib_doc is None and len(self.file_watchers) == 0:
            return

        self._remove_file_watcher()

        self._lib_doc = None
        self._meta = None

    def is_valid(self) -> bool:
        with self._lock:
            return self._lib_doc is not None

    def get_libdoc(self) -> VariablesDoc:
        with self._lock:
            if self._lib_doc is None:
                self._update()

            assert self._lib_doc is not None

            return self._lib_doc


@dataclass(slots=True)
class LibraryMetaData:
    name: Optional[str]
    member_name: Optional[str]
    origin: Optional[str]
    submodule_search_locations: Optional[List[str]]
    by_path: bool

    mtimes: Optional[Dict[str, int]] = None

    has_errors: bool = False

    @property
    def cache_key(self) -> str:
        if self.by_path:
            if self.origin is not None:
                return self.origin
        else:
            if self.name is not None:
                return self.name + (f".{self.member_name}" if self.member_name else "")

        raise ValueError("Cannot determine cache key.")


def _collect_library_mtimes(
    origin: Optional[str],
    submodule_search_locations: Optional[List[str]],
) -> Optional[Dict[str, int]]:
    """Collect mtimes from origin and submodule_search_locations."""
    mtimes: Dict[str, int] = {}

    if origin is not None:
        mtimes[origin] = os.stat(origin, follow_symlinks=False).st_mtime_ns

    if submodule_search_locations:
        for loc in submodule_search_locations:
            for dirpath, _dirnames, filenames in os.walk(loc):
                for filename in filenames:
                    if filename.endswith(".py"):
                        filepath = os.path.join(dirpath, filename)
                        mtimes[filepath] = os.stat(filepath, follow_symlinks=False).st_mtime_ns

    return mtimes or None


def _matches_any_pattern(
    patterns: List[Pattern],
    name: Optional[str],
    origin: Optional[str],
) -> bool:
    return any(
        (p.matches(name) if name is not None else False) or (p.matches(origin) if origin is not None else False)
        for p in patterns
    )


@dataclass(slots=True)
class RobotFileMeta:
    source: str
    mtime_ns: int


@dataclass(slots=True)
class NamespaceMetaData:
    """Lightweight metadata for fast cache freshness checks.

    Stored alongside NamespaceData in the disk cache. Checked before
    loading the full NamespaceData pickle to avoid unnecessary I/O.
    """

    source: str
    source_mtime_ns: int
    config_fingerprint: Any
    dependency_fingerprints: Dict[str, Any] = field(default_factory=dict)


class ImportsManager:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        documents_manager: DocumentsManager,
        file_watcher_manager: Optional[FileWatcherManagerBase],
        document_cache_helper: "DocumentsCacheHelper",
        root_folder: Path,
        variables: Dict[str, str],
        variable_files: List[str],
        environment: Optional[Dict[str, str]],
        ignored_libraries: List[str],
        ignored_variables: List[str],
        ignore_arguments_for_library: List[str],
        global_library_search_order: List[str],
        cache_base_path: Optional[Path],
        load_library_timeout: Optional[int] = None,
    ) -> None:
        super().__init__()

        self.documents_manager = documents_manager
        self.documents_manager.did_create_uri.add(self._on_possible_imports_modified)
        self.documents_manager.did_change.add(self._on_possible_resource_document_modified)

        self.file_watcher_manager: FileWatcherManagerBase = (
            file_watcher_manager if file_watcher_manager is not None else FileWatcherManagerDummy()
        )

        self.document_cache_helper = document_cache_helper

        self.root_folder = root_folder

        if cache_base_path is None:
            cache_base_path = root_folder

        self._logger.trace(lambda: f"use {cache_base_path} as base for caching")

        self.cache_path = cache_base_path / ".robotcode_cache"
        self.data_cache = DefaultDataCache(
            self.cache_path
            / f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            / get_robot_version_str(),
            app_version=__version__,
        )
        weakref.finalize(self, DefaultDataCache.close, self.data_cache)

        self.cmd_variables = variables
        self.cmd_variable_files = variable_files

        self.ignored_libraries_patters = [Pattern(s) for s in ignored_libraries]
        self.ignored_variables_patters = [Pattern(s) for s in ignored_variables]
        self.ignore_arguments_for_library_patters = [Pattern(s) for s in ignore_arguments_for_library]

        self.global_library_search_order = global_library_search_order

        self._libaries_lock = RLock(default_timeout=120, name="ImportsManager._libaries_lock")
        self._libaries: Dict[_LibrariesEntryKey, _LibrariesEntry] = {}
        self._resources_lock = RLock(default_timeout=120, name="ImportsManager._resources_lock")
        self._resources: Dict[_ResourcesEntryKey, _ResourcesEntry] = {}
        self._variables_lock = RLock(default_timeout=120, name="ImportsManager._variables_lock")
        self._variables: Dict[_VariablesEntryKey, _VariablesEntry] = {}
        self.file_watchers: List[FileWatcherEntry] = []
        self._command_line_variables: Optional[List[VariableDefinition]] = None
        self._command_line_variables_lock = RLock(
            default_timeout=120, name="ImportsManager._command_line_variables_lock"
        )
        self._resolvable_command_line_variables: Optional[Dict[str, Any]] = None
        self._resolvable_command_line_variables_lock = RLock(
            default_timeout=120, name="ImportsManager._resolvable_command_line_variables_lock"
        )

        self._environment = dict(os.environ)
        if environment:
            self._environment.update(environment)

        workspace_langs = self.document_cache_helper.get_languages_for_document(Uri.from_path(self.root_folder))
        if workspace_langs is not None:
            languages_fingerprint: Any = (
                tuple(sorted(workspace_langs.bdd_prefixes)),
                tuple(sorted(workspace_langs.headers.items())),
                tuple(sorted(workspace_langs.settings.items())),
                tuple(sorted(workspace_langs.true_strings)),
                tuple(sorted(workspace_langs.false_strings)),
            )
        else:
            languages_fingerprint = None

        self._config_fingerprint: Any = (
            tuple(sorted(self.cmd_variables.items())),
            tuple(self.cmd_variable_files),
            tuple(sorted((k, v) for k, v in self._environment.items() if k not in os.environ)),
            tuple(self.global_library_search_order),
            languages_fingerprint,
        )

        self._library_files_cache = SimpleLRUCache(2048)
        self._resource_files_cache = SimpleLRUCache(2048)
        self._variables_files_cache = SimpleLRUCache(2048)
        self._module_spec_cache: Dict[str, ModuleSpec] = {}

        self._executor_lock = RLock(default_timeout=120, name="ImportsManager._executor_lock")
        self._executor: Optional[ProcessPoolExecutor] = None

        self._resource_document_changed_timer_lock = RLock(
            default_timeout=120, name="ImportsManager._resource_document_changed_timer_lock"
        )
        self._resource_document_changed_timer: Optional[threading.Timer] = None
        self._resource_document_changed_timer_interval = 1
        self._resource_document_changed_documents: Set[TextDocument] = set()

        self._resource_libdoc_cache: "weakref.WeakKeyDictionary[ast.AST, Dict[str, ResourceDoc]]" = (
            weakref.WeakKeyDictionary()
        )

        self._diagnostics: List[Diagnostic] = []

        # precedence: explicit config (arg) > environment variable > default
        if load_library_timeout is None:
            env_value = os.environ.get(ENV_LOAD_LIBRARY_TIMEOUT_VAR)
            if env_value is not None:
                try:
                    load_library_timeout = int(env_value)
                except ValueError:
                    self._logger.warning(
                        lambda: (
                            "Invalid value for "
                            f"{ENV_LOAD_LIBRARY_TIMEOUT_VAR}={env_value!r}, using default "
                            f"{DEFAULT_LOAD_LIBRARY_TIMEOUT}"
                        ),
                        context_name="imports",
                    )
                    load_library_timeout = DEFAULT_LOAD_LIBRARY_TIMEOUT
            else:
                load_library_timeout = DEFAULT_LOAD_LIBRARY_TIMEOUT

        # enforce sane lower bound
        if load_library_timeout <= 0:
            self._logger.warning(
                lambda: (
                    "Configured load_library_timeout "
                    f"{load_library_timeout} is not > 0, fallback to {DEFAULT_LOAD_LIBRARY_TIMEOUT}"
                ),
                context_name="imports",
            )
            load_library_timeout = DEFAULT_LOAD_LIBRARY_TIMEOUT

        self.load_library_timeout = load_library_timeout

        self._logger.trace(
            lambda: f"Using load_library_timeout={self.load_library_timeout}s",
            context_name="imports",
        )

    @staticmethod
    def _shutdown_executor(executor: ProcessPoolExecutor) -> None:
        try:
            executor.shutdown(wait=False)
        except RuntimeError:
            pass

    @property
    def diagnostics(self) -> List[Diagnostic]:
        self.get_command_line_variables()

        return self._diagnostics

    @property
    def environment(self) -> Mapping[str, str]:
        return self._environment

    @property
    def config_fingerprint(self) -> Any:
        """Cached configuration snapshot.

        Computed once at init from cmd_variables, cmd_variable_files,
        environment, and global_library_search_order. Changes are
        detected via direct ``==`` comparison.
        """
        return self._config_fingerprint

    def compute_dependency_fingerprints(self, namespace: "Namespace") -> Dict[str, Any]:
        """Collect current metadata for all dependencies of a namespace.

        Each value is the metadata object itself (LibraryMetaData, RobotFileMeta,
        or an mtime int). Changes are detected via direct ``==`` comparison
        against the saved metadata — no hashing needed.

        Uses already-cached metadata from the internal import cache to avoid
        expensive module resolution (find_library / get_module_spec).
        Falls back to the full get_*_meta methods when no cached entry exists.
        """
        fingerprints: Dict[str, Any] = {}

        for entry in namespace.libraries.values():
            try:
                lib_meta = self.get_cached_library_meta(entry.import_name, entry.args)
                if lib_meta is None:
                    lib_meta, _, _ = self.get_library_meta(entry.import_name)
                if lib_meta is not None:
                    fingerprints[f"lib:{entry.import_name}"] = lib_meta
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass

        for entry in namespace.resources.values():
            source = entry.library_doc.source
            if source:
                try:
                    res_meta = self.get_cached_resource_meta(source)
                    if res_meta is None:
                        res_meta = self.get_resource_meta(source)
                    if res_meta is not None:
                        fingerprints[f"res:{source}"] = res_meta
                    else:
                        mtime = os.stat(source, follow_symlinks=False).st_mtime_ns
                        fingerprints[f"res:{source}"] = mtime
                except OSError:
                    pass

        for entry in namespace.variables_imports.values():
            try:
                var_meta = self.get_cached_variables_meta(entry.import_name, entry.args)
                if var_meta is None:
                    var_meta, _ = self.get_variables_meta(entry.import_name)
                if var_meta is not None:
                    fingerprints[f"var:{entry.import_name}"] = var_meta
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass

        return fingerprints

    def build_namespace_meta(self, source: str, namespace: "Namespace") -> NamespaceMetaData:
        """Build a NamespaceMetaData for the given namespace and its dependencies."""
        try:
            source_mtime_ns = os.stat(source, follow_symlinks=False).st_mtime_ns
        except OSError:
            source_mtime_ns = 0

        return NamespaceMetaData(
            source=source,
            source_mtime_ns=source_mtime_ns,
            config_fingerprint=self.config_fingerprint,
            dependency_fingerprints=self.compute_dependency_fingerprints(namespace),
        )

    def validate_namespace_meta(self, meta: NamespaceMetaData) -> bool:
        """Check whether a cached NamespaceMetaData is still fresh.

        Performs a 2-level validation:
        Level 1 (fast): source_mtime_ns, config_fingerprint
        Level 2 (dependency check): each dependency fingerprint
        """
        # Level 1: fast checks
        try:
            current_mtime = os.stat(meta.source, follow_symlinks=False).st_mtime_ns
        except OSError:
            return False

        if meta.source_mtime_ns != current_mtime:
            return False

        if meta.config_fingerprint != self.config_fingerprint:
            return False

        # Level 2: dependency checks — direct comparison, no hashing
        base_dir = os.path.dirname(meta.source)
        for key, saved_value in meta.dependency_fingerprints.items():
            if key.startswith("lib:"):
                lib_name = key[4:]
                try:
                    lib_meta = self.get_cached_library_meta(lib_name)
                    if lib_meta is None:
                        lib_meta, _, _ = self.get_library_meta(lib_name, base_dir=base_dir)
                    if lib_meta is None or lib_meta != saved_value:
                        return False
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    return False
            elif key.startswith("res:"):
                res_source = key[4:]
                try:
                    res_meta = self.get_cached_resource_meta(res_source)
                    if res_meta is None:
                        res_meta = self.get_resource_meta(res_source)
                    if res_meta is None or res_meta != saved_value:
                        return False
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    return False
            elif key.startswith("var:"):
                var_name = key[4:]
                try:
                    var_meta = self.get_cached_variables_meta(var_name)
                    if var_meta is None:
                        var_meta, _ = self.get_variables_meta(var_name, base_dir=base_dir)
                    if var_meta is None or var_meta != saved_value:
                        return False
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    return False

        return True

    def get_namespace_for_resource(self, document: TextDocument) -> "Namespace":
        return self.document_cache_helper.get_resource_namespace(document)

    def get_resource_doc_from_document(self, document: TextDocument) -> ResourceDoc:
        source = str(document.uri.to_path())

        if not self._is_document_loaded(source):
            cached, _meta = self._get_model_doc_cached(source)
            if cached is not None:
                return cached

        model = self.document_cache_helper.get_resource_model(document)
        return self.get_libdoc_from_model(model, source)

    def clear_cache(self) -> None:
        if self.cache_path.exists():
            shutil.rmtree(self.cache_path, ignore_errors=True)

            self._logger.debug(lambda: f"Cleared cache {self.cache_path}")

    @_logger.call
    def get_command_line_variables(self) -> List[VariableDefinition]:
        with self._command_line_variables_lock:
            if self._command_line_variables is None:
                command_line_vars: List[VariableDefinition] = []

                command_line_vars += [
                    CommandLineVariableDefinition(
                        0,
                        0,
                        0,
                        0,
                        "",
                        f"${{{k}}}",
                        None,
                        has_value=True,
                        value=v,
                    )
                    for k, v in self.cmd_variables.items()
                ]

                for variable_file in self.cmd_variable_files:
                    name, args = split_args_from_name_or_path(str(variable_file))
                    try:
                        lib_doc = self.get_libdoc_for_variables_import(
                            name.replace("\\", "\\\\"),
                            tuple(args),
                            str(self.root_folder),
                            self,
                            resolve_variables=False,
                            resolve_command_line_vars=False,
                        )
                        if lib_doc is not None:
                            command_line_vars += [
                                CommandLineVariableDefinition(
                                    line_no=e.line_no,
                                    col_offset=e.col_offset,
                                    end_line_no=e.end_line_no,
                                    end_col_offset=e.end_col_offset,
                                    source=e.source,
                                    name=e.name,
                                    name_token=e.name_token,
                                    has_value=e.has_value,
                                    resolvable=e.resolvable,
                                    value=e.value,
                                    value_is_native=e.value_is_native,
                                )
                                for e in lib_doc.variables
                            ]

                            if lib_doc.errors:
                                for error in lib_doc.errors:
                                    self._diagnostics.append(
                                        Diagnostic(
                                            Range.zero(),
                                            f"Processing variable file variable file '{name}({', '.join(args)})' failed"
                                            + ("" if error.source is not None else f": {error.message}"),
                                            DiagnosticSeverity.ERROR,
                                            error.type_name,
                                            related_information=(
                                                [
                                                    DiagnosticRelatedInformation(
                                                        Location(
                                                            str(Uri.from_path(os.path.abspath(error.source))),
                                                            Range.from_int_range(
                                                                (error.line_no - 1) if error.line_no is not None else -1
                                                            ),
                                                        ),
                                                        error.message,
                                                    )
                                                ]
                                                if error.source is not None
                                                else None
                                            ),
                                        )
                                    )
                    except RobotError as e:
                        self._diagnostics.append(
                            Diagnostic(
                                Range.zero(),
                                f"Error in command line variable file '{name}({', '.join(args)})': {e}",
                                DiagnosticSeverity.ERROR,
                                type(e).__name__,
                            )
                        )
                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException as e:
                        self._diagnostics.append(
                            Diagnostic(
                                Range.zero(),
                                f"Error in command line variable file '{name}({', '.join(args)})': {e}",
                                DiagnosticSeverity.ERROR,
                                type(e).__name__,
                            )
                        )
                        ex = e
                        self._logger.exception(
                            lambda: f"Error in command line variable file '{name}({', '.join(args)})'",
                            exc_info=ex,
                        )

                self._command_line_variables = command_line_vars

            return self._command_line_variables or []

    def get_resolvable_command_line_variables(self) -> Dict[str, Any]:
        with self._resolvable_command_line_variables_lock:
            if self._resolvable_command_line_variables is None:
                self._resolvable_command_line_variables = {
                    v.name: v.value for v in (self.get_command_line_variables()) if v.has_value
                }

            return self._resolvable_command_line_variables

    @event
    def libraries_changed(sender, libraries: List[LibraryDoc]) -> None: ...

    @event
    def resources_changed(sender, resources: List[LibraryDoc]) -> None: ...

    @event
    def variables_changed(sender, variables: List[LibraryDoc]) -> None: ...

    @event
    def imports_changed(sender, uri: DocumentUri) -> None: ...

    def _on_possible_imports_modified(self, sender: Any, uri: DocumentUri) -> None:
        # Fires on FileChangeType.CREATED — needed so namespaces with previously
        # unresolved imports (file didn't exist yet) get invalidated and re-analyzed.
        self.imports_changed(self, uri)

    @language_id("robotframework")
    def _on_possible_resource_document_modified(self, sender: Any, document: TextDocument) -> None:
        run_as_task(self.__on_possible_resource_document_modified, sender, document)

    def __on_possible_resource_document_modified(self, sender: Any, document: TextDocument) -> None:
        with self._resource_document_changed_timer_lock:
            if document in self._resource_document_changed_documents:
                return

            if self._resource_document_changed_timer is not None:
                self._resource_document_changed_timer.cancel()
                self._resource_document_changed_timer = None

            self._resource_document_changed_documents.add(document)

            self._resource_document_changed_timer = threading.Timer(
                self._resource_document_changed_timer_interval, self.__resource_documents_changed
            )
            self._resource_document_changed_timer.start()

    def __resource_documents_changed(self) -> None:
        with self._resource_document_changed_timer_lock:
            self._resource_document_changed_timer = None

            documents = self._resource_document_changed_documents
            self._resource_document_changed_documents = set()

        for document in documents:
            self.__resource_document_changed(document)

    def __resource_document_changed(self, document: TextDocument) -> None:
        resource_changed: List[LibraryDoc] = []

        with self._resources_lock:
            for r_entry in self._resources.values():
                lib_doc: Optional[LibraryDoc] = None
                try:
                    if not r_entry.is_valid():
                        continue

                    uri = r_entry.get_document().uri
                    result = uri == document.uri
                    if result:
                        lib_doc = r_entry.get_libdoc()
                        r_entry.invalidate()

                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    result = True

                if result and lib_doc is not None:
                    resource_changed.append(lib_doc)

        if resource_changed:
            self.resources_changed(self, resource_changed)

    @_logger.call
    def did_change_watched_files(self, sender: Any, changes: List[FileEvent]) -> None:
        libraries_changed: List[Tuple[_LibrariesEntryKey, FileChangeType, Optional[LibraryDoc]]] = []
        resource_changed: List[Tuple[_ResourcesEntryKey, FileChangeType, Optional[LibraryDoc]]] = []
        variables_changed: List[Tuple[_VariablesEntryKey, FileChangeType, Optional[LibraryDoc]]] = []

        lib_doc: Optional[LibraryDoc]

        with self._libaries_lock:
            for l_key, l_entry in self._libaries.items():
                lib_doc = None
                if l_entry.is_valid():
                    lib_doc = l_entry.get_libdoc()
                result = l_entry.check_file_changed(changes)
                if result is not None:
                    libraries_changed.append((l_key, result, lib_doc))

        try:
            with self._resources_lock:
                for r_key, r_entry in self._resources.items():
                    lib_doc = None
                    if r_entry.is_valid():
                        lib_doc = r_entry.get_libdoc()
                    result = r_entry.check_file_changed(changes)
                    if result is not None:
                        resource_changed.append((r_key, result, lib_doc))
        except BaseException as e:
            self._logger.exception(e)
            raise

        with self._variables_lock:
            for v_key, v_entry in self._variables.items():
                lib_doc = None
                if v_entry.is_valid():
                    lib_doc = v_entry.get_libdoc()
                result = v_entry.check_file_changed(changes)
                if result is not None:
                    variables_changed.append((v_key, result, lib_doc))

        if libraries_changed:
            for l, t, _ in libraries_changed:
                if t == FileChangeType.DELETED:
                    self.__remove_library_entry(l, self._libaries[l], True)

            self.libraries_changed(self, [v for (_, _, v) in libraries_changed if v is not None])

        if resource_changed:
            for r, t, _ in resource_changed:
                if t == FileChangeType.DELETED:
                    self.__remove_resource_entry(r, self._resources[r], True)

            self.resources_changed(self, [v for (_, _, v) in resource_changed if v is not None])

        if variables_changed:
            for v, t, _ in variables_changed:
                if t == FileChangeType.DELETED:
                    self.__remove_variables_entry(v, self._variables[v], True)

            self.variables_changed(self, [v for (_, _, v) in variables_changed if v is not None])

    def __remove_library_entry(
        self,
        entry_key: _LibrariesEntryKey,
        entry: _LibrariesEntry,
        now: bool = False,
    ) -> None:
        try:
            if len(entry.references) == 0 or now:
                self._logger.debug(lambda: f"Remove Library Entry {entry_key}")
                with self._libaries_lock:
                    if len(entry.references) == 0 or now:
                        e1 = self._libaries.get(entry_key, None)
                        if e1 == entry:
                            self._libaries.pop(entry_key, None)
                            entry.invalidate()
                self._logger.debug(lambda: f"Library Entry {entry_key} removed")
        finally:
            self._library_files_cache.clear()

    def __remove_resource_entry(
        self,
        entry_key: _ResourcesEntryKey,
        entry: _ResourcesEntry,
        now: bool = False,
    ) -> None:
        try:
            if len(entry.references) == 0 or now:
                self._logger.debug(lambda: f"Remove Resource Entry {entry_key}")
                with self._resources_lock:
                    if len(entry.references) == 0 or now:
                        e1 = self._resources.get(entry_key, None)
                        if e1 == entry:
                            self._resources.pop(entry_key, None)

                            entry.invalidate()
                self._logger.debug(lambda: f"Resource Entry {entry_key} removed")
        finally:
            self._resource_files_cache.clear()

    def __remove_variables_entry(
        self,
        entry_key: _VariablesEntryKey,
        entry: _VariablesEntry,
        now: bool = False,
    ) -> None:
        try:
            if len(entry.references) == 0 or now:
                self._logger.debug(lambda: f"Remove Variables Entry {entry_key}")
                with self._variables_lock:
                    if len(entry.references) == 0 or now:
                        e1 = self._variables.get(entry_key, None)
                        if e1 == entry:
                            self._variables.pop(entry_key, None)
                            entry.invalidate()
                self._logger.debug(lambda: f"Variables Entry {entry_key} removed")
        finally:
            self._variables_files_cache.clear()

    def _get_module_spec_cached(self, module_name: str) -> Optional[ModuleSpec]:
        cached = self._module_spec_cache.get(module_name)
        if cached is not None:
            return cached

        spec = get_module_spec(module_name)
        if spec is not None:
            self._module_spec_cache[module_name] = spec
        return spec

    def get_library_meta(
        self,
        name: str,
        base_dir: str = ".",
        variables: Optional[Dict[str, Optional[Any]]] = None,
    ) -> Tuple[Optional[LibraryMetaData], str, bool]:
        import_name = name
        ignore_arguments = False
        try:
            import_name = self.find_library(name, base_dir=base_dir, variables=variables)

            result: Optional[LibraryMetaData] = None
            module_spec: Optional[ModuleSpec] = None
            if is_library_by_path(import_name):
                if (p := Path(import_name)).exists():
                    result = LibraryMetaData(
                        p.stem,
                        None,
                        import_name,
                        None,
                        True,
                        mtimes=_collect_library_mtimes(import_name, None),
                    )
            else:
                module_spec = self._get_module_spec_cached(import_name)
                if module_spec is not None and module_spec.origin is not None:
                    result = LibraryMetaData(
                        module_spec.name,
                        module_spec.member_name,
                        module_spec.origin,
                        module_spec.submodule_search_locations,
                        False,
                        mtimes=_collect_library_mtimes(module_spec.origin, module_spec.submodule_search_locations),
                    )

            if result is not None:
                ignore_arguments = _matches_any_pattern(
                    self.ignore_arguments_for_library_patters, result.name, result.origin
                )

                if _matches_any_pattern(self.ignored_libraries_patters, result.name, result.origin):
                    self._logger.debug(
                        lambda: (
                            f"Ignore library {result.name or '' if result is not None else ''}"
                            f" {result.origin or '' if result is not None else ''} for caching."
                        ),
                        context_name="import",
                    )
                    return None, import_name, ignore_arguments

            return result, import_name, ignore_arguments
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            pass

        return None, import_name, ignore_arguments

    def get_variables_meta(
        self,
        name: str,
        base_dir: str = ".",
        variables: Optional[Dict[str, Optional[Any]]] = None,
        resolve_variables: bool = True,
        resolve_command_line_vars: bool = True,
    ) -> Tuple[Optional[LibraryMetaData], str]:
        import_name = name
        try:
            import_name = self.find_variables(
                name,
                base_dir=base_dir,
                variables=variables,
                resolve_variables=resolve_variables,
                resolve_command_line_vars=resolve_command_line_vars,
            )

            result: Optional[LibraryMetaData] = None
            module_spec: Optional[ModuleSpec] = None
            if is_variables_by_path(import_name):
                if (p := Path(import_name)).exists():
                    result = LibraryMetaData(
                        p.stem,
                        None,
                        import_name,
                        None,
                        True,
                        mtimes=_collect_library_mtimes(import_name, None),
                    )
            else:
                module_spec = self._get_module_spec_cached(import_name)
                if module_spec is not None and module_spec.origin is not None:
                    result = LibraryMetaData(
                        module_spec.name,
                        module_spec.member_name,
                        module_spec.origin,
                        module_spec.submodule_search_locations,
                        False,
                        mtimes=_collect_library_mtimes(module_spec.origin, module_spec.submodule_search_locations),
                    )

            if result is not None:
                if _matches_any_pattern(self.ignored_variables_patters, result.name, result.origin):
                    self._logger.debug(
                        lambda: (
                            f"Ignore Variables {result.name or '' if result is not None else ''}"
                            f" {result.origin or '' if result is not None else ''} for caching."
                        )
                    )
                    return None, import_name

            return result, import_name
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            pass

        return None, name

    def get_cached_library_meta(self, import_name: str, args: Tuple[Any, ...] = ()) -> Optional[LibraryMetaData]:
        """Return already-computed LibraryMetaData from the internal cache, or None.

        Matches by import name and args to find the correct entry, since
        the same library with different args may produce different keywords.
        """
        with self._libaries_lock:
            for entry in self._libaries.values():
                if entry.name == import_name and entry.args == args:
                    return entry.meta
        return None

    def get_cached_resource_meta(self, source: str) -> Optional[RobotFileMeta]:
        """Return already-computed RobotFileMeta from the internal cache, or None."""
        entry_key = _ResourcesEntryKey(str(normalized_path(Path(source))))
        with self._resources_lock:
            entry = self._resources.get(entry_key)
            if entry is not None:
                return entry.meta
        return None

    def get_cached_variables_meta(self, import_name: str, args: Tuple[Any, ...] = ()) -> Optional[LibraryMetaData]:
        """Return already-computed LibraryMetaData for a variables import, or None.

        Matches by import name and args, since variable files can return
        different content depending on the arguments.
        """
        with self._variables_lock:
            for entry in self._variables.values():
                if entry.name == import_name and entry.args == args:
                    return entry.meta
        return None

    def find_library(
        self,
        name: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        if contains_variable(name, "$@&%"):
            return self._library_files_cache.get(self._find_library, name, base_dir, variables)

        return self._library_files_cache.get(self._find_library_simple, name, base_dir)

    def _find_library(
        self,
        name: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        return find_library(
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
        )

    def _find_library_simple(
        self,
        name: str,
        base_dir: str,
    ) -> str:
        if name in STDLIBS:
            result = ROBOT_LIBRARY_PACKAGE + "." + name
        else:
            result = name

        if is_library_by_path(result):
            return find_file_ex(result, base_dir, "Library")

        return result

    def find_resource(
        self,
        name: str,
        base_dir: str,
        file_type: str = "Resource",
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        if contains_variable(name, "$@&%"):
            return self._resource_files_cache.get(self.__find_resource, name, base_dir, file_type, variables)

        return self._resource_files_cache.get(self.__find_resource_simple, name, base_dir, file_type)

    @_logger.call
    def __find_resource(
        self,
        name: str,
        base_dir: str,
        file_type: str = "Resource",
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        return find_file(
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
            file_type,
        )

    def __find_resource_simple(
        self,
        name: str,
        base_dir: str,
        file_type: str = "Resource",
    ) -> str:
        return find_file_ex(name, base_dir, file_type)

    def find_variables(
        self,
        name: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
        resolve_variables: bool = True,
        resolve_command_line_vars: bool = True,
    ) -> str:
        if resolve_variables and contains_variable(name, "$@&%"):
            return self._variables_files_cache.get(
                self.__find_variables,
                name,
                base_dir,
                variables,
                resolve_command_line_vars,
            )
        return self._variables_files_cache.get(self.__find_variables_simple, name, base_dir)

    @_logger.call
    def __find_variables(
        self,
        name: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
        resolve_command_line_vars: bool = True,
    ) -> str:
        return find_variables(
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables() if resolve_command_line_vars else None,
            variables,
        )

    @_logger.call
    def __find_variables_simple(
        self,
        name: str,
        base_dir: str,
    ) -> str:
        if get_robot_version() >= (5, 0):
            if is_variables_by_path(name):
                return find_file_ex(name, base_dir, "Variables")

            return name

        return find_file_ex(name, base_dir, "Variables")

    @property
    def executor(self) -> ProcessPoolExecutor:
        with self._executor_lock:
            if self._executor is None:
                self._executor = ProcessPoolExecutor(mp_context=mp.get_context("spawn"))
                weakref.finalize(self, ImportsManager._shutdown_executor, self._executor)

        return self._executor

    def _run_in_subprocess(self, func: Any, func_args: Tuple[Any, ...], timeout_msg: str) -> Any:
        """Run a callable in a fresh single-use subprocess and return the result.

        A fresh process per import is intentional: libraries and variable files
        can pollute the interpreter (e.g. via sys.modules, global state, native
        extensions) and cannot be safely re-imported after on-disk changes.
        """
        executor = ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn"))
        try:
            try:
                return executor.submit(func, *func_args).result(self.load_library_timeout)
            except TimeoutError as e:
                raise RuntimeError(
                    f"{timeout_msg} "
                    f"timed out after {self.load_library_timeout} seconds. "
                    "The import may be slow or blocked. "
                    "If required, increase the timeout by setting the ROBOTCODE_LOAD_LIBRARY_TIMEOUT "
                    "environment variable."
                ) from e
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)
            raise
        finally:
            executor.shutdown(wait=True)

    def _save_import_cache(
        self,
        section: CacheSection,
        meta: Optional[LibraryMetaData],
        result: Any,
        kind: str,
        name: str,
        args: Tuple[Any, ...],
    ) -> None:
        """Save an import result to the disk cache, or log skip if no meta."""
        try:
            if meta is not None:
                try:
                    self.data_cache.save_entry(section, meta.cache_key, meta, result)
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    raise RuntimeError(f"Cannot write cache entry for {kind} '{name}'") from e
            else:
                self._logger.debug(lambda: f"Skip caching {kind} {name}{args!r}", context_name="import")
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)

    def _get_library_libdoc(
        self,
        name: str,
        args: Tuple[Any, ...],
        working_dir: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Tuple[LibraryDoc, Optional[LibraryMetaData]]:
        meta, _source, ignore_arguments = self.get_library_meta(name, base_dir, variables)

        if meta is not None and not meta.has_errors:
            try:
                entry = self.data_cache.read_entry(CacheSection.LIBRARY, meta.cache_key, LibraryMetaData, LibraryDoc)
                if entry is not None and entry.meta is not None:
                    if entry.meta.has_errors:
                        self._logger.debug(
                            lambda: f"Saved library spec for {name}{args!r} is not used due to errors in meta data",
                            context_name="import",
                        )
                    elif entry.meta == meta:
                        self._logger.debug(lambda: f"Use cached library meta data for {name}", context_name="import")
                        return entry.data, meta
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._logger.exception(e)

        self._logger.debug(lambda: f"Load library in process {name}{args!r}", context_name="import")

        result = self._run_in_subprocess(
            get_library_doc,
            (
                name,
                args if not ignore_arguments else (),
                working_dir,
                base_dir,
                self.get_resolvable_command_line_variables(),
                variables,
            ),
            f"Loading library {name!r} with args {args!r} (working_dir={working_dir!r}, base_dir={base_dir!r})",
        )

        if meta is not None:
            meta.has_errors = bool(result.errors)

        self._save_import_cache(CacheSection.LIBRARY, meta, result, "library", name, args)

        return result, meta

    @_logger.call
    def get_libdoc_for_library_import(
        self,
        name: str,
        args: Tuple[Any, ...],
        base_dir: str,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> LibraryDoc:
        with self._logger.measure_time(lambda: f"loading library {name}{args!r}", context_name="import"):
            source = self.find_library(name, base_dir, variables)

            resolved_args = resolve_args(
                args,
                str(self.root_folder),
                base_dir,
                self.get_resolvable_command_line_variables(),
                variables,
            )
            entry_key = _LibrariesEntryKey(source, resolved_args)

            with self._libaries_lock:
                if entry_key not in self._libaries:
                    self._libaries[entry_key] = _LibrariesEntry(
                        self,
                        name,
                        args,
                        str(self.root_folder),
                        base_dir,
                        variables=variables,
                        ignore_reference=sentinel is None,
                    )

                entry = self._libaries[entry_key]

                if not entry.ignore_reference and sentinel is not None and sentinel not in entry.references:
                    fin = weakref.finalize(sentinel, self.__remove_library_entry, entry_key, entry)
                    fin.atexit = False  # type: ignore[misc]
                    entry.references.add(sentinel)

            return entry.get_libdoc()

    def _is_document_loaded(self, source: str) -> bool:
        doc = self.documents_manager.get(Uri.from_path(source))
        return doc is not None and doc.version is not None

    @_logger.call
    def get_libdoc_from_model(
        self,
        model: ast.AST,
        source: str,
    ) -> ResourceDoc:

        entry = self._resource_libdoc_cache.get(model)
        if entry is not None and source in entry:
            return entry[source]

        use_disk_cache = not self._is_document_loaded(source)

        result: Optional[ResourceDoc] = None
        meta: Optional[RobotFileMeta] = None
        if use_disk_cache:
            result, meta = self._get_model_doc_cached(source)
        if result is None:
            result = get_model_doc(model=model, source=source)
            if use_disk_cache:
                if meta is None:
                    meta = self.get_resource_meta(source)
                if meta is not None:
                    self._save_model_doc_cache(source, result, meta)

        if entry is None:
            entry = {}
            self._resource_libdoc_cache[model] = entry

        entry[source] = result

        return result

    @staticmethod
    def get_resource_meta(source: str) -> Optional[RobotFileMeta]:
        try:
            normalized = str(normalized_path(source))
            mtime_ns = os.stat(normalized, follow_symlinks=False).st_mtime_ns
            return RobotFileMeta(normalized, mtime_ns)
        except OSError:
            return None

    def _get_model_doc_cached(self, source: str) -> Tuple[Optional[ResourceDoc], Optional["RobotFileMeta"]]:
        meta = self.get_resource_meta(source)
        if meta is None:
            return None, None

        try:
            entry = self.data_cache.read_entry(CacheSection.RESOURCE, meta.source, RobotFileMeta, ResourceDoc)
            if entry is not None and entry.meta == meta:
                return entry.data, meta
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            ex = e
            self._logger.debug(
                lambda: f"Failed to load cached model doc for {source}: {ex}",
                context_name="import",
            )

        return None, meta

    def _save_model_doc_cache(self, source: str, result: ResourceDoc, meta: "RobotFileMeta") -> None:

        try:
            self.data_cache.save_entry(CacheSection.RESOURCE, meta.source, meta, result)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            ex = e
            self._logger.debug(
                lambda: f"Failed to save model doc cache for {source}: {ex}",
                context_name="import",
            )

    def _get_variables_libdoc(
        self,
        name: str,
        args: Tuple[Any, ...],
        working_dir: str,
        base_dir: str,
        variables: Optional[Dict[str, Any]] = None,
        resolve_variables: bool = True,
        resolve_command_line_vars: bool = True,
    ) -> Tuple[VariablesDoc, Optional[LibraryMetaData]]:
        meta, _source = self.get_variables_meta(
            name,
            base_dir,
            variables,
            resolve_variables,
            resolve_command_line_vars=resolve_command_line_vars,
        )

        if meta is not None:
            try:
                entry = self.data_cache.read_entry(
                    CacheSection.VARIABLES, meta.cache_key, LibraryMetaData, VariablesDoc
                )
                if entry is not None and entry.meta == meta:
                    return entry.data, meta
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._logger.exception(e)

        result = self._run_in_subprocess(
            get_variables_doc,
            (
                name,
                args,
                working_dir,
                base_dir,
                self.get_resolvable_command_line_variables() if resolve_command_line_vars else None,
                variables,
            ),
            f"Loading variables {name!r} with args {args!r} (working_dir={working_dir!r}, base_dir={base_dir!r})",
        )

        self._save_import_cache(CacheSection.VARIABLES, meta, result, "variables", name, args)

        return result, meta

    @_logger.call
    def get_libdoc_for_variables_import(
        self,
        name: str,
        args: Tuple[Any, ...],
        base_dir: str,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
        resolve_variables: bool = True,
        resolve_command_line_vars: bool = True,
    ) -> VariablesDoc:
        with self._logger.measure_time(lambda: f"getting libdoc for variables import {name}", context_name="import"):
            source = self.find_variables(name, base_dir, variables, resolve_variables, resolve_command_line_vars)

            if args:
                resolved_args = resolve_args(
                    args,
                    str(self.root_folder),
                    base_dir,
                    self.get_resolvable_command_line_variables() if resolve_command_line_vars else None,
                    variables,
                )
            else:
                resolved_args = ()

            entry_key = _VariablesEntryKey(source, resolved_args)

            with self._variables_lock:
                if entry_key not in self._variables:
                    self._variables[entry_key] = _VariablesEntry(
                        name,
                        resolved_args,
                        str(self.root_folder),
                        base_dir,
                        self,
                        variables=variables,
                        resolve_variables=resolve_variables,
                        resolve_command_line_vars=resolve_command_line_vars,
                    )

                entry = self._variables[entry_key]

                if sentinel is not None and sentinel not in entry.references:
                    entry.references.add(sentinel)
                    fin = weakref.finalize(sentinel, self.__remove_variables_entry, entry_key, entry)
                    fin.atexit = False  # type: ignore[misc]

            return entry.get_libdoc()

    @_logger.call
    def _get_entry_for_resource_import(
        self,
        name: str,
        base_dir: str,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
        *,
        source: Optional[str] = None,
    ) -> _ResourcesEntry:
        source = source or self.find_resource(name, base_dir, variables=variables)
        normalized_source = os.path.normpath(os.path.abspath(source))

        entry_key = _ResourcesEntryKey(normalized_source)

        with self._resources_lock:
            if entry_key not in self._resources:
                self._resources[entry_key] = _ResourcesEntry(name, self, Path(normalized_source))

            entry = self._resources[entry_key]

            if sentinel is not None and sentinel not in entry.references:
                entry.references.add(sentinel)
                fin = weakref.finalize(sentinel, self.__remove_resource_entry, entry_key, entry)
                fin.atexit = False  # type: ignore[misc]

        return entry

    def get_namespace_and_libdoc_for_resource_import(
        self,
        name: str,
        base_dir: str,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
        *,
        source: Optional[str] = None,
    ) -> Tuple["Namespace", LibraryDoc]:
        with self._logger.measure_time(lambda: f"getting namespace and libdoc for {name}", context_name="import"):
            with self._logger.measure_time(lambda: f"getting resource entry {name}", context_name="import"):
                entry = self._get_entry_for_resource_import(name, base_dir, sentinel, variables, source=source)

            with self._logger.measure_time(lambda: f"getting namespace {name}", context_name="import"):
                namespace = entry.get_namespace()
            with self._logger.measure_time(lambda: f"getting libdoc {name}", context_name="import"):
                libdoc = entry.get_libdoc()

            return namespace, libdoc

    def get_resource_doc_for_resource_import(
        self,
        name: str,
        base_dir: str,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
        *,
        source: Optional[str] = None,
    ) -> ResourceDoc:
        with self._logger.measure_time(lambda: f"getting resource doc for {name}", context_name="import"):
            entry = self._get_entry_for_resource_import(name, base_dir, sentinel, variables, source=source)

            return entry.get_resource_doc()

    def complete_library_import(
        self,
        name: Optional[str],
        base_dir: str = ".",
        variables: Optional[Dict[str, Any]] = None,
    ) -> List[CompleteResult]:
        return self.executor.submit(
            complete_library_import,
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
        ).result(COMPLETE_LIBRARY_IMPORT_TIMEOUT)

    def complete_resource_import(
        self,
        name: Optional[str],
        base_dir: str = ".",
        variables: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[CompleteResult]]:
        return self.executor.submit(
            complete_resource_import,
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
        ).result(COMPLETE_RESOURCE_IMPORT_TIMEOUT)

    def complete_variables_import(
        self,
        name: Optional[str],
        base_dir: str = ".",
        variables: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[CompleteResult]]:
        return self.executor.submit(
            complete_variables_import,
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
        ).result(COMPLETE_VARIABLES_IMPORT_TIMEOUT)

    def resolve_variable(
        self,
        name: str,
        base_dir: str = ".",
        variables: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return resolve_variable(
            name,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
        )

    def replace_variables_scalar(
        self,
        scalar: str,
        base_dir: str = ".",
        variables: Optional[Dict[str, Any]] = None,
        ignore_errors: bool = False,
    ) -> Any:
        return replace_variables_scalar(
            scalar,
            str(self.root_folder),
            base_dir,
            self.get_resolvable_command_line_variables(),
            variables,
            ignore_errors=ignore_errors,
        )

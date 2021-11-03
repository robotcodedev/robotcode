from __future__ import annotations

import ast
import asyncio
import weakref
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Coroutine, List, Optional, Tuple, cast

from ....utils.async_event import async_tasking_event
from ....utils.logging import LoggingDescriptor
from ....utils.path import path_is_relative_to
from ....utils.uri import Uri
from ...common.lsp_types import DocumentUri, FileChangeType, FileEvent
from ...common.parts.workspace import FileWatcherEntry
from ...common.text_document import TextDocument
from ..configuration import RobotConfig
from ..utils.async_ast import walk

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol
    from .namespace import Namespace

from .library_doc import (
    CompleteResult,
    Error,
    KeywordArgumentDoc,
    KeywordDoc,
    KeywordStore,
    LibraryDoc,
    complete_library_import,
    complete_resource_import,
    dummy_first_run_pool,
    find_file,
    find_library,
    get_library_doc,
    init_pool,
    is_embedded_keyword,
)

RESOURCE_EXTENSIONS = (".resource", ".robot", ".txt", ".tsv", ".rst", ".rest")
REST_EXTENSIONS = (".rst", ".rest")
PROCESS_POOL_MAX_WORKERS = None

LOAD_LIBRARY_TIME_OUT = 30
FIND_FILE_TIME_OUT = 10
COMPLETE_LIBRARY_IMPORT_TIME_OUT = COMPLETE_RESOURCE_IMPORT_TIME_OUT = 10


@dataclass()
class _LibrariesEntryKey:
    name: str
    args: Tuple[Any, ...]

    def __hash__(self) -> int:
        return hash((self.name, self.args))


class _LibrariesEntry:
    def __init__(
        self,
        name: str,
        args: Tuple[Any, ...],
        parent: ImportsManager,
        get_libdoc_coroutine: Callable[[], Coroutine[Any, Any, LibraryDoc]],
        ignore_reference: bool = False,
    ) -> None:
        super().__init__()
        self.name = name
        self.args = args
        self.parent = parent
        self._get_libdoc_coroutine = get_libdoc_coroutine
        self.references: weakref.WeakSet[Any] = weakref.WeakSet()
        self.file_watchers: List[FileWatcherEntry] = []
        self._lib_doc: Optional[LibraryDoc] = None
        self._lock = asyncio.Lock()
        self._loop = asyncio.get_event_loop()
        self.ignore_reference = ignore_reference

    def __del__(self) -> None:
        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.invalidate(), self._loop)

    def __repr__(self) -> str:
        return (
            f"{type(self).__qualname__}(name={repr(self.name)}, "
            f"args={repr(self.args)}, file_watchers={repr(self.file_watchers)}, id={repr(id(self))}"
        )

    async def check_file_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]:
        async with self._lock:
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
                            path_is_relative_to(path, Path(e).absolute())
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
                        and any(path_is_relative_to(path, Path(e).absolute()) for e in self._lib_doc.python_path)
                    )
                ):
                    await self._invalidate()

                    return change.type

            return None

    async def _update(self) -> None:
        self._lib_doc = await self._get_libdoc_coroutine()

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
                await self.parent.parent_protocol.workspace.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [
                        str(Path(location).absolute().joinpath("**"))
                        for location in self._lib_doc.module_spec.submodule_search_locations
                    ],
                )
            )

            if source_or_origin is not None and Path(source_or_origin).parent in [
                Path(loc).absolute() for loc in self._lib_doc.module_spec.submodule_search_locations
            ]:
                return

        # we are a file, so put the parent path to filewatchers
        if source_or_origin is not None:
            self.file_watchers.append(
                await self.parent.parent_protocol.workspace.add_file_watchers(
                    self.parent.did_change_watched_files, [str(Path(source_or_origin).parent.joinpath("**"))]
                )
            )

            return

        # we are not found, so put the pythonpath to filewatchers
        if self._lib_doc.python_path is not None:
            self.file_watchers.append(
                await self.parent.parent_protocol.workspace.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(Path(s).joinpath("**")) for s in self._lib_doc.python_path],
                )
            )

    async def invalidate(self) -> None:
        async with self._lock:
            await self._invalidate()

    async def _invalidate(self) -> None:
        if self._lib_doc is None and len(self.file_watchers) == 0:
            return

        await self._remove_file_watcher()
        self._lib_doc = None

    async def _remove_file_watcher(self) -> None:
        if self.file_watchers is not None:
            for watcher in self.file_watchers:
                await self.parent.parent_protocol.workspace.remove_file_watcher_entry(watcher)
        self.file_watchers = []

    async def is_valid(self) -> bool:
        async with self._lock:
            return self._lib_doc is not None

    async def get_libdoc(self) -> LibraryDoc:
        async with self._lock:
            if self._lib_doc is None:
                await self._update()

            assert self._lib_doc is not None

            return self._lib_doc


@dataclass()
class _ResourcesEntryKey:
    name: str

    def __hash__(self) -> int:
        return hash(self.name)


class _ResourcesEntry:
    def __init__(
        self,
        name: str,
        parent: ImportsManager,
        get_document_coroutine: Callable[[], Coroutine[Any, Any, TextDocument]],
    ) -> None:
        super().__init__()
        self.name = name
        self.parent = parent
        self._get_document_coroutine = get_document_coroutine
        self.references: weakref.WeakSet[Any] = weakref.WeakSet()
        self.file_watchers: List[FileWatcherEntry] = []
        self._document: Optional[TextDocument] = None
        self._lock = asyncio.Lock()
        self._loop = asyncio.get_event_loop()

    def __del__(self) -> None:
        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.invalidate(), self._loop)

    def __repr__(self) -> str:
        return (
            f"{type(self).__qualname__}(name={repr(self.name)}, "
            f"file_watchers={repr(self.file_watchers)}, id={repr(id(self))}"
        )

    async def check_file_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]:
        async with self._lock:
            if self._document is None or self._document.version is None:
                return None

            for change in changes:
                uri = Uri(change.uri)
                if uri.scheme != "file":
                    continue

                path = uri.to_path()
                if (
                    self._document is not None
                    and ((path.resolve() == self._document.uri.to_path().resolve()))
                    or self._document is None
                ):
                    await self._invalidate()

                    return change.type

            return None

    def __close_document(self, document: TextDocument) -> None:
        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.parent.parent_protocol.documents.close_document(document), self._loop)
        else:
            del document

    async def _update(self) -> None:
        self._document = await self._get_document_coroutine()

        for r in self.references:
            self._document.references.add(r)

            weakref.finalize(r, self.__close_document, self._document)

        if self._document.version is None:
            self.file_watchers.append(
                await self.parent.parent_protocol.workspace.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(self._document.uri.to_path())],
                )
            )

    async def invalidate(self) -> None:
        async with self._lock:
            await self._invalidate()

    async def _invalidate(self) -> None:
        if self._document is None and len(self.file_watchers) == 0:
            return

        await self._remove_file_watcher()

        self._document = None

    async def _remove_file_watcher(self) -> None:
        if self.file_watchers is not None:
            for watcher in self.file_watchers:
                await self.parent.parent_protocol.workspace.remove_file_watcher_entry(watcher)
        self.file_watchers = []

    async def is_valid(self) -> bool:
        async with self._lock:
            return self._document is not None

    async def get_document(self) -> TextDocument:
        async with self._lock:
            if self._document is None:
                await self._update()

            assert self._document is not None

            return self._document

    async def get_namespace(self) -> Namespace:
        return await self.parent.parent_protocol.documents_cache.get_resource_namespace(await self.get_document())

    async def get_libdoc(self) -> LibraryDoc:
        return await (
            await self.parent.parent_protocol.documents_cache.get_resource_namespace(await self.get_document())
        ).get_library_doc()


def _shutdown_process_pool(pool: ProcessPoolExecutor) -> None:
    pool.shutdown(True)


# we need this, because ProcessPoolExecutor is not correctly initialized if asyncio is reading from stdin
def _init_process_pool() -> ProcessPoolExecutor:
    import atexit

    result = ProcessPoolExecutor(max_workers=PROCESS_POOL_MAX_WORKERS, initializer=init_pool)

    try:
        result.submit(dummy_first_run_pool).result(5)
    except BaseException:
        pass

    atexit.register(_shutdown_process_pool, result)
    return result


class ImportsManager:
    _logger = LoggingDescriptor()

    process_pool = _init_process_pool()

    def __init__(
        self, parent_protocol: RobotLanguageServerProtocol, folder: Uri, config: Optional[RobotConfig]
    ) -> None:
        super().__init__()
        self.parent_protocol = parent_protocol
        self.folder = folder
        self.config = config
        self._libaries_lock = asyncio.Lock()
        self._libaries: OrderedDict[_LibrariesEntryKey, _LibrariesEntry] = OrderedDict()
        self._resources_lock = asyncio.Lock()
        self._resources: OrderedDict[_ResourcesEntryKey, _ResourcesEntry] = OrderedDict()
        self.file_watchers: List[FileWatcherEntry] = []
        self._loop = asyncio.get_event_loop()
        self.parent_protocol.documents.did_open.add(self.resource_document_changed)
        self.parent_protocol.documents.did_change.add(self.resource_document_changed)
        self.parent_protocol.documents.did_close.add(self.resource_document_changed)
        self.parent_protocol.documents.did_save.add(self.resource_document_changed)

    @async_tasking_event
    async def libraries_changed(sender, params: List[LibraryDoc]) -> None:
        ...

    @async_tasking_event
    async def resources_changed(sender, params: List[LibraryDoc]) -> None:
        ...

    async def resource_document_changed(self, sender: Any, document: TextDocument) -> None:
        resource_changed: List[LibraryDoc] = []

        async with self._resources_lock:
            for r_entry in self._resources.values():
                lib_doc: Optional[LibraryDoc] = None
                try:
                    if not await r_entry.is_valid():
                        continue

                    uri = (await r_entry.get_document()).uri
                    result = uri == document.uri
                    if result:
                        lib_doc = await r_entry.get_libdoc()
                        await r_entry.invalidate()

                except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    result = True

                if result and lib_doc is not None:
                    resource_changed.append(lib_doc)

        if resource_changed:
            await self.resources_changed(self, resource_changed)

    async def did_change_watched_files(self, sender: Any, changes: List[FileEvent]) -> None:
        libraries_changed: List[LibraryDoc] = []
        resource_changed: List[LibraryDoc] = []

        lib_doc: Optional[LibraryDoc]

        async with self._libaries_lock:
            for l_entry in self._libaries.values():
                lib_doc = None
                if await l_entry.is_valid():
                    lib_doc = await l_entry.get_libdoc()
                result = await l_entry.check_file_changed(changes)
                if result is not None and lib_doc is not None:
                    libraries_changed.append(lib_doc)

        async with self._resources_lock:
            for r_entry in self._resources.values():
                lib_doc = None
                if await r_entry.is_valid():
                    lib_doc = await r_entry.get_libdoc()
                result = await r_entry.check_file_changed(changes)
                if result is not None and lib_doc is not None:
                    resource_changed.append(await r_entry.get_libdoc())

        if libraries_changed:
            await self.libraries_changed(self, libraries_changed)

        if resource_changed:
            await self.resources_changed(self, resource_changed)

    def __remove_library_entry(self, entry_key: _LibrariesEntryKey, entry: _LibrariesEntry, now: bool = False) -> None:
        async def threadsafe_remove(k: _LibrariesEntryKey, e: _LibrariesEntry, n: bool) -> None:
            if n or len(e.references) == 0:
                self._logger.debug(lambda: f"Remove Library Entry {k}")
                async with self._libaries_lock:
                    await entry.invalidate()
                    self._libaries.pop(k, None)

        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(threadsafe_remove(entry_key, entry, now), loop=self._loop)

    def __remove_resource_entry(self, entry_key: _ResourcesEntryKey, entry: _ResourcesEntry) -> None:
        async def threadsafe_remove(k: _ResourcesEntryKey, e: _ResourcesEntry) -> None:
            if len(e.references) == 0:
                async with self._resources_lock:
                    if k in self._resources:
                        self._logger.debug(lambda: f"Remove Resource Entry {k}")
                        await entry.invalidate()
                        self._resources.pop(k, None)

        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(threadsafe_remove(entry_key, entry), loop=self._loop)

    @_logger.call
    async def find_library(self, name: str, base_dir: str) -> str:
        return await asyncio.wait_for(
            self._loop.run_in_executor(
                self.process_pool,
                find_library,
                name,
                str(self.folder.to_path()),
                base_dir,
                self.config.python_path if self.config is not None else None,
                self.config.env if self.config is not None else None,
                self.config.variables if self.config is not None else None,
            ),
            FIND_FILE_TIME_OUT,
        )

    @_logger.call
    async def get_libdoc_for_library_import(
        self, name: str, args: Tuple[Any, ...], base_dir: str, sentinel: Any = None
    ) -> LibraryDoc:

        source = await self.find_library(name, base_dir)

        async def _get_libdoc() -> LibraryDoc:
            self._logger.debug(lambda: f"Load Library {source}{repr(args)}")

            result = await asyncio.wait_for(
                self._loop.run_in_executor(
                    self.process_pool,
                    get_library_doc,
                    name,
                    args,
                    str(self.folder.to_path()),
                    base_dir,
                    self.config.python_path if self.config is not None else None,
                    self.config.env if self.config is not None else None,
                    self.config.variables if self.config is not None else None,
                ),
                LOAD_LIBRARY_TIME_OUT,
            )

            if result.stdout:
                self._logger.warning(lambda: f"stdout captured at loading library {name}{repr(args)}:\n{result.stdout}")
            return result

        async with self._libaries_lock:

            entry_key = _LibrariesEntryKey(source, args)

            if entry_key not in self._libaries:
                self._libaries[entry_key] = entry = _LibrariesEntry(
                    name, args, self, _get_libdoc, ignore_reference=sentinel is None
                )

            entry = self._libaries[entry_key]

            if not entry.ignore_reference and sentinel is not None and sentinel not in entry.references:
                entry.references.add(sentinel)
                weakref.finalize(sentinel, self.__remove_library_entry, entry_key, entry)

            return await entry.get_libdoc()

    @_logger.call
    async def get_libdoc_from_model(
        self, model: ast.AST, source: str, model_type: str = "RESOURCE", scope: str = "GLOBAL"
    ) -> LibraryDoc:

        from robot.errors import DataError
        from robot.libdocpkg.robotbuilder import KeywordDocBuilder
        from robot.running.builder.transformers import ResourceBuilder
        from robot.running.model import ResourceFile
        from robot.running.usererrorhandler import UserErrorHandler
        from robot.running.userkeyword import UserLibrary

        from ..utils.ast import HasError, HasErrors

        errors: List[Error] = []

        async for node in walk(model):
            error = node.error if isinstance(node, HasError) else None
            if error is not None:
                errors.append(Error(message=error, type_name="ModelError", source=source, line_no=node.lineno))
            node_errors = node.errors if isinstance(node, HasErrors) else None
            if node_errors is not None:
                for e in node_errors:
                    errors.append(Error(message=e, type_name="ModelError", source=source, line_no=node.lineno))

        res = ResourceFile(source=source)

        ResourceBuilder(res).visit(model)

        class MyUserLibrary(UserLibrary):  # type: ignore
            current_kw: Any = None

            def _log_creating_failed(self, handler: UserErrorHandler, error: BaseException) -> None:
                err = Error(
                    message=f"Creating keyword '{handler.name}' failed: {str(error)}",
                    type_name=type(error).__qualname__,
                    source=self.current_kw.source if self.current_kw is not None else None,
                    line_no=self.current_kw.lineno if self.current_kw is not None else None,
                )
                errors.append(err)

            def _create_handler(self, kw: Any) -> Any:
                self.current_kw = kw
                try:
                    handler = super()._create_handler(kw)
                    setattr(handler, "errors", None)
                except DataError as e:
                    err = Error(
                        message=str(e),
                        type_name=type(e).__qualname__,
                        source=kw.source,
                        line_no=kw.lineno,
                    )
                    errors.append(err)

                    handler = UserErrorHandler(e, kw.name, self.name)
                    handler.source = kw.source
                    handler.lineno = kw.lineno

                    setattr(handler, "errors", [err])

                return handler

        lib = MyUserLibrary(res)

        libdoc = LibraryDoc(
            name=lib.name or "",
            doc=lib.doc,
            type=model_type,
            scope=scope,
            source=source,
            line_no=1,
            errors=errors,
        )

        libdoc.keywords = KeywordStore(
            source=libdoc.name,
            source_type=libdoc.type,
            keywords={
                kw[0].name: KeywordDoc(
                    name=kw[0].name,
                    args=tuple(KeywordArgumentDoc.from_robot(a) for a in kw[0].args),
                    doc=kw[0].doc,
                    tags=tuple(kw[0].tags),
                    source=kw[0].source,
                    line_no=kw[0].lineno,
                    libname=libdoc.name,
                    is_embedded=is_embedded_keyword(kw[0].name),
                    errors=getattr(kw[1], "errors") if hasattr(kw[1], "errors") else None,
                    is_error_handler=isinstance(kw[1], UserErrorHandler),
                    error_handler_message=str(cast(UserErrorHandler, kw[1]).error)
                    if isinstance(kw[1], UserErrorHandler)
                    else None,
                )
                for kw in [
                    (KeywordDocBuilder(resource=model_type == "RESOURCE").build_keyword(lw), lw) for lw in lib.handlers
                ]
            },
        )

        return libdoc

    @_logger.call
    async def find_file(self, name: str, base_dir: str, file_type: str = "Resource") -> str:
        return await asyncio.wait_for(
            self._loop.run_in_executor(
                self.process_pool,
                find_file,
                name,
                str(self.folder.to_path()),
                base_dir,
                self.config.python_path if self.config is not None else None,
                self.config.env if self.config is not None else None,
                self.config.variables if self.config is not None else None,
                file_type,
            ),
            FIND_FILE_TIME_OUT,
        )

    @_logger.call
    async def _get_entry_for_resource_import(self, name: str, base_dir: str, sentinel: Any = None) -> _ResourcesEntry:
        source = await self.find_file(name, base_dir, "Resource")

        async def _get_document() -> TextDocument:
            from robot.utils import FileReader

            self._logger.debug(lambda: f"Load resource {name} from source {source}")

            source_path = Path(source).resolve()
            extension = source_path.suffix
            if extension.lower() not in RESOURCE_EXTENSIONS:
                raise ImportError(
                    f"Invalid resource file extension '{extension}'. "
                    f"Supported extensions are {', '.join(repr(s) for s in RESOURCE_EXTENSIONS)}."
                )

            source_uri = DocumentUri(Uri.from_path(source_path).normalized())

            result = self.parent_protocol.documents.get(source_uri, None)
            if result is not None:
                return result

            with FileReader(source_path) as reader:
                text = str(reader.read())

            return self.parent_protocol.documents.append_document(
                document_uri=source_uri, language_id="robotframework", text=text
            )

        async with self._resources_lock:
            entry_key = _ResourcesEntryKey(source)

            if entry_key not in self._resources:
                self._resources[entry_key] = entry = _ResourcesEntry(name, self, _get_document)

            entry = self._resources[entry_key]

            if sentinel is not None and sentinel not in entry.references:
                entry.references.add(sentinel)
                weakref.finalize(sentinel, self.__remove_resource_entry, entry_key, entry)

            return entry

    @_logger.call
    async def get_document_for_resource_import(self, name: str, base_dir: str, sentinel: Any = None) -> TextDocument:
        entry = await self._get_entry_for_resource_import(name, base_dir, sentinel)

        return await entry.get_document()

    async def get_namespace_for_resource_import(self, name: str, base_dir: str, sentinel: Any = None) -> "Namespace":
        entry = await self._get_entry_for_resource_import(name, base_dir, sentinel)

        return await entry.get_namespace()

    async def get_libdoc_for_resource_import(self, name: str, base_dir: str, sentinel: Any = None) -> LibraryDoc:
        entry = await self._get_entry_for_resource_import(name, base_dir, sentinel)

        return await entry.get_libdoc()

    async def complete_library_import(self, name: Optional[str], base_dir: str = ".") -> Optional[List[CompleteResult]]:
        result = await asyncio.wait_for(
            self._loop.run_in_executor(
                self.process_pool,
                complete_library_import,
                name,
                str(self.folder.to_path()),
                base_dir,
                self.config.python_path if self.config is not None else None,
                self.config.env if self.config is not None else None,
                self.config.variables if self.config is not None else None,
            ),
            COMPLETE_LIBRARY_IMPORT_TIME_OUT,
        )

        return result

    async def complete_resource_import(
        self, name: Optional[str], base_dir: str = "."
    ) -> Optional[List[CompleteResult]]:
        result = await asyncio.wait_for(
            self._loop.run_in_executor(
                self.process_pool,
                complete_resource_import,
                name,
                str(self.folder.to_path()),
                base_dir,
                self.config.python_path if self.config is not None else None,
                self.config.env if self.config is not None else None,
                self.config.variables if self.config is not None else None,
            ),
            COMPLETE_RESOURCE_IMPORT_TIME_OUT,
        )

        return result

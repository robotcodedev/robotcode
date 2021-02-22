from __future__ import annotations

import ast
import asyncio
import weakref
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, NamedTuple, Optional, Tuple

from ...language_server.parts.workspace import FileWatcherEntry, Workspace
from ...language_server.types import FileChangeType, FileEvent
from ...utils.async_event import async_tasking_event
from ...utils.logging import LoggingDescriptor
from ...utils.uri import Uri
from ..configuration import RobotConfig
from ..utils.async_visitor import walk
from .library_doc import (
    Error,
    KeywordDoc,
    KeywordStore,
    LibraryDoc,
    find_file,
    get_library_doc,
    init_pool,
    is_embedded_keyword,
)

DEFAULT_LIBRARIES = ("BuiltIn", "Reserved", "Easter")


@dataclass()
class _EntryKey:
    name: str
    args: Tuple[Any, ...]

    def __hash__(self) -> int:
        return hash((self.name, self.args))


class _Entry:
    def __init__(
        self,
        name: str,
        args: Tuple[Any, ...],
        parent: LibraryManager,
        load_doc_coroutine: Callable[[], Coroutine[Any, Any, LibraryDoc]],
    ) -> None:
        super().__init__()
        self.name = name
        self.args = args
        self.parent = parent
        self.load_doc_coroutine = load_doc_coroutine
        self.references: weakref.WeakSet[Any] = weakref.WeakSet()
        self.file_watchers: List[FileWatcherEntry] = []
        self._doc: Optional[LibraryDoc] = None
        self._lock = asyncio.Lock()
        self._loop = asyncio.get_event_loop()

    def __del__(self) -> None:
        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.invalidate(), self._loop)

    def __repr__(self) -> str:
        return (
            f"{type(self).__qualname__}(name={repr(self.name)}, "
            f"args={repr(self.args)}, file_watchers={repr(self.file_watchers)}, id={repr(id(self))}"
        )

    async def check_changed(self, changes: List[FileEvent]) -> Optional[FileChangeType]:
        async with self._lock:
            if self._doc is None:
                return None

            for change in changes:
                uri = Uri(change.uri)
                if uri.scheme != "file":
                    continue

                path = uri.to_path()
                if self._doc is not None and (
                    (
                        self._doc.module_spec is not None
                        and self._doc.module_spec.submodule_search_locations is not None
                        and any(
                            path.is_relative_to(Path(e).absolute())
                            for e in self._doc.module_spec.submodule_search_locations
                        )
                    )
                    or (
                        self._doc.module_spec is not None
                        and self._doc.module_spec.origin is not None
                        and path.is_relative_to(Path(self._doc.module_spec.origin).parent)
                    )
                    or (self._doc.source and path.is_relative_to(Path(self._doc.source).parent))
                    or (
                        self._doc.module_spec is None
                        and not self._doc.source
                        and self._doc.python_path
                        and any(path.is_relative_to(Path(e).absolute()) for e in self._doc.python_path)
                    )
                ):
                    await self._invalidate()

                    return change.type

            return None

    async def _update(self) -> None:
        self._doc = await self.load_doc_coroutine()

        source_or_origin = (
            self._doc.source
            if self._doc.source is not None
            else self._doc.module_spec.origin
            if self._doc.module_spec is not None
            else None
        )

        # we are a module, so add the module path into file watchers
        if self._doc.module_spec is not None and self._doc.module_spec.submodule_search_locations is not None:
            self.file_watchers.append(
                await self.parent.workspace.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [
                        str(Path(location).absolute().joinpath("**"))
                        for location in self._doc.module_spec.submodule_search_locations
                    ],
                )
            )

            if source_or_origin is not None and Path(source_or_origin).parent in [
                Path(loc).absolute() for loc in self._doc.module_spec.submodule_search_locations
            ]:
                return

        # we are a file, so put the parent path to filewatchers
        if source_or_origin is not None:
            self.file_watchers.append(
                await self.parent.workspace.add_file_watchers(
                    self.parent.did_change_watched_files, [str(Path(source_or_origin).parent.joinpath("**"))]
                )
            )

            return

        # we are not found so, put the pythonpath to filewatchers
        if self._doc.python_path is not None:
            self.file_watchers.append(
                await self.parent.workspace.add_file_watchers(
                    self.parent.did_change_watched_files,
                    [str(Path(s).joinpath("**")) for s in self._doc.python_path],
                )
            )

    async def invalidate(self) -> None:
        async with self._lock:
            await self._invalidate()

    async def _invalidate(self) -> None:
        if self._doc is None and len(self.file_watchers) == 0:
            return

        await self._remove_file_watcher()
        self._doc = None

    async def _remove_file_watcher(self) -> None:
        if self.file_watchers is not None:
            for watcher in self.file_watchers:
                await self.parent.workspace.remove_file_watcher_entry(watcher)
        self.file_watchers = []

    async def get_doc(self) -> LibraryDoc:
        async with self._lock:
            if self._doc is None:
                await self._update()

            assert self._doc is not None

            return self._doc


# we need this, because ProcessPoolExecutor is not correctly initialized if asyncio is reading from stdin
def _init_process_pool() -> ProcessPoolExecutor:
    result = ProcessPoolExecutor()
    try:
        result.submit(init_pool).result(5)
    except BaseException:
        pass
    return result


class LibraryChangedParams(NamedTuple):
    name: str
    args: Tuple[Any, ...]
    type: FileChangeType


class LibraryManager:
    _logger = LoggingDescriptor()

    process_pool = _init_process_pool()

    def __init__(self, workspace: Workspace, folder: Uri, config: Optional[RobotConfig]) -> None:
        super().__init__()
        self.workspace = workspace
        self.folder = folder
        self.config = config
        self._libaries_lock = asyncio.Lock()
        self._libaries: OrderedDict[_EntryKey, _Entry] = OrderedDict()
        self.file_watchers: List[FileWatcherEntry] = []
        self._loop = asyncio.get_event_loop()

    @async_tasking_event
    async def libraries_changed(sender, params: List[LibraryChangedParams]) -> None:
        ...

    async def did_change_watched_files(self, sender: Any, changes: List[FileEvent]) -> None:
        changed: Dict[_EntryKey, FileChangeType] = {}

        for key, entry in self._libaries.items():
            result = await entry.check_changed(changes)
            if result is not None:
                changed[key] = result

        await self.libraries_changed(self, [LibraryChangedParams(k.name, k.args, v) for k, v in changed.items()])

    def __remove_entry(self, entry_key: _EntryKey, entry: _Entry, now: bool = False) -> None:
        async def threadsafe_remove(k: _EntryKey, e: _Entry, n: bool) -> None:
            if n or len(e.references) == 0:
                self._logger.debug(lambda: f"remove library {k.name}{repr(k.args)}")
                async with self._libaries_lock:
                    await entry.invalidate()
                    self._libaries.pop(k, None)

        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(threadsafe_remove(entry_key, entry, now), loop=self._loop)

    @_logger.call
    async def get_doc_from_library(
        self, sentinel: Any, name: str, args: Tuple[Any, ...] = (), base_dir: str = "."
    ) -> LibraryDoc:
        async with self._libaries_lock:
            entry_key = _EntryKey(name, args)

            if entry_key not in self._libaries:

                async def _load_libdoc() -> LibraryDoc:
                    self._logger.debug(lambda: f"load/reload library {name}{repr(args)}")

                    result = await asyncio.wait_for(
                        self._loop.run_in_executor(
                            self.process_pool,
                            get_library_doc,
                            name,
                            args,
                            str(self.folder.to_path()),
                            base_dir,
                            self.config.pythonpath if self.config is not None else None,
                        ),
                        30,
                    )

                    self._logger.debug(
                        lambda: f"loaded library {result.name} "
                        f"from source {repr(result.source)} and module spec {repr(result.module_spec)}"
                    )

                    return result

                self._libaries[entry_key] = entry = _Entry(name, args, self, _load_libdoc)

        entry = self._libaries[entry_key]

        if sentinel is not None and sentinel not in entry.references:
            entry.references.add(sentinel)
            weakref.finalize(sentinel, self.__remove_entry, entry_key, entry)

        return await entry.get_doc()

    @_logger.call
    async def get_doc_from_model(
        self, model: ast.AST, source: str, model_type: str = "RESOURCE", scope: str = "GLOBAL"
    ) -> LibraryDoc:

        from robot.libdocpkg.robotbuilder import KeywordDocBuilder
        from robot.running.builder.transformers import ResourceBuilder
        from robot.running.model import ResourceFile
        from robot.running.usererrorhandler import UserErrorHandler
        from robot.running.userkeyword import UserLibrary
        from robot.errors import DataError

        errors: List[Error] = []

        async for node in walk(model):
            error = getattr(node, "error", None)
            if error is not None:
                errors.append(Error(message=error, type_name="ModelError", source=source, line_no=node.lineno))
            node_error = getattr(node, "errors", None)
            if node_error is not None:
                for e in node_error:
                    errors.append(Error(message=e, type_name="ModelError", source=source, line_no=node.lineno))

        res = ResourceFile(source=source)

        ResourceBuilder(res).visit(model)

        class MyUserLibrary(UserLibrary):  # type: ignore
            def _log_creating_failed(self, handler: UserErrorHandler, error: BaseException) -> None:
                pass

            def _create_handler(self, kw: Any) -> Any:
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
            name=lib.name or "", doc=lib.doc, type=model_type, scope=scope, source=source, line_no=1, errors=errors
        )

        libdoc.keywords = KeywordStore(
            keywords={
                kw[0].name: KeywordDoc(
                    name=kw[0].name,
                    args=tuple(str(a) for a in kw[0].args),
                    doc=kw[0].doc,
                    tags=tuple(kw[0].tags),
                    source=kw[0].source,
                    line_no=kw[0].lineno,
                    is_embedded=is_embedded_keyword(kw[0].name),
                    errors=getattr(kw[1], "errors") if hasattr(kw[1], "errors") else None,
                )
                for kw in [
                    (KeywordDocBuilder(resource=model_type == "RESOURCE").build_keyword(lw), lw) for lw in lib.handlers
                ]
            }
        )

        return libdoc

    @_logger.call
    async def find_file(self, name: str, base_dir: str = ".", file_type: str = "Resource") -> str:
        return await asyncio.wait_for(
            self._loop.run_in_executor(
                self.process_pool,
                find_file,
                name,
                str(self.folder.to_path()),
                base_dir,
                self.config.pythonpath if self.config is not None else None,
                file_type,
            ),
            30,
        )

import ast
import asyncio
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

import multiprocessing

from ...language_server.parts.workspace import FileWatcherEntry, Workspace
from ...language_server.types import FileChangeType, FileEvent
from ...utils.async_event import async_tasking_event
from ...utils.uri import Uri
from ..configuration import RobotConfig
from ..utils.async_visitor import walk
from .library_doc import Error, KeywordDoc, KeywordStore, LibraryDoc, find_file, get_library_doc

DEFAULT_LIBRARIES = ("BuiltIn", "Reserved", "Easter")


@dataclass()
class _EntryKey:
    name: str
    args: Tuple[Any, ...]

    def __hash__(self) -> int:
        return hash((self.name, self.args))


class _Entry:
    def __init__(self, doc: LibraryDoc, file_watcher: Optional[FileWatcherEntry] = None) -> None:
        super().__init__()
        self.doc = doc
        self.references: weakref.WeakSet[Any] = weakref.WeakSet()
        self.file_watcher = file_watcher


class LibraryManager:
    _pool = multiprocessing.Pool()

    def __init__(self, workspace: Workspace, folder: Uri, config: Optional[RobotConfig]) -> None:
        super().__init__()
        self.workspace = workspace
        self.folder = folder
        self.config = config
        self._libaries_lock = asyncio.Lock()
        self._libaries: OrderedDict[_EntryKey, _Entry] = OrderedDict()
        self._loop = asyncio.get_event_loop()

    @property
    def pool(self) -> multiprocessing.pool.Pool:
        return self._pool

    def __remove_entry(self, entry_key: _EntryKey, entry: _Entry) -> None:
        async def check(k: _EntryKey, e: _Entry) -> None:
            async with self._libaries_lock:
                self._libaries.pop(k, None)

            if e is not None and e.file_watcher is not None:
                await self.workspace.remove_file_watcher(e.file_watcher)

        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(check(entry_key, entry), loop=self._loop)

    @async_tasking_event
    async def libraries_removed(sender, library_sources: List[str]) -> None:
        ...

    async def did_change_watched_files(self, sender: Any, changes: List[FileEvent]) -> None:
        to_remove: List[Tuple[_EntryKey, _Entry]] = []
        for change in changes:
            if change.type in [FileChangeType.CHANGED, FileChangeType.DELETED]:
                async with self._libaries_lock:
                    to_remove += [
                        (k, v)
                        for k, v in self._libaries.items()
                        if v.doc.source is not None and Path(v.doc.source) == Uri(change.uri).to_path()
                    ]

        if to_remove:
            async with self._libaries_lock:
                for r in to_remove:
                    self.__remove_entry(*r)

            await self.libraries_removed(self, [entry[1].doc.source for entry in to_remove])

    async def get_doc_from_library(
        self, sentinel: Any, name: str, args: Tuple[Any, ...] = (), base_dir: str = "."
    ) -> LibraryDoc:
        entry_key = _EntryKey(name, args)

        async with self._libaries_lock:
            if entry_key not in self._libaries:
                lib_doc = self.pool.apply_async(
                    get_library_doc,
                    # aiomultiprocess.Worker(
                    #     target=get_library_doc,
                    args=(
                        name,
                        args,
                        self.folder.to_path_str(),
                        base_dir,
                        self.config.pythonpath if self.config is not None else None,
                    ),
                ).get(100)

                if lib_doc.source is not None:
                    self._libaries[entry_key] = _Entry(
                        lib_doc, await self.workspace.add_file_watcher(self.did_change_watched_files, lib_doc.source)
                    )

            entry = self._libaries[entry_key]

            if sentinel is not None:
                entry.references.add(sentinel)
                weakref.finalize(sentinel, self.__remove_entry, entry_key, entry)

            return entry.doc

    async def get_doc_from_model(
        self, model: ast.AST, source: str, model_type: str = "RESOURCE", scope: str = "GLOBAL"
    ) -> LibraryDoc:

        from robot.libdocpkg.robotbuilder import KeywordDocBuilder
        from robot.running.builder.transformers import ResourceBuilder
        from robot.running.model import ResourceFile
        from robot.running.usererrorhandler import UserErrorHandler
        from robot.running.userkeyword import UserLibrary

        errors: List[Error] = []

        async for node in walk(model):
            error = getattr(node, "error", None)
            if error is not None:
                errors.append(Error(f"Error in file '{source}' on line {node.lineno}: {error}", "ModelError"))
            node_error = getattr(node, "errors", None)
            if node_error is not None:
                for e in node_error:
                    errors.append(Error(f"Error in file '{source}' on line {node.lineno}: {e}", "ModelError"))

        res = ResourceFile(source=source)

        ResourceBuilder(res).visit(model)

        class MyUserLibrary(UserLibrary):  # type: ignore
            def _log_creating_failed(self, handler: UserErrorHandler, error: BaseException) -> None:
                errors.append(
                    Error(
                        "Error in %s '%s': Creating keyword '%s' failed: %s"
                        % (self.source_type.lower(), self.source, handler.name, str(error)),
                        type(error).__qualname__,
                    )
                )

        lib = MyUserLibrary(res)

        libdoc = LibraryDoc(
            name=lib.name or "", doc=lib.doc, type=model_type, scope=scope, source=source, line_no=1, errors=errors
        )

        libdoc.keywords = KeywordStore(
            {
                kw.name: KeywordDoc(
                    libdoc,
                    name=kw.name,
                    args=tuple(str(a) for a in kw.args),
                    doc=kw.doc,
                    tags=tuple(kw.tags),
                    source=kw.source,
                    line_no=kw.lineno,
                )
                for kw in KeywordDocBuilder().build_keywords(lib)
            }
        )

        libdoc.keywords = KeywordStore(
            {
                kw.name: KeywordDoc(
                    libdoc,
                    name=kw.name,
                    args=tuple(str(a) for a in kw.args),
                    doc=kw.doc,
                    tags=tuple(kw.tags),
                    source=kw.source,
                    line_no=kw.lineno,
                )
                for kw in KeywordDocBuilder(resource=model_type == "RESOURCE").build_keywords(lib)
            }
        )

        return libdoc

    async def find_file(self, name: str, base_dir: str = ".", file_type: str = "Resource") -> str:
        return self.pool.apply_async(
            find_file,
            # aiomultiprocess.Worker(
            #     target=find_file,
            args=(
                name,
                self.folder.to_path_str(),
                base_dir,
                self.config.pythonpath if self.config is not None else None,
                file_type,
            ),
        ).get(10)

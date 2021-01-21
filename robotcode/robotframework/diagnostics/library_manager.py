import ast
import asyncio
import multiprocessing
import multiprocessing.pool
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from ...utils.uri import Uri
from ..configuration import RobotConfig
from ..utils.async_visitor import walk
from .library_doc import Error, KeywordDoc, LibraryDoc, find_file, get_library_doc, KeywordStore

DEFAULT_LIBRARIES = ("BuiltIn", "Reserved", "Easter")


@dataclass()
class _EntryKey:
    name: str
    args: Tuple[Any, ...]

    def __hash__(self) -> int:
        return hash((self.name, self.args))


class _Entry:
    def __init__(self, doc: LibraryDoc) -> None:
        super().__init__()
        self.doc = doc
        self.references: weakref.WeakSet[Any] = weakref.WeakSet()


class LibraryManager:

    __pool: multiprocessing.pool.Pool = multiprocessing.Pool()

    @classmethod
    def get_global_pool(cls) -> multiprocessing.pool.Pool:
        return cls.__pool

    def __init__(self, folder: Uri, config: Optional[RobotConfig]) -> None:
        super().__init__()
        self.folder = folder
        self.config = config
        self._libaries_lock = asyncio.Lock()
        self._libaries: OrderedDict[_EntryKey, _Entry] = OrderedDict()
        self.loop = asyncio.get_event_loop()

    @property
    def pool(self) -> multiprocessing.pool.Pool:
        return self.get_global_pool()

    def __check_entry(self, entry_key: _EntryKey) -> None:
        async def check() -> None:
            async with self._libaries_lock:
                entry = self._libaries.get(entry_key, None)
                if entry is not None:
                    if len(entry.references) == 0:
                        self._libaries.pop(entry_key, None)

        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(check(), loop=self.loop)

    async def get_doc_from_library(
        self, sentinel: Any, name: str, args: Tuple[Any, ...] = (), base_dir: str = "."
    ) -> LibraryDoc:
        entry_key = _EntryKey(name, args)

        async with self._libaries_lock:
            if entry_key not in self._libaries:
                self._libaries[entry_key] = _Entry(
                    self.pool.apply_async(
                        get_library_doc,
                        args=(
                            name,
                            args,
                            self.folder.to_path_str(),
                            base_dir,
                            self.config.pythonpath if self.config is not None else None,
                        ),
                    ).get(100)
                )

            entry = self._libaries[entry_key]

            if sentinel is not None:
                entry.references.add(sentinel)
                weakref.finalize(sentinel, self.__check_entry, entry_key)

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
                    args=tuple(kw.args),
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
                    args=tuple(kw.args),
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
            args=(
                name,
                self.folder.to_path_str(),
                base_dir,
                self.config.pythonpath if self.config is not None else None,
                file_type,
            ),
        ).get(10)

from __future__ import annotations

import ast
import asyncio
import io
import weakref
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
)

from ...language_server.parts.workspace import WorkspaceFolder

if TYPE_CHECKING:
    from robot.parsing.lexer import Token

from ...language_server.text_document import TextDocument
from ...utils.async_event import async_tasking_event
from ...utils.uri import Uri
from ..configuration import RobotConfig
from ..diagnostics.imports_manager import ImportsManager
from ..diagnostics.namespace import Namespace

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart

_TResult = TypeVar("_TResult")


class UnknownFileTypeError(Exception):
    pass


@dataclass
class _Entry:
    version: Optional[int]
    model: Optional[ast.AST] = None
    tokens: Optional[List[Any]] = None
    namespace: Optional[Namespace] = None


class DocumentsCache(RobotLanguageServerProtocolPart):
    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        self._lock = asyncio.Lock()
        self._entries: weakref.WeakKeyDictionary[TextDocument, _Entry] = weakref.WeakKeyDictionary()
        self._loop = asyncio.get_event_loop()

        self._imports_managers_lock = asyncio.Lock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None

    async def __get_entry(self, document: TextDocument, setter: Callable[[_Entry], Awaitable[_TResult]]) -> _TResult:
        async with self._lock:
            if document not in self._entries:
                self._entries[document] = _Entry(document.version)

            return await setter(self._entries[document])

    async def get_tokens(self, document: TextDocument) -> AsyncIterator["Token"]:
        for e in await self.__get_tokens(document):
            yield e

    async def __get_tokens(self, document: TextDocument) -> List[Any]:
        import robot.api

        async def get_tokens() -> AsyncIterator["Token"]:
            with io.StringIO(document.text) as content:
                path = document.uri.to_path()
                suffix = path.suffix.lower()

                if path.name == "__init__.robot":
                    for t in robot.api.get_init_tokens(content):
                        yield t
                elif suffix == ".robot":
                    for t in robot.api.get_tokens(content):
                        yield t
                elif suffix == ".resource":
                    for t in robot.api.get_resource_tokens(content):
                        yield t
                else:
                    raise UnknownFileTypeError(str(document.uri))

        async def setter(e: _Entry) -> List["Token"]:
            if e.tokens is None:
                e.tokens = [e async for e in get_tokens()]
            return e.tokens

        return await self.__get_entry(document, setter)

    async def get_model(self, document: TextDocument) -> ast.AST:
        async def setter(e: _Entry) -> ast.AST:
            if e.model is None:
                e.model = await self.__get_model(document)
            return e.model

        return await self.__get_entry(document, setter)

    async def __get_model(self, document: TextDocument) -> ast.AST:
        import robot.api

        with io.StringIO(document.text) as content:
            path = document.uri.to_path()
            suffix = path.suffix.lower()

            if path.name == "__init__.robot":
                return cast(ast.AST, robot.api.get_init_model(content))
            elif suffix in (".robot",):
                return cast(ast.AST, robot.api.get_model(content))
            elif suffix in (".resource", ".rst", ".rest"):
                return cast(ast.AST, robot.api.get_resource_model(content))
            else:
                raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

    async def get_namespace(self, document: TextDocument) -> Namespace:
        async def setter(e: _Entry) -> Namespace:
            if e.namespace is None:
                e.namespace, e.model = await self.__get_namespace(document, e.model)
            return e.namespace

        return await self.__get_entry(document, setter)

    @async_tasking_event
    async def namespace_invalidated(sender, document: TextDocument) -> None:
        ...

    async def __invalidate_namespace(self, document: TextDocument, namespace: Namespace) -> None:
        async def setter(e: _Entry) -> None:
            e.namespace = None

        await self.__get_entry(document, setter)
        await self.namespace_invalidated(self, document)

    async def __get_namespace(self, document: TextDocument, model: Optional[ast.AST]) -> Tuple[Namespace, ast.AST]:
        model = await self.__get_model(document) if model is None else model

        imports_manager = await self.get_imports_manager(document)

        def invalidate(namespace: Namespace) -> None:
            if self._loop.is_running():
                asyncio.ensure_future(self.__invalidate_namespace(document, namespace))

        return (
            Namespace(imports_manager, model, str(document.uri.to_path()), document.parent or document, invalidate),
            model,
        )

    @property
    def default_imports_manager(self) -> ImportsManager:
        if self._default_imports_manager is None:
            self._default_imports_manager = ImportsManager(
                self.parent, Uri(self.parent.workspace.root_uri or "."), RobotConfig(args=(), pythonpath=[])
            )
        return self._default_imports_manager

    async def get_imports_manager(self, document: TextDocument) -> ImportsManager:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return self.default_imports_manager

        async with self._imports_managers_lock:
            if folder not in self._imports_managers:
                config = await self.parent.workspace.get_configuration(RobotConfig, folder.uri)

                self._imports_managers[folder] = ImportsManager(self.parent, folder.uri, config)
            return self._imports_managers[folder]

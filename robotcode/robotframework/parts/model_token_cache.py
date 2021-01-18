import ast
import asyncio
import io
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple, TypeVar, cast

if TYPE_CHECKING:
    from robot.parsing.lexer import Token

from ...language_server.parts.protocol_part import LanguageServerProtocolPart
from ...language_server.protocol import LanguageServerProtocol
from ...language_server.text_document import TextDocument

from ..diagnostics.namespace import Namespace
from ..diagnostics.library_manager import LibraryManager
from ..configuration import RobotcodeConfig

_TResult = TypeVar("_TResult")


class UnknownFileTypeError(Exception):
    pass


@dataclass
class _Entry:
    version: int
    model: Optional[ast.AST] = None
    tokens: Optional[List[Any]] = None
    namespace: Optional[Namespace] = None


class ModelTokenCache(LanguageServerProtocolPart):
    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self._lock = asyncio.Lock()
        self._entries: Dict[Tuple[weakref.ref[TextDocument], int], _Entry] = {}
        self._loop = asyncio.get_event_loop()
        self._library_manager = LibraryManager()

    async def __get_entry(self, document: TextDocument, setter: Callable[[_Entry], Awaitable[_TResult]]) -> _TResult:
        version = document.version

        async def remove_safe(r: weakref.ref[TextDocument], v: int) -> None:
            async with self._lock:
                self._entries.pop((r, v))

        def remove(r: weakref.ref[TextDocument]) -> None:
            asyncio.ensure_future(remove_safe(r, version))

        async with self._lock:

            document_ref = weakref.ref(document, remove)

            if (document_ref, version) not in self._entries or self._entries[
                (document_ref, version)
            ].version != document.version:
                self._entries[(document_ref, version)] = _Entry(document.version)

            return await setter(self._entries[(document_ref, version)])

    async def get_tokens(self, document: TextDocument) -> AsyncIterator["Token"]:
        for e in await self._get_tokens(document):
            yield e

    async def _get_tokens(self, document: TextDocument) -> List[Any]:
        import robot.api

        async def get_tokens() -> AsyncIterator["Token"]:
            with io.StringIO(document.text) as content:
                for t in robot.api.get_tokens(content, tokenize_variables=True):
                    yield t

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
            elif suffix == ".robot":
                return cast(ast.AST, robot.api.get_model(content))
            elif suffix == ".resource":
                return cast(ast.AST, robot.api.get_resource_model(content))
            else:
                raise UnknownFileTypeError(str(document.uri))

    async def get_namespace(self, document: TextDocument) -> Namespace:
        async def setter(e: _Entry) -> Namespace:
            if e.namespace is None:
                e.namespace, e.model = await self.__get_namespace(document, e.model)
            return e.namespace

        return await self.__get_entry(document, setter)

    async def __get_namespace(self, document: TextDocument, model: Optional[ast.AST]) -> Tuple[Namespace, ast.AST]:
        library_manager = await self.get_library_manager(document)

        model = await self.__get_model(document) if model is None else model
        return Namespace(library_manager, model, document.uri.to_path_str()), model

    async def get_library_manager(self, document: TextDocument) -> LibraryManager:
        # TODO: library manger per workspace folder

        folder = self.parent.workspace.get_workspace_folder(document.uri)

        a = await self.parent.workspace.get_configuration("robotcode", None if folder is None else folder.uri)

        conf = RobotcodeConfig.parse_obj(a)

        return self._library_manager

import ast
import io
import weakref
import asyncio

from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple, TypeVar, cast

from ...language_server.parts.protocol_part import LanguageServerProtocolPart
from ...language_server.protocol import LanguageServerProtocol
from ...language_server.text_document import TextDocument

_TResult = TypeVar("_TResult")


class UnknownFileTypeError(Exception):
    pass


@dataclass
class _Entry:
    version: int
    model: Optional[ast.AST] = None
    tokens: Optional[List[Any]] = None


class ModelCache(LanguageServerProtocolPart):
    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self._lock = asyncio.Lock()
        self._entries: Dict[Tuple[weakref.ref[TextDocument], int], _Entry] = {}
        self._loop = asyncio.get_event_loop()

    async def __get_entry(self, document: TextDocument, setter: Callable[[_Entry], Awaitable[_TResult]]) -> _TResult:
        async with self._lock:
            version = document.version

            async def remove_safe(r: weakref.ref[TextDocument], v: int) -> None:
                async with self._lock:
                    self._entries.pop((r, v))

            def remove(r: weakref.ref[TextDocument]) -> None:
                asyncio.run_coroutine_threadsafe(remove_safe(r, version), self._loop)

            document_ref = weakref.ref(document, remove)

            if (document_ref, version) not in self._entries or self._entries[
                (document_ref, version)
            ].version != document.version:
                self._entries[(document_ref, version)] = _Entry(document.version)

            return await setter(self._entries[(document_ref, version)])

    async def get_tokens(self, document: TextDocument) -> AsyncIterator[Any]:
        for e in await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(self._get_tokens(document), self._loop)):
            yield e

    async def _get_tokens(self, document: TextDocument) -> List[Any]:
        import robot.api
        from robot.parsing.lexer import Token

        async def get_tokens() -> AsyncIterator[Token]:
            with io.StringIO(document.text) as content:
                for t in robot.api.get_tokens(content, tokenize_variables=True):
                    yield t

        async def setter(e: _Entry) -> List[Any]:
            if e.tokens is None:
                e.tokens = [e async for e in get_tokens()]
            return e.tokens

        return await self.__get_entry(document, setter)

    async def get_model(self, document: TextDocument) -> ast.AST:
        return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(self._get_model(document), self._loop))

    async def _get_model(self, document: TextDocument) -> ast.AST:
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

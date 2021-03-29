from __future__ import annotations

import asyncio
import inspect
import io
import weakref
from types import MethodType
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

from ..utils.logging import LoggingDescriptor
from ..utils.uri import Uri
from .types import DocumentUri, Position, Range, TextDocumentItem


def _utf16_unit_offset(chars: str) -> int:
    return sum(ord(ch) > 0xFFFF for ch in chars)


def _position_from_utf16(lines: List[str], position: Position) -> Position:
    # see: https://github.com/microsoft/language-server-protocol/issues/376

    try:
        return Position(
            line=position.line,
            character=position.character - _utf16_unit_offset(lines[position.line][: position.character]),
        )
    except IndexError:
        return Position(line=len(lines), character=0)


def _range_from_utf16(lines: List[str], range: Range) -> Range:
    return Range(start=_position_from_utf16(lines, range.start), end=_position_from_utf16(lines, range.end))


class InvalidRangeError(Exception):
    pass


_T = TypeVar("_T")


class TextDocument:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        text_document_item: Optional[TextDocumentItem] = None,
        *,
        document_uri: Optional[DocumentUri] = None,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
        text: Optional[str] = None,
    ) -> None:
        super().__init__()

        self._lock = asyncio.Lock()

        self.document_uri = (
            text_document_item.uri
            if text_document_item is not None
            else document_uri
            if document_uri is not None
            else ""
        )
        self.uri = Uri(self.document_uri)

        self.language_id = (
            text_document_item.language_id
            if text_document_item is not None
            else language_id
            if language_id is not None
            else ""
        )
        self.version = text_document_item.version if text_document_item is not None else version
        self._text = text_document_item.text if text_document_item is not None else text if text is not None else ""

        self._lines: Optional[List[str]] = None

        self._cache: Dict[weakref.ref[Any], Any] = {}
        self._in_change_cache = False

        self._data: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()

        self._loop = asyncio.get_event_loop()

    @_logger.call
    def __del__(self) -> None:
        self._clear()

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self) -> str:
        return (
            f"TextDocument(uri={repr(self.uri)}, "
            f"language_id={repr(self.language_id)}, "
            f"version={repr(self.version)}"
            f")"
        )

    @property
    def text(self) -> str:
        return self._text

    async def apply_none_change(self) -> None:
        async with self._lock:
            self._lines = None
            self._invalidate_cache()

    async def apply_full_change(self, version: Optional[int], text: str) -> None:
        async with self._lock:
            if version is not None:
                self.version = version
            self._text = text
            self._lines = None
            self._invalidate_cache()

    async def apply_incremental_change(self, version: Optional[int], range: Range, text: str) -> None:
        async with self._lock:
            try:
                if version is not None:
                    self.version = version

                if range.start > range.end:
                    raise InvalidRangeError(f"Start position is greater then end position {range}.")

                lines = self._text.splitlines(True)
                (start_line, start_col), (end_line, end_col) = _range_from_utf16(lines, range)

                if start_line == len(lines):
                    self._text = self._text + text
                    return

                with io.StringIO() as new:
                    for i, line in enumerate(lines):
                        if i < start_line:
                            new.write(line)
                            continue

                        if i > end_line:
                            new.write(line)
                            continue

                        if i == start_line:
                            new.write(line[:start_col])
                            new.write(text)

                        if i == end_line:
                            new.write(line[end_col:])

                    self._text = new.getvalue()
                self._lines = None
            finally:
                self._invalidate_cache()

    @property
    def lines(self) -> List[str]:
        if self._lines is None:
            self._lines = self._text.splitlines(True)

        return self._lines

    def _invalidate_cache(self) -> None:
        self._cache.clear()

    async def invalidate_cache(self) -> None:
        async with self._lock:
            self._invalidate_cache()

    def _invalidate_data(self) -> None:
        self._data.clear()

    async def invalidate_data(self) -> None:
        async with self._lock:
            self._invalidate_data()

    async def get_cache(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        if self._in_change_cache:
            return await self._get_cache(entry, *args, **kwargs)

        else:
            self._in_change_cache = True
            try:
                async with self._lock:
                    return await self._get_cache(entry, *args, **kwargs)
            finally:
                self._in_change_cache = False

    async def __remove_cache_entry_safe(self, ref: Any) -> None:
        async with self._lock:
            self._cache.pop(ref)

    def __remove_cache_entry(self, ref: Any) -> None:
        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.__remove_cache_entry_safe(ref), self._loop)
        else:
            self._cache.pop(ref)

    def __get_cache_reference(self, entry: Callable[..., Any]) -> weakref.ref[Any]:

        if inspect.ismethod(entry):
            reference: weakref.ref[Any] = weakref.WeakMethod(cast(MethodType, entry), self.__remove_cache_entry)
        else:
            reference = weakref.ref(entry, self.__remove_cache_entry)

        return reference

    async def _get_cache(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:

        reference = self.__get_cache_reference(entry)

        if reference not in self._cache:
            self._cache[reference] = None

        if self._cache[reference] is None:
            result = entry(self, *args, **kwargs)  # type: ignore

            if isinstance(result, Awaitable):
                self._cache[reference] = await result
            else:
                self._cache[reference] = result

        return cast("_T", self._cache[reference])

    async def set_cache(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
        data: _T,
    ) -> _T:
        if self._in_change_cache:
            return await self._set_cache(entry, data)

        else:
            self._in_change_cache = True
            try:
                async with self._lock:
                    return await self._set_cache(entry, data)
            finally:
                self._in_change_cache = False

    async def _set_cache(
        self, entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]], data: _T
    ) -> _T:
        reference = self.__get_cache_reference(entry)

        self._cache[reference] = data

        return data

    async def remove_cache_entry(
        self, entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]]
    ) -> None:
        async with self._lock:
            if inspect.ismethod(entry):
                self._cache.pop(weakref.WeakMethod(cast(MethodType, entry)), None)
            else:
                self._cache.pop(weakref.ref(entry), None)

    def set_data(self, key: Any, data: Any) -> None:
        self._data[key] = data

    def get_data(self, key: Any, default: Any = None) -> Any:
        return self._data.get(key, default)

    def _clear(self) -> None:
        self._invalidate_cache()
        self._invalidate_data()

    async def clear(self) -> None:
        async with self._lock:
            self._clear()

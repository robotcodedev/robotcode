from __future__ import annotations

import asyncio
import inspect
import io
import weakref
from types import MethodType
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

from ...utils.uri import Uri
from .lsp_types import DocumentUri, Position, Range, TextDocumentItem


def _utf16_unit_offset(chars: str) -> int:
    return sum(ord(ch) > 0xFFFF for ch in chars)


def _position_from_utf16(lines: List[str], position: Position) -> Position:
    # see: https://github.com/microsoft/language-server-protocol/issues/376

    try:
        return Position(
            line=position.line,
            character=position.character - _utf16_unit_offset(lines[position.line][: position.character]),
        )
    except IndexError:  # pragma: no cover
        return Position(line=len(lines), character=0)


def _range_from_utf16(lines: List[str], range: Range) -> Range:
    return Range(start=_position_from_utf16(lines, range.start), end=_position_from_utf16(lines, range.end))


class InvalidRangeError(Exception):
    pass


_T = TypeVar("_T")


class CacheEntry:
    def __init__(self, data: Any = None) -> None:
        self.data = data
        self.lock: asyncio.Lock = asyncio.Lock()


class TextDocument:
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

        self._references: weakref.WeakSet[Any] = weakref.WeakSet()

        self.document_uri = (
            text_document_item.uri
            if text_document_item is not None
            else document_uri
            if document_uri is not None
            else ""
        )
        self.uri = Uri(self.document_uri).normalized()

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

        self._cache: Dict[weakref.ref[Any], CacheEntry] = {}

        self._data: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()

    @property
    def references(self) -> weakref.WeakSet[Any]:  # pragma: no cover
        return self._references

    def __del__(self) -> None:
        self._clear()

    def __str__(self) -> str:  # pragma: no cover
        return self.__repr__()

    def __repr__(self) -> str:  # pragma: no cover
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
            finally:
                self._lines = None
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

    def __remove_cache_entry(self, ref: Any) -> None:
        async def __remove_cache_entry_safe(_ref: Any) -> None:
            async with self._lock:
                self._cache.pop(_ref)

        if self._lock.locked():
            asyncio.create_task(__remove_cache_entry_safe(ref))
        else:
            self._cache.pop(ref)

    def __get_cache_reference(self, entry: Callable[..., Any], /, *, add_remove: bool = True) -> weakref.ref[Any]:

        if inspect.ismethod(entry):
            reference: weakref.ref[Any] = weakref.WeakMethod(
                cast(MethodType, entry), self.__remove_cache_entry if add_remove else None
            )
        else:
            reference = weakref.ref(entry, self.__remove_cache_entry if add_remove else None)

        return reference

    async def get_cache(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:

        reference = self.__get_cache_reference(entry)

        if reference not in self._cache:
            async with self._lock:
                self._cache[reference] = CacheEntry()

        e = self._cache[reference]

        async with e.lock:
            if e.data is None:
                result = entry(self, *args, **kwargs)  # type: ignore

                e.data = await result

        return cast("_T", e.data)

    async def remove_cache_entry(
        self, entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]]
    ) -> None:
        async with self._lock:
            self.__remove_cache_entry(self.__get_cache_reference(entry, add_remove=False))

        await asyncio.sleep(0)

    def set_data(self, key: Any, data: Any) -> None:
        self._data[key] = data

    def get_data(self, key: Any, default: Optional[_T] = None) -> _T:
        return self._data.get(key, default)

    def _clear(self) -> None:
        self._lines = None
        self._invalidate_cache()
        self._invalidate_data()

    async def clear(self) -> None:
        async with self._lock:
            self._clear()

from __future__ import annotations

import collections
import inspect
import io
import threading
import weakref
from typing import Any, Awaitable, Callable, Dict, Final, List, Optional, TypeVar, Union, cast

from robotcode.core.async_tools import async_event, create_sub_task
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import DocumentUri, Position, Range
from robotcode.core.uri import Uri


def is_multibyte_char(char: str) -> bool:
    return ord(char) > 0xFFFF


def position_from_utf16(lines: List[str], position: Position) -> Position:
    if position.line >= len(lines):
        return position

    utf32_offset = 0
    utf16_counter = 0

    for c in lines[position.line]:
        utf16_counter += 2 if is_multibyte_char(c) else 1

        if utf16_counter > position.character:
            break

        utf32_offset += 1

    return Position(line=position.line, character=utf32_offset)


def position_to_utf16(lines: List[str], position: Position) -> Position:
    if position.line >= len(lines):
        return position

    utf16_counter = 0

    for i, c in enumerate(lines[position.line]):
        if i >= position.character:
            break

        utf16_counter += 2 if is_multibyte_char(c) else 1

    return Position(line=position.line, character=utf16_counter)


def range_from_utf16(lines: List[str], range: Range) -> Range:
    return Range(start=position_from_utf16(lines, range.start), end=position_from_utf16(lines, range.end))


def range_to_utf16(lines: List[str], range: Range) -> Range:
    return Range(start=position_to_utf16(lines, range.start), end=position_to_utf16(lines, range.end))


class InvalidRangeError(Exception):
    pass


_T = TypeVar("_T")


class CacheEntry:
    def __init__(self) -> None:
        self.data: Any = None
        self.has_data: bool = False
        self.lock = threading.RLock()


class TextDocument:
    _logger: Final = LoggingDescriptor()

    def __init__(
        self,
        document_uri: DocumentUri,
        text: str,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> None:
        super().__init__()

        self._lock = threading.RLock()
        self.document_uri = document_uri
        self.uri = Uri(self.document_uri).normalized()
        self.language_id = language_id
        self._version = version
        self._text = text
        self._orig_text = text
        self._orig_version = version
        self._lines: Optional[List[str]] = None
        self._cache: Dict[weakref.ref[Any], CacheEntry] = collections.defaultdict(CacheEntry)
        self._data: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()
        self.opened_in_editor = False

    @property
    def version(self) -> Optional[int]:
        return self._version

    @version.setter
    def version(self, value: Optional[int]) -> None:
        self._version = value

    def __str__(self) -> str:  # pragma: no cover
        return self.__repr__()

    def __repr__(self) -> str:  # pragma: no cover
        return f"TextDocument(uri={self.uri!r}, language_id={self.language_id!r}, version={self._version!r})"

    def text(self) -> str:
        with self._lock:
            return self._text

    def save(self, version: Optional[int], text: Optional[str]) -> None:
        self.apply_full_change(version, text, save=True)

    def revert(self, version: Optional[int]) -> bool:
        if self._orig_text != self._text or self._orig_version != self._version:
            self.apply_full_change(version or self._orig_version, self._orig_text)
            return True
        return False

    @_logger.call
    def apply_none_change(self) -> None:
        with self._lock:
            self._lines = None
            self._invalidate_cache()

    @_logger.call
    def apply_full_change(self, version: Optional[int], text: Optional[str], *, save: bool = False) -> None:
        with self._lock:
            if version is not None:
                self._version = version
            if text is not None:
                self._text = text
                self._lines = None
            if save:
                self._orig_text = self._text
            self._invalidate_cache()

    @_logger.call
    def apply_incremental_change(self, version: Optional[int], range: Range, text: str) -> None:
        with self._lock:
            try:
                if version is not None:
                    self._version = version

                if range.start > range.end:
                    raise InvalidRangeError(f"Start position is greater then end position {range}.")

                lines = self.__get_lines()

                (start_line, start_col), (end_line, end_col) = range_from_utf16(lines, range)

                if start_line == len(lines):
                    self._text = self._text + text
                    return

                with io.StringIO() as new_text:
                    for i, line in enumerate(lines):
                        if i < start_line or i > end_line:
                            new_text.write(line)
                            continue

                        if i == start_line:
                            new_text.write(line[:start_col])
                            new_text.write(text)

                        if i == end_line:
                            new_text.write(line[end_col:])

                    self._text = new_text.getvalue()
            finally:
                self._lines = None
                self._invalidate_cache()

    def __get_lines(self) -> List[str]:
        if self._lines is None:
            self._lines = self._text.splitlines(True)

        return self._lines

    def get_lines(self) -> List[str]:
        with self._lock:
            if self._lines is None:
                return self.__get_lines()

            return self._lines

    @async_event
    async def cache_invalidate(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def cache_invalidated(sender) -> None:  # NOSONAR
        ...

    def _invalidate_cache(self) -> None:
        create_sub_task(self.cache_invalidate(self))
        self._cache.clear()
        create_sub_task(self.cache_invalidated(self))

    def invalidate_cache(self) -> None:
        with self._lock:
            self._invalidate_cache()

    def _invalidate_data(self) -> None:
        self._data.clear()

    def invalidate_data(self) -> None:
        with self._lock:
            self._invalidate_data()

    def __remove_cache_entry(self, ref: Any) -> None:
        with self._lock:
            if ref in self._cache:
                self._cache.pop(ref)

    def __get_cache_reference(self, entry: Callable[..., Any], /, *, add_remove: bool = True) -> weakref.ref[Any]:
        if inspect.ismethod(entry):
            return weakref.WeakMethod(entry, self.__remove_cache_entry if add_remove else None)

        return weakref.ref(entry, self.__remove_cache_entry if add_remove else None)

    def get_cache_value(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
    ) -> Optional[_T]:
        reference = self.__get_cache_reference(entry)

        e = self._cache.get(reference, None)
        if e is None:
            return None

        return cast(Optional[_T], e.data)

    def get_cache_sync(
        self,
        entry: Union[Callable[[TextDocument], _T], Callable[..., _T]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        reference = self.__get_cache_reference(entry)

        e = self._cache[reference]

        with e.lock:
            if not e.has_data:
                e.data = entry(self, *args, **kwargs)
                e.has_data = True

            return cast(_T, e.data)

    async def get_cache(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        reference = self.__get_cache_reference(entry)

        e = self._cache[reference]

        with e.lock:
            if not e.has_data:
                e.data = await entry(self, *args, **kwargs)
                e.has_data = True

            return cast(_T, e.data)

    async def remove_cache_entry(
        self, entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]]
    ) -> None:
        self.__remove_cache_entry(self.__get_cache_reference(entry, add_remove=False))

    def set_data(self, key: Any, data: Any) -> None:
        self._data[key] = data

    def remove_data(self, key: Any) -> None:
        try:
            self._data.pop(key)
        except KeyError:
            pass

    def get_data(self, key: Any, default: Optional[Any] = None) -> Any:
        return self._data.get(key, default)

    def _clear(self) -> None:
        self._lines = None
        self._invalidate_cache()
        self._invalidate_data()

    @_logger.call
    def clear(self) -> None:
        with self._lock:
            self._clear()

    def position_from_utf16(self, position: Position) -> Position:
        return position_from_utf16(self.get_lines(), position)

    def position_to_utf16(self, position: Position) -> Position:
        return position_to_utf16(self.get_lines(), position)

    def range_from_utf16(self, range: Range) -> Range:
        return range_from_utf16(self.get_lines(), range)

    def range_to_utf16(self, range: Range) -> Range:
        return range_to_utf16(self.get_lines(), range)

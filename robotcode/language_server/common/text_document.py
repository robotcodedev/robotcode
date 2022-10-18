from __future__ import annotations

import collections
import inspect
import io
import weakref
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

from ...utils.async_tools import Lock, async_event, create_sub_task
from ...utils.logging import LoggingDescriptor
from ...utils.uri import Uri
from .lsp_types import DocumentUri, Range


class InvalidRangeError(Exception):
    pass


_T = TypeVar("_T")


class CacheEntry:
    def __init__(self) -> None:
        self.data: Any = None
        self.has_data: bool = False
        self.lock = Lock()


class TextDocument:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        document_uri: DocumentUri,
        text: str,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> None:
        super().__init__()

        self._lock = Lock()
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
        return (
            f"TextDocument(uri={repr(self.uri)}, "
            f"language_id={repr(self.language_id)}, "
            f"version={repr(self._version)}"
            f")"
        )

    def text_sync(self) -> str:
        return self._text

    async def text(self) -> str:
        async with self._lock:
            return self._text

    async def save(self, version: Optional[int], text: Optional[str]) -> None:
        await self.apply_full_change(version, text, save=True)

    async def revert(self, version: Optional[int]) -> bool:
        if self._orig_text != self._text or self._orig_version != self._version:
            await self.apply_full_change(version or self._orig_version, self._orig_text)
            return True
        return False

    @_logger.call
    async def apply_none_change(self) -> None:
        async with self._lock:
            self._lines = None
            await self._invalidate_cache()

    @_logger.call
    async def apply_full_change(self, version: Optional[int], text: Optional[str], *, save: bool = False) -> None:
        async with self._lock:
            if version is not None:
                self._version = version
            if text is not None:
                self._text = text
                self._lines = None
            if save:
                self._orig_text = self._text
            await self._invalidate_cache()

    @_logger.call
    async def apply_incremental_change(self, version: Optional[int], range: Range, text: str) -> None:
        async with self._lock:
            try:
                if version is not None:
                    self._version = version

                if range.start > range.end:
                    raise InvalidRangeError(f"Start position is greater then end position {range}.")

                lines = self.__get_lines()

                (start_line, start_col), (end_line, end_col) = range

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
                await self._invalidate_cache()

    def __get_lines(self) -> List[str]:
        if self._lines is None:
            self._lines = self._text.splitlines(True)

        return self._lines

    async def get_lines(self) -> List[str]:
        async with self._lock:
            if self._lines is None:
                return self.__get_lines()

            return self._lines

    @async_event
    async def cache_invalidate(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def cache_invalidated(sender) -> None:  # NOSONAR
        ...

    async def _invalidate_cache(self) -> None:
        create_sub_task(self.cache_invalidate(self))
        self._cache.clear()
        create_sub_task(self.cache_invalidated(self))

    @_logger.call
    async def invalidate_cache(self) -> None:
        async with self._lock:
            await self._invalidate_cache()

    async def _invalidate_data(self) -> None:
        self._data.clear()

    @_logger.call
    async def invalidate_data(self) -> None:
        async with self._lock:
            await self._invalidate_data()

    async def __remove_cache_entry_safe(self, _ref: Any) -> None:
        async with self._lock:
            if _ref in self._cache:
                self._cache.pop(_ref)

    def __remove_cache_entry(self, ref: Any) -> None:
        create_sub_task(self.__remove_cache_entry_safe(ref))

    def __get_cache_reference(self, entry: Callable[..., Any], /, *, add_remove: bool = True) -> weakref.ref[Any]:

        if inspect.ismethod(entry):
            reference: weakref.ref[Any] = weakref.WeakMethod(entry, self.__remove_cache_entry if add_remove else None)
        else:
            reference = weakref.ref(entry, self.__remove_cache_entry if add_remove else None)

        return reference

    def get_cache_value(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
    ) -> Optional[_T]:

        reference = self.__get_cache_reference(entry)

        e = self._cache.get(reference, None)
        if e is None:
            return None

        return cast(Optional[_T], e.data)

    async def get_cache(
        self,
        entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:

        reference = self.__get_cache_reference(entry)

        e = self._cache[reference]

        async with e.lock:
            if not e.has_data:
                e.data = await entry(self, *args, **kwargs)
                e.has_data = True

            return cast(_T, e.data)

    @_logger.call
    async def remove_cache_entry(
        self, entry: Union[Callable[[TextDocument], Awaitable[_T]], Callable[..., Awaitable[_T]]]
    ) -> None:
        await self.__remove_cache_entry_safe(self.__get_cache_reference(entry, add_remove=False))

    def set_data(self, key: Any, data: Any) -> None:
        self._data[key] = data

    def remove_data(self, key: Any) -> None:
        try:
            self._data.pop(key)
        except KeyError:
            pass

    def get_data(self, key: Any, default: Optional[_T] = None) -> _T:
        return self._data.get(key, default)

    async def _clear(self) -> None:
        self._lines = None
        await self._invalidate_cache()
        await self._invalidate_data()

    @_logger.call
    async def clear(self) -> None:
        async with self._lock:
            await self._clear()

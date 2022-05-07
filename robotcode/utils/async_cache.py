from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Tuple, TypeVar, cast

from .async_tools import Lock

_T = TypeVar("_T")


def _freeze(v: Any) -> Any:
    if isinstance(v, dict):
        return hash(frozenset(v.items()))
    return v


@dataclass
class CacheEntry:
    value: Any = None
    has_value: bool = False
    lock: Lock = Lock()


class AsyncSimpleCache:
    def __init__(self, max_items: int = 128) -> None:
        self.max_items = max_items

        self._cache: Dict[Tuple[Any, ...], CacheEntry] = defaultdict(CacheEntry)
        self._order: List[Tuple[Any, ...]] = []
        self._lock = Lock()

    async def has(self, *args: Any, **kwargs: Any) -> bool:
        return self._make_key(*args, **kwargs) in self._cache

    async def get(self, func: Callable[..., Awaitable[_T]], *args: Any, **kwargs: Any) -> _T:
        key = self._make_key(*args, **kwargs)

        async with self._lock:
            entry = self._cache[key]
            if entry.has_value:
                return cast(_T, entry.value)

        async with entry.lock:
            entry.value = await func(*args, **kwargs)
            entry.has_value = True

            self._order.insert(0, key)

            if len(self._order) > self.max_items:
                del self._cache[self._order.pop()]

            return entry.value

    @staticmethod
    def _make_key(*args: Any, **kwargs: Any) -> Tuple[Any, ...]:
        return (tuple(_freeze(v) for v in args), hash(frozenset({k: _freeze(v) for k, v in kwargs.items()})))

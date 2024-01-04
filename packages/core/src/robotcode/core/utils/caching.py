from collections import defaultdict
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast

_T = TypeVar("_T")


def _freeze(v: Any) -> Any:
    if isinstance(v, dict):
        return hash(frozenset(v.items()))
    return v


class CacheEntry:
    def __init__(self) -> None:
        self.data: Any = None
        self.has_data: bool = False
        self.lock = RLock()


class SimpleLRUCache:
    def __init__(self, max_items: Optional[int] = 128) -> None:
        self.max_items = max_items

        self._cache: Dict[Tuple[Any, ...], CacheEntry] = defaultdict(CacheEntry)
        self._order: Optional[List[Tuple[Any, ...]]] = None
        if self.max_items:
            self._order = []
        self._lock = RLock()

    def has(self, *args: Any, **kwargs: Any) -> bool:
        key = self._make_key(*args, **kwargs)

        if key in self._cache:
            return self._cache[key].has_data

        return False

    def get(self, func: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        key = self._make_key(*args, **kwargs)

        entry = self._cache[key]

        with entry.lock:
            if not entry.has_data:
                entry.data = func(*args, **kwargs)
                entry.has_data = True

                if self._order is not None and self.max_items is not None:
                    with self._lock:
                        self._order.insert(0, key)

                        if len(self._order) > self.max_items:
                            del self._cache[self._order.pop()]

            return cast(_T, entry.data)

    @staticmethod
    def _make_key(*args: Any, **kwargs: Any) -> Tuple[Any, ...]:
        return (
            tuple(_freeze(v) for v in args),
            hash(frozenset({k: _freeze(v) for k, v in kwargs.items()})),
        )

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            if self._order is not None:
                self._order.clear()

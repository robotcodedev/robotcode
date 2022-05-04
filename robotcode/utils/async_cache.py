from typing import Any, Awaitable, Callable, Dict, List, Tuple, TypeVar, cast

from .async_tools import Lock

_T = TypeVar("_T")


def _freeze(v: Any) -> Any:
    if isinstance(v, dict):
        return frozenset(v.items())
    return v


class AsyncSimpleCache:
    def __init__(self, max_items: int = 128) -> None:
        self.max_items = max_items

        self._cache: Dict[Tuple[Any, ...], Any] = {}
        self._order: List[Tuple[Any, ...]] = []
        self._lock = Lock()

    async def get(self, func: Callable[..., Awaitable[_T]], *args: Any, **kwargs: Any) -> _T:
        key = self._make_key(*args, **kwargs)

        async with self._lock:
            try:
                return cast(_T, self._cache[key])
            except KeyError:
                pass

            res = await func(*args, **kwargs)

            self._cache[key] = res
            self._order.insert(0, key)

            if len(self._order) > self.max_items:
                del self._cache[self._order.pop()]

            return res

    @staticmethod
    def _make_key(*args: Any, **kwargs: Any) -> Tuple[Any, ...]:
        return (tuple(_freeze(v) for v in args), frozenset({k: _freeze(v) for k, v in kwargs.items()}))

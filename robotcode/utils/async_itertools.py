from typing import AsyncIterator, AsyncIterable, Iterable, TypeVar, Union

__all__ = ["async_chain"]

_T = TypeVar("_T")


async def async_chain(*iterables: Union[Iterable[_T], AsyncIterable[_T]]) -> AsyncIterator[_T]:
    for iterable in iterables:
        if isinstance(iterable, AsyncIterable):
            async for v in iterable:
                yield v
        else:
            for v in iterable:
                yield v

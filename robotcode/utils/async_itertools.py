from typing import AsyncIterable, AsyncIterator, Iterable, TypeVar, Union

__all__ = ["async_chain", "async_chain_iterator"]

_T = TypeVar("_T")


async def async_chain(*iterables: Union[Iterable[_T], AsyncIterable[_T]]) -> AsyncIterator[_T]:
    for iterable in iterables:
        if isinstance(iterable, AsyncIterable):
            async for v in iterable:
                yield v
        else:
            for v in iterable:
                yield v


async def async_chain_iterator(iterator: AsyncIterator[Union[Iterable[_T], AsyncIterable[_T]]]) -> AsyncIterator[_T]:
    async for e in iterator:
        async for v in async_chain(e):
            yield v

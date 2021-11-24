import inspect
from typing import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    TypeVar,
    Union,
    cast,
)

__all__ = ["async_chain", "async_chain_iterator"]

_T = TypeVar("_T")
AnyIterable = Union[Iterable[_T], AsyncIterable[_T]]


async def async_chain(*iterables: AnyIterable[_T]) -> AsyncIterator[_T]:
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


async def async_takewhile(
    predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]],
    iterable: AnyIterable[_T],
) -> AsyncIterator[_T]:
    if isinstance(iterable, AsyncIterable):
        async for e in iterable:
            result = predicate(e)
            if inspect.isawaitable(result):
                result = await cast(Awaitable[bool], result)
            if result:
                yield e
            else:
                break
    else:
        for e in iterable:
            result = predicate(e)
            if inspect.isawaitable(result):
                result = await cast(Awaitable[bool], result)
            if result:
                yield e
            else:
                break


async def async_dropwhile(
    predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]],
    iterable: AnyIterable[_T],
) -> AsyncIterator[_T]:
    result: Union[bool, Awaitable[bool]] = True
    if isinstance(iterable, AsyncIterable):
        async for e in iterable:
            if not result:
                yield e
            else:
                result = predicate(e)
                if inspect.isawaitable(result):
                    result = await cast(Awaitable[bool], result)

                if not result:
                    yield e
    else:
        for e in iterable:
            if not result:
                yield e
            else:
                result = predicate(e)
                if inspect.isawaitable(result):
                    result = await cast(Awaitable[bool], result)

                if not result:
                    yield e

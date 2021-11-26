import inspect
from typing import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    TypeVar,
    Union,
    cast,
)

__all__ = ["async_chain", "async_chain_iterator", "async_takewhile", "async_dropwhile"]

_T = TypeVar("_T")
AnyIterable = Union[Iterable[_T], AsyncIterable[_T]]


async def async_chain(*iterables: AnyIterable[_T]) -> AsyncGenerator[_T, None]:
    for iterable in iterables:
        if isinstance(iterable, AsyncIterable):
            async for v in iterable:
                yield v
        else:
            for v in iterable:
                yield v


async def async_chain_iterator(
    iterator: AsyncIterator[Union[Iterable[_T], AsyncIterable[_T]]]
) -> AsyncGenerator[_T, None]:
    async for e in iterator:
        async for v in async_chain(e):
            yield v


async def async_takewhile(
    predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]],
    iterable: AnyIterable[_T],
) -> AsyncGenerator[_T, None]:
    if isinstance(iterable, AsyncIterable):
        async for e in iterable:
            result = await __call_predicate(predicate, e)
            if result:
                yield e
            else:
                break
    else:
        for e in iterable:
            result = await __call_predicate(predicate, e)
            if result:
                yield e
            else:
                break


async def __call_predicate(predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]], e: _T) -> bool:
    result = predicate(e)
    if inspect.isawaitable(result):
        return await cast(Awaitable[bool], result)
    return cast(bool, result)


async def async_dropwhile(
    predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]],
    iterable: AnyIterable[_T],
) -> AsyncGenerator[_T, None]:
    result: Union[bool, Awaitable[bool]] = True

    if isinstance(iterable, AsyncIterable):
        async for e in iterable:
            if not result:
                yield e
            else:
                result = await __call_predicate(predicate, e)

                if not result:
                    yield e
    else:
        for e in iterable:
            if not result:
                yield e
            else:
                result = await __call_predicate(predicate, e)

                if not result:
                    yield e

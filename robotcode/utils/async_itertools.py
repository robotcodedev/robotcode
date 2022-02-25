import inspect
from typing import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Optional,
    TypeVar,
    Union,
    cast,
)

__all__ = ["async_chain", "async_chain_iterator", "async_takewhile", "async_dropwhile"]

_T = TypeVar("_T")
AnyIterable = Union[Iterable[_T], AsyncIterable[_T]]


async def as_async_iterable(iterable: AnyIterable[_T]) -> AsyncGenerator[_T, None]:
    if isinstance(iterable, AsyncIterable):
        async for v in iterable:
            yield v
    else:
        for v in iterable:
            yield v


async def async_chain(*iterables: AnyIterable[_T]) -> AsyncGenerator[_T, None]:
    for iterable in iterables:
        if isinstance(iterable, AsyncIterable):
            async for v in iterable:
                yield v
        else:
            for v in iterable:
                yield v


async def async_chain_iterator(iterator: AsyncIterator[AnyIterable[_T]]) -> AsyncGenerator[_T, None]:
    async for e in iterator:
        async for v in async_chain(e):
            yield v


async def __call_predicate(predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]], e: _T) -> bool:
    result = predicate(e)
    if inspect.isawaitable(result):
        return await cast(Awaitable[bool], result)
    return cast(bool, result)


async def iter_any_iterable(iterable: AnyIterable[_T]) -> AsyncGenerator[_T, None]:
    if isinstance(iterable, AsyncIterable):
        async for e in iterable:
            yield e
    else:
        for e in iterable:
            yield e


async def async_takewhile(
    predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]],
    iterable: AnyIterable[_T],
) -> AsyncGenerator[_T, None]:
    async for e in iter_any_iterable(iterable):
        result = await __call_predicate(predicate, e)
        if result:
            yield e
        else:
            break


async def async_dropwhile(
    predicate: Union[Callable[[_T], bool], Callable[[_T], Awaitable[bool]]],
    iterable: AnyIterable[_T],
) -> AsyncGenerator[_T, None]:
    result: Union[bool, Awaitable[bool]] = True

    async for e in iter_any_iterable(iterable):
        if not result:
            yield e
        else:
            result = await __call_predicate(predicate, e)

            if not result:
                yield e


class __NotSet:
    pass


__NOT_SET = __NotSet()


async def async_next(__i: AsyncIterator[_T], __default: Union[_T, None, __NotSet] = __NOT_SET) -> Optional[_T]:
    try:
        return await __i.__anext__()
    except StopAsyncIteration:
        if __default is __NOT_SET:
            raise
        return cast(_T, __default)

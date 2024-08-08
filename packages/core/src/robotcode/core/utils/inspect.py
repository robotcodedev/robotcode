import inspect
from typing import Any, Callable, Coroutine, Iterator, Optional


def iter_methods(
    obj: Any, predicate: Optional[Callable[[Callable[..., Any]], bool]] = None
) -> Iterator[Callable[..., Any]]:
    is_cls = inspect.isclass(obj)
    cls = obj if is_cls else type(obj)

    for name in dir(cls):
        v = getattr(cls, name)
        if inspect.isfunction(v):
            if is_cls:
                m = v
            else:
                m = getattr(obj, name)
                if not inspect.ismethod(m):  # type: ignore
                    continue

            if predicate is None or predicate(m):
                yield m


_lambda_type = type(lambda: 0)
_lambda_name = (lambda: 0).__name__


def is_lambda(v: Any) -> bool:
    return isinstance(v, _lambda_type) and v.__name__ == _lambda_name


def ensure_coroutine(
    func: Callable[..., Any],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    async def wrapper(*fargs: Any, **fkwargs: Any) -> Any:
        return func(*fargs, **fkwargs)

    if inspect.iscoroutinefunction(func) or inspect.iscoroutinefunction(inspect.unwrap(func)):
        return func

    return wrapper

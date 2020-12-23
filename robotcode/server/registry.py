from typing import Any, Callable, Optional, Type


class Registry:
    def __init__(self, func) -> None:
        self.__func = func

    def __get__(self, obj: Any, objtype: Type) -> "Registry":
        return self

    def __set_name__(self, owner: Any, name: str):
        self.__owner = owner
        self.__owner_name = name

    def rpc_method(self, _func: Optional[Callable[..., Any]] = None, *, name: str) -> Callable[..., Any]:
        def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:

            return func

        if _func is None:
            return _decorator
        return _decorator(_func)

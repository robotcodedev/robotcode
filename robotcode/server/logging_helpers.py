import functools
import inspect
import logging
from types import FunctionType, MethodType
from typing import Any, Callable, List, Mapping, Optional, Type, Union, cast
import collections

__all__ = ["DefineLoggerDescriptor", "define_logger"]


def get_class_that_defined_method(meth: Callable):
    if inspect.ismethod(meth):
        for c in inspect.getmro(cast(MethodType, meth).__self__.__class__):
            if c.__dict__.get(meth.__name__) is meth:
                return c
        meth = cast(MethodType, meth).__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        class_name = meth.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)[0]
        try:
            cls = getattr(inspect.getmodule(meth), class_name)
        except AttributeError:
            cls = cast(FunctionType, meth).__globals__.get(class_name)
        if isinstance(cls, type):
            return cls
    return None


def _get_callable_has_self_or_cls_parameter(func: Any):
    if inspect.ismethod(func) or isinstance(func, (classmethod, staticmethod)):
        return True
    if inspect.isfunction(func) and len(func.__qualname__.split(".<locals>.", 1)[-1].rsplit(".", 1)) > 1:
        return True
    return False


def get_unwrapped_func(func: Callable):
    result = inspect.unwrap(func)
    if isinstance(result, (staticmethod, classmethod)):
        result = result.__func__
    return result


_LoggerEntry = collections.namedtuple("_LoggerEntry", "level prefix condition")


class _HasLoggerEntries:
    __logging_entries__: List[_LoggerEntry]


_FUNC_TYPE = Union[Callable[..., logging.Logger], staticmethod, classmethod, None]


class DefineLoggerDescriptor(logging.LoggerAdapter):
    __func: _FUNC_TYPE = None
    __name: Optional[str] = None
    __level: Union[int, str] = logging.NOTSET
    __owner: Any = None
    __owner_name: Optional[str] = None
    __postfix: str = ""
    __logger: Optional[logging.Logger] = None

    def __init__(
        self,
        _func: _FUNC_TYPE = None,
        *,
        name: Optional[str] = None,
        postfix: str = "",
        level: Union[int, str] = logging.NOTSET,
        extra: Mapping[str, Any] = {},
    ) -> None:

        self.__func = _func

        if _func is not None:
            functools.update_wrapper(self, _func)  # type: ignore

        self.__name = name
        self.__level = level
        self.__postfix = postfix
        self.extra = extra

    def log(self, level: int, msg: Any, *args, **kwargs):
        if self.isEnabledFor(level):
            super().log(level, msg() if callable(msg) else msg, *args, **kwargs)

    def __init_logger(self) -> "DefineLoggerDescriptor":
        if self.__logger is None:
            returned_logger = None

            if self.__func is not None:

                if self.__owner is None:
                    returned_logger = self.__func()
                else:
                    if self.__func is not None:
                        if isinstance(self.__func, staticmethod):
                            returned_logger = cast(staticmethod, self.__func).__func__()
                        elif isinstance(self.__func, classmethod):
                            returned_logger = cast(classmethod, self.__func).__func__(type(self.__owner))
                        else:
                            returned_logger = self.__func(self.__owner)

            self.__logger = (
                returned_logger
                if returned_logger is not None
                else logging.getLogger(
                    self.__name
                    if self.__name is not None
                    else self.__func.__module__
                    + ("" if self.__owner is None else "." + self.__owner.__qualname__)
                    + self.__postfix
                )
            )

            if self.__logger is None:
                raise NotImplementedError("Can't get or create a Logger object")

            self.setLevel(self.__level)

        return self

    @property
    def logger(self) -> Optional[logging.Logger]:
        if self.__logger is None:
            self.__init_logger()

        return self.__logger

    def __set_name__(self, owner: Any, name: str):
        self.__owner = owner
        self.__owner_name = name

    def __call__(self, _func: _FUNC_TYPE = None) -> "DefineLoggerDescriptor":
        if _func is not None:
            self.__func = _func

        return self

    def __get__(self, obj: Any, objtype: Type) -> "DefineLoggerDescriptor":
        return self

    def call(
        self,
        _func: Optional[Callable[..., Any]] = None,
        *,
        level: int = logging.DEBUG,
        prefix: str = "",
        condition: Optional[Callable[..., bool]] = None,
        **kwargs,
    ) -> Callable[..., Any]:
        def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            unwrapped_func = inspect.unwrap(func)

            if not hasattr(unwrapped_func, "__logging_entries__"):
                unwrapped_func.__logging_entries__ = []

            unwrapped_func.__logging_entries__.append(_LoggerEntry(level=level, prefix=prefix, condition=condition))

            skipt_first_arg = _get_callable_has_self_or_cls_parameter(unwrapped_func)

            @functools.wraps(func)
            def __wrapper(*wrapper_args, **wrapper_kwargs) -> Callable[..., Any]:

                if isinstance(unwrapped_func, staticmethod):
                    real_args = wrapper_args[1:]
                    real_func = unwrapped_func.__func__
                elif isinstance(unwrapped_func, classmethod):
                    real_args = (type(wrapper_args[0]), *wrapper_args[1:])
                    real_func = unwrapped_func.__func__
                else:
                    real_args = wrapper_args
                    real_func = unwrapped_func

                if hasattr(unwrapped_func, "__logging_entries__"):
                    self.__init_logger()

                    if isinstance(unwrapped_func, (staticmethod, classmethod)):
                        func_name = (
                            unwrapped_func.__func__.__qualname__
                            if self.__owner or self.__name is None
                            else unwrapped_func.__func__.__name__
                        )
                    else:
                        func_name = (
                            unwrapped_func.__qualname__
                            if self.__owner is None or self.__name
                            else unwrapped_func.__name__
                        )

                    for c in cast(_HasLoggerEntries, unwrapped_func).__logging_entries__:
                        if (c.condition is None or c.condition(*real_args, **wrapper_kwargs)):

                            def build_message():
                                message_args = wrapper_args[1:] if skipt_first_arg else wrapper_args

                                return "{0}{1}({2}{3}{4})".format(
                                    c.prefix,
                                    func_name,
                                    ", ".join(repr(a) for a in message_args),
                                    (", " if len(message_args) > 0 and len(wrapper_kwargs) > 0 else ""),
                                    (
                                        ", ".join(f"{str(k)}={repr(v)}" for k, v in wrapper_kwargs.items())
                                        if len(wrapper_kwargs) > 0
                                        else ""
                                    ),
                                )
                            self.log(c.level, build_message, **kwargs)

                result = None
                try:
                    result = real_func(*real_args, **wrapper_kwargs)
                except BaseException:
                    raise

                return result

            return __wrapper

        if _func is None:
            return _decorator
        return _decorator(_func)


define_logger = DefineLoggerDescriptor

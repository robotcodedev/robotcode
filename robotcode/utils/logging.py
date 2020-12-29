import functools
import inspect
import logging
from types import FunctionType, MethodType
from typing import Any, Callable, List, Optional, Type, TypeVar, Union, cast, overload
import collections

__all__ = ["LoggingDescriptor"]


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


def get_unwrapped_func(func: Callable[..., Any]) -> Callable[..., Any]:
    result = inspect.unwrap(func)
    if isinstance(result, (staticmethod, classmethod)):
        return get_unwrapped_func(result.__func__)
    return result


_LoggerEntry = collections.namedtuple("_LoggerEntry", "level prefix condition states")


class _HasLoggerEntries:
    __logging_entries__: List[_LoggerEntry]


_FUNC_TYPE = Union[Callable[[], logging.Logger], Callable[[], None], staticmethod, None]

_F = TypeVar("_F", bound=Callable[..., Any])


class LoggingDescriptor:
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
    ) -> None:
        self.__func = _func

        if _func is not None:
            functools.update_wrapper(self, _func)  # type: ignore

        self.__name = name
        self.__level = level
        self.__postfix = postfix

    def __init_logger(self) -> "LoggingDescriptor":
        if self.__logger is None:
            returned_logger = None

            if self.__func is not None:

                if isinstance(self.__func, staticmethod):
                    returned_logger = cast(staticmethod, self.__func).__func__()
                else:
                    returned_logger = self.__func()

            self.__logger = (
                returned_logger
                if returned_logger is not None
                else logging.getLogger(
                    self.__name
                    if self.__name is not None
                    else (
                        ("" if self.__owner is None else self.__owner.__module__ + "." + self.__owner.__qualname__)
                        if self.__owner is not None
                        else get_unwrapped_func(self.__func).__module__
                        if self.__func is not None
                        else "<unknown>"
                    )
                    + self.__postfix
                )
            )

            if self.__logger is None:
                raise NotImplementedError("Can't get or create a Logger object")

            self.set_level(self.__level)

        return self

    @property
    def logger(self) -> logging.Logger:
        if self.__logger is None:
            self.__init_logger()

        if self.__logger is None:
            raise Exception("Logger not initialized")

        return self.__logger

    def __set_name__(self, owner: Any, name: str):
        self.__owner = owner
        self.__owner_name = name

    def __call__(self, _func: _FUNC_TYPE = None) -> "LoggingDescriptor":
        if _func is not None:
            self.__func = _func

        return self

    def __get__(self, obj: Any, objtype: Type) -> "LoggingDescriptor":
        return self

    def log(self, level: int, msg: Any, condition: Callable[[], bool] = None, *args, **kwargs):
        if self.is_enabled_for(level) and (condition is not None and condition() or condition is None):
            self.logger.log(level, msg() if callable(msg) else msg, *args, **kwargs)

    def debug(self, msg: Union[str, Callable[[], str]], condition: Callable[[], bool] = None, *args, **kwargs):
        self.log(logging.DEBUG, msg, condition, *args, **kwargs)

    def info(self, msg: Union[str, Callable[[], str]], condition: Callable[[], bool] = None, *args, **kwargs):
        self.log(logging.INFO, msg, condition, *args, **kwargs)

    def warning(self, msg: Union[str, Callable[[], str]], condition: Callable[[], bool] = None, *args, **kwargs):
        self.log(logging.WARNING, msg, condition, *args, **kwargs)

    def error(self, msg: Union[str, Callable[[], str]], condition: Callable[[], bool] = None, *args, **kwargs):
        self.log(logging.ERROR, msg, condition, *args, **kwargs)

    def exception(
        self,
        msg: Union[BaseException, str, Callable[[], str]],
        condition: Callable[[], bool] = None,
        exc_info=True,
        *args,
        **kwargs,
    ):
        self.log(logging.ERROR, msg, condition, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg: Union[str, Callable[[], str]], condition: Callable[[], bool] = None, *args, **kwargs):
        self.log(logging.CRITICAL, msg, condition, *args, **kwargs)

    def is_enabled_for(self, level):
        return self.logger.isEnabledFor(level)

    def set_level(self, level):
        self.logger.setLevel(level)

    def get_effective_level(self):
        return self.logger.getEffectiveLevel()

    def has_handlers(self):
        return self.logger.hasHandlers()

    @property
    def name(self):
        return self.logger.name

    def __repr__(self):
        logger = self.logger
        level = logging.getLevelName(logger.getEffectiveLevel())
        return f"{self.__class__.__name__}(name={repr(logger.name)}, level={repr(level)})"

    @overload
    def call(self, __func: _F) -> _F:
        ...

    @overload
    def call(
        self,
        *,
        level: int = logging.DEBUG,
        prefix: str = "",
        condition: Optional[Callable[..., bool]] = None,
        entering=True,
        exiting=True,
        exception=True,
    ) -> Callable[[_F], _F]:
        ...

    def call(
        self,
        _func: Callable[..., Any] = None,
        *,
        level: int = logging.DEBUG,
        prefix: str = "",
        condition: Optional[Callable[..., bool]] = None,
        entering=True,
        exiting=False,
        exception=False,
        **kwargs,
    ) -> Callable[[_F], _F]:
        def _decorator(func: Callable[..., Any]):
            unwrapped_func = inspect.unwrap(func)

            if not hasattr(unwrapped_func, "__logging_entries__"):
                unwrapped_func.__logging_entries__ = []

            unwrapped_func.__logging_entries__.append(
                _LoggerEntry(
                    level=level,
                    prefix=prefix,
                    condition=condition,
                    states={"entering": entering, "exiting": exiting, "exception": exception},
                )
            )

            skip_first_arg = _get_callable_has_self_or_cls_parameter(unwrapped_func)

            @functools.wraps(func)
            def _wrapper(*wrapper_args, **wrapper_kwargs) -> Any:

                if isinstance(unwrapped_func, staticmethod):
                    real_args = wrapper_args[1:]
                    real_func = unwrapped_func.__func__
                else:
                    real_args = wrapper_args
                    real_func = unwrapped_func

                def has_logging_entries():
                    return hasattr(unwrapped_func, "__logging_entries__")

                def func_name():
                    if isinstance(unwrapped_func, staticmethod):
                        return (
                            unwrapped_func.__func__.__qualname__
                            if self.__owner or self.__name is None
                            else unwrapped_func.__func__.__name__
                        )
                    else:
                        return (
                            unwrapped_func.__qualname__
                            if self.__owner is None or self.__name
                            else unwrapped_func.__name__
                        )

                def get_logging_entries():
                    return cast(_HasLoggerEntries, unwrapped_func).__logging_entries__

                def log(message, *, state, log_level=None, **log_kwargs):
                    if has_logging_entries():
                        for c in get_logging_entries():
                            if c.states[state]:

                                def state_msg():
                                    return (state + " ") if state != "entering" or c.states["exiting"] else ""

                                self.log(
                                    log_level if log_level is not None else c.level,
                                    lambda: f"{state_msg()}{prefix}{message()}",
                                    condition=lambda: c.condition is None or c.condition(*real_args, **wrapper_kwargs),
                                    **{**kwargs, **log_kwargs},
                                )

                def build_enter_message():
                    message_args = wrapper_args[1:] if skip_first_arg else wrapper_args

                    return "{0}({1}{2}{3})".format(
                        func_name(),
                        ", ".join(repr(a) for a in message_args),
                        (", " if len(message_args) > 0 and len(wrapper_kwargs) > 0 else ""),
                        (
                            ", ".join(f"{str(k)}={repr(v)}" for k, v in wrapper_kwargs.items())
                            if len(wrapper_kwargs) > 0
                            else ""
                        ),
                    )

                def build_exit_message(res):
                    return "{0}(...) -> {1}".format(func_name(), repr(res))

                def build_exception_message(exception):
                    return "{0}(...)->{1}".format(func_name(), exception)

                log(build_enter_message, state="entering")

                result = None
                try:
                    result = real_func(*real_args, **wrapper_kwargs)
                except BaseException as e:
                    ex = e
                    log(lambda: build_exception_message(ex), log_level=logging.ERROR, state="exception", exc_info=True)
                    raise
                else:
                    log(lambda: build_exit_message(result), state="exiting")
                return result

            return _wrapper

        if _func is None:
            return _decorator
        return _decorator(_func)

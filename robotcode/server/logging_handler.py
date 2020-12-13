from abc import ABC, abstractmethod
from logging import Logger, DEBUG, INFO

__all__ = ["LoggingHandler"]


def _do_log(logger, level, func, *args, **kwargs):
    if logger is not None and logger.isEnabledFor(level):
        msg = f"Calling {func.__qualname__}({', '.join(repr(a) for a in args)}{(', 'if len(args)>0 else ''+', '.join(f'{str(k)}={repr(v)}' for k,v in kwargs.items())) if len(kwargs)>0 else ''})"  # noqa: E501
        logger.log(level, msg)


class LoggingHandler(ABC):
    @abstractmethod
    def _get_logger(self) -> Logger:
        ...

    @staticmethod
    def _debug_call(func):
        def wrapper(self: LoggingHandler, *args, **kwargs):
            _do_log(self._get_logger(), DEBUG, func, *args, **kwargs)
            return func(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def _info_call(func):
        def wrapper(self: LoggingHandler, *args, **kwargs):
            _do_log(self._get_logger(), INFO, func, *args, **kwargs)
            return func(self, *args, **kwargs)

        return wrapper

import asyncio
from inspect import ismethod
from types import MethodType
from typing import Any, Callable, Generic, MutableSet, TypeVar, Union, cast
import weakref

__all__ = ["TCallback", "AsyncEvent"]

TCallback = TypeVar("TCallback", bound=Union[Callable[..., Any], MethodType])


class AsyncEvent(Generic[TCallback]):
    def __init__(self):
        self.listeners: weakref.WeakSet[TCallback] = weakref.WeakSet()
        self.methods_listeners: MutableSet[weakref.WeakMethod] = set()

    def add(self, callback: TCallback):
        def remove_method(method):
            self.methods_listeners.remove(method)

        if ismethod(callback):
            self.methods_listeners.add(weakref.WeakMethod(cast(MethodType, callback), remove_method))
        else:
            self.listeners.add(callback)

    def remove(self, callback: TCallback):
        if ismethod(callback):
            self.methods_listeners.remove(weakref.WeakMethod(cast(MethodType, callback)))
        else:
            self.listeners.remove(callback)

    def __iadd__(self, callback: TCallback):
        """Shortcut for using += to add a listener."""
        self.add(callback)
        return self

    def __isub__(self, callback: TCallback):
        self.remove(callback)
        return self

    async def __call__(self, *args, **kwargs):
        return await self.notify(*args, **kwargs)

    async def notify(self, *args, **kwargs):
        for listener in self.listeners:
            result = listener(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
        for listener in self.methods_listeners:
            result = listener()(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result

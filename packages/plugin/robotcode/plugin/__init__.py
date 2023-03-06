from typing import Any, Callable, TypeVar, cast

import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookimpl = cast(Callable[[F], F], pluggy.HookimplMarker("robotcode"))

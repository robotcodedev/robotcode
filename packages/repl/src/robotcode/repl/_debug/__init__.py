"""Synchronous, logger-driven Robot Framework debug core.

The `DebugController` consumes the keyword event stream (start/end) emitted by
the interpreter's logger (see `BaseInterpreter.register_observer`) and
drives pausing/stepping/inspection through a small `Frontend` protocol. It is
deliberate that this core knows nothing about threads, sockets, or DAP — those
are concerns of a particular front-end. The CLI front-end is the
`ConsoleInterpreter` itself (it implements `Frontend.wait_at_stop`).
"""

from .controller import DebugController
from .types import (
    Breakpoint,
    DebugTerminated,
    Frontend,
    ResumeAction,
    Scope,
    StackFrame,
    StopEvent,
    StopReason,
    Variable,
)

__all__ = [
    "Breakpoint",
    "DebugController",
    "DebugTerminated",
    "Frontend",
    "ResumeAction",
    "Scope",
    "StackFrame",
    "StopEvent",
    "StopReason",
    "Variable",
]

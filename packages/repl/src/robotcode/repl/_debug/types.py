"""Data model + front-end protocol for the debug core."""

import enum
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, runtime_checkable


class DebugTerminated(BaseException):
    """Raised when a front-end asks to terminate the run from a stop.

    A controller-level signal. Subclasses `BaseException` (not `Exception`) so
    it isn't caught by user/library ``except Exception`` handlers. Note: Robot's
    ``suite.run()`` swallows *any* exception raised from a logger callback, so
    this does NOT abort the run by unwinding on its own — the run-driver must
    translate it into an RF-native stop.
    """


class ResumeAction(enum.Enum):
    """What a front-end asks the core to do after a stop."""

    CONTINUE = "continue"
    STEP_IN = "step_in"
    STEP_OVER = "step_over"
    STEP_OUT = "step_out"
    UNTIL = "until"
    TERMINATE = "terminate"


class StopReason(enum.Enum):
    ENTRY = "entry"
    BREAKPOINT = "breakpoint"
    STEP = "step"
    PAUSE = "pause"
    EXCEPTION = "exception"


@dataclass
class StackFrame:
    """One entry of the keyword call stack.

    `name`/`type`/`source`/`line` are the display surface. `context` and
    `variables` are captured *at frame entry* (weakrefs) so per-frame variable
    inspection later sees the scope as it was when the frame started, not the
    current one.
    """

    name: str
    type: str
    source: Optional[str]
    line: Optional[int]
    depth: int
    executed: bool = True
    context: Any = field(default=None, repr=False, compare=False)
    variables: Any = field(default=None, repr=False, compare=False)

    @property
    def short_name(self) -> str:
        """The unqualified keyword name (drops the `Library.` prefix)."""
        return self.name.rsplit(".", 1)[-1]


@dataclass
class Breakpoint:
    """A registered breakpoint with optional attributes (the shared CLI + DAP model).

    `kind` is ``"line"`` (`source`+`line`) or ``"keyword"`` (`name`). The optional
    attributes drive the hit-time decision: `condition` (stop only if the
    expression is truthy — a *failing* condition stops too, so the breakage is
    noticed), `ignore_count` (skip the next N triggering hits), `log_message`
    (logpoint: log + continue, never stop), `temporary` (remove after it stops),
    `commands` (debugger commands replayed at the hit). `id` is a stable number
    for referencing the breakpoint (`.condition 2`, `.delete 2`, …).
    """

    id: int
    kind: str
    source: Optional[str] = None
    line: Optional[int] = None
    name: Optional[str] = None
    condition: Optional[str] = None
    ignore_count: int = 0
    log_message: Optional[str] = None
    temporary: bool = False
    enabled: bool = True
    commands: List[str] = field(default_factory=list)
    hits: int = 0


@dataclass
class StopEvent:
    reason: StopReason
    frame: StackFrame
    stack: List[StackFrame]
    description: str = ""
    breakpoint: Optional[Breakpoint] = None  # the breakpoint that triggered, if any


@dataclass
class Variable:
    """One variable in a scope — rendered name, value repr, and type name.

    Repr-only by design (the CLI never drills into values). A future DAP
    frontend will need lazy/nested expansion of dicts/lists/objects via a
    `variablesReference` adapter, which may add an optional live-value field here.
    """

    name: str
    value: str
    type: str


@dataclass
class Scope:
    """A named variable scope of a frame (`Local`/`Test`/`Suite`/`Global`).

    `variables` is already de-duplicated against the broader enclosing scopes,
    so `Local` shows only what the frame itself introduced, etc.
    """

    name: str
    variables: List[Variable]


@runtime_checkable
class Frontend(Protocol):
    """The seam between the synchronous debug core and a UI.

    `wait_at_stop` is called on the Robot Framework execution thread while the
    run is paused; it blocks until the front-end decides how to resume and
    returns that as a `ResumeAction`. A scripted/recording implementation makes
    the whole core deterministically testable.
    """

    def wait_at_stop(self, stop: StopEvent) -> ResumeAction: ...

    def on_output(self, text: str, category: str = "console") -> None: ...

    def on_continued(self) -> None: ...

    def on_exited(self, exit_code: int) -> None: ...

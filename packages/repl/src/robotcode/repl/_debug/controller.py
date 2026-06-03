"""The synchronous, logger-driven debug core.

Maintains the keyword call stack from the start/end event stream, matches
breakpoints, runs the stepping state machine, and — when execution should pause
— calls ``frontend.wait_at_stop(...)`` synchronously on the Robot Framework
thread, then resumes per the returned `ResumeAction`. No threads, no DAP.

Registered as an execution observer via ``BaseInterpreter.register_observer``.
"""

import contextlib
import re
import reprlib
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Iterator, List, Mapping, Optional, Set

from robot.running.context import EXECUTION_CONTEXTS
from robot.variables import evaluate_expression

from robotcode.core.utils.path import normalized_path
from robotcode.robot.utils import RF_VERSION

from ..base_interpreter import result_qualified_name
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

if TYPE_CHECKING:
    from robot import result, running

# Robot marks not-executed body items (e.g. the untaken branch of an IF) as
# "NOT RUN" already at the start hook (verified RF 5/6/7). The debugger must
# never pause on those, so frames carry an `executed` flag.
_NOT_RUN = "NOT RUN"
_FAIL = "FAIL"
_PASS = "PASS"

# Frame types that represent an actual keyword call. A control structure
# (TRY/FOR/IF/…) ending FAIL is just the failure propagating *through* it, not
# its origin — so only these types can trigger an exception stop. The strings
# are identical across RF 5/6/7 (verified).
_KEYWORD_FRAME_TYPES = frozenset({"KEYWORD", "SETUP", "TEARDOWN"})

# Setup/teardown run *during* a failure's unwind without ending it: the enclosing
# keyword still propagates the original failure afterwards. So a setup/teardown
# must not clear the exception-stop de-dup fence (unlike a genuinely fresh
# sibling keyword, which means the unwind is over). Strings stable across RF 5/6/7.
_SETUP_TEARDOWN_FRAME_TYPES = frozenset({"SETUP", "TEARDOWN"})

# BuiltIn keywords that catch a failure of the keyword(s) they run, so a FAIL
# beneath them is not an uncaught (run-aborting) exception. Matched by short
# name — `StackFrame.short_name` drops the `BuiltIn.` qualifier uniformly across
# versions (RF7 `full_name` vs RF<7 qualified `name`).
_CATCHING_KEYWORDS = frozenset(
    {
        "Run Keyword And Expect Error",
        "Run Keyword And Ignore Error",
        "Run Keyword And Warn On Failure",
        "Wait Until Keyword Succeeds",
        "Run Keyword And Continue On Failure",
        "Run Keyword And Return Status",
    }
)

# The `Breakpoint` marker keyword from `robotcode.repl.Repl` (see Repl/repl.py):
# the debugger stops where it runs. Its qualified name is stable across RF 5/6/7.
_BREAKPOINT_MARKER = "robotcode.repl.Repl.Breakpoint"

# Sentinel "stop at any depth" marker for step-in.
_ANY_DEPTH = 1 << 30

# Matches a SINGLE bare variable token (`${x}`, `@{x}`, `&{x}`, optional `[item]`).
# `[^{}]*` (not `.*`) keeps a multi-variable expression like `${a} + ${b}` out —
# it isn't one variable, so it falls through to expression evaluation.
_IS_VARIABLE_RE = re.compile(r"^[$@&]\{[^{}]*\}(\[[^\]]*\])?$")

# Keeps value reprs in the variable view bounded, so a giant list/dict/string
# can't flood a stop block.
_repr = reprlib.Repr()
_repr.maxstring = 500
_repr.maxlist = _repr.maxtuple = _repr.maxset = _repr.maxdeque = 50
_repr.maxdict = 500


# `evaluate_expression` takes the variable store directly from RF 6.1 on; before
# that it expects the inner `.store`.
if RF_VERSION >= (6, 1):

    def _evaluate_value(expression: str, store: Any) -> Any:
        return evaluate_expression(expression, store)

else:

    def _evaluate_value(expression: str, store: Any) -> Any:
        return evaluate_expression(expression, store.store)


def _normalize_source(source: str) -> str:
    return str(normalized_path(Path(source)))


class DebugController:
    def __init__(self, frontend: Optional[Frontend] = None) -> None:
        self._stack: List[StackFrame] = []
        self._frontend = frontend

        # breakpoints — a list of records with stable numeric ids (the shared
        # CLI + DAP model: condition / ignore-count / logpoint / temporary).
        self._breakpoints: List[Breakpoint] = []
        self._next_bp_id = 1
        # the breakpoint matched at the current stop (for `.commands` replay)
        self._stopped_breakpoint: Optional[Breakpoint] = None

        # stepping / pause state
        self._stepping: Optional[ResumeAction] = None
        self._step_stop_depth: int = 0
        # line of the paused frame when `.until` was issued (stop past it)
        self._until_line: Optional[int] = None
        self._stop_on_entry = False
        self._pause_requested = False

        # set while a keyword evaluated *at a stop* runs, so its nested events
        # don't re-trigger a pause (re-entrancy guard).
        self._suppressed = False

        # exception breakpoints: active filter ids (empty = disabled, the bare-
        # REPL default so a user's own `Fail` never pauses). `_fail_depth_floor`
        # fences the de-dup: while a stopped failure unwinds, every enclosing
        # keyword re-reports FAIL — we must stop once, at the innermost frame.
        self._exception_filters: Set[str] = set()
        self._fail_depth_floor: Optional[int] = None

        # set by `detach()` (the `.detach` command): stop pausing entirely so the
        # run finishes uninterrupted, without tearing down the run.
        self._detached = False

    # --- configuration ------------------------------------------------------

    def set_frontend(self, frontend: Optional[Frontend]) -> None:
        self._frontend = frontend

    def _add_breakpoint(self, **fields: Any) -> Breakpoint:
        bp = Breakpoint(id=self._next_bp_id, **fields)
        self._next_bp_id += 1
        self._breakpoints.append(bp)
        return bp

    def add_line_breakpoint(
        self,
        source: str,
        line: int,
        *,
        condition: Optional[str] = None,
        log_message: Optional[str] = None,
        temporary: bool = False,
    ) -> Breakpoint:
        return self._add_breakpoint(
            kind="line",
            source=_normalize_source(source),
            line=line,
            condition=condition,
            log_message=log_message,
            temporary=temporary,
        )

    def add_keyword_breakpoint(
        self,
        name: str,
        *,
        condition: Optional[str] = None,
        log_message: Optional[str] = None,
        temporary: bool = False,
    ) -> Breakpoint:
        return self._add_breakpoint(
            kind="keyword", name=name, condition=condition, log_message=log_message, temporary=temporary
        )

    def set_line_breakpoints(self, source: str, lines: List[int]) -> None:
        """Replace the line breakpoints for `source` (DAP-style per-source set)."""
        norm = _normalize_source(source)
        self._breakpoints = [bp for bp in self._breakpoints if not (bp.kind == "line" and bp.source == norm)]
        for line in lines:
            self.add_line_breakpoint(source, line)

    def set_keyword_breakpoints(self, names: List[str]) -> None:
        """Replace all keyword-name breakpoints."""
        self._breakpoints = [bp for bp in self._breakpoints if bp.kind != "keyword"]
        for name in names:
            self.add_keyword_breakpoint(name)

    def get_breakpoint(self, bp_id: int) -> Optional[Breakpoint]:
        return next((bp for bp in self._breakpoints if bp.id == bp_id), None)

    def remove_breakpoint(self, bp_id: int) -> bool:
        bp = self.get_breakpoint(bp_id)
        if bp is None:
            return False
        self._breakpoints.remove(bp)
        return True

    def set_exception_breakpoints(self, filters: Iterable[str]) -> None:
        """Arm exception breakpoints. Recognised filters: ``failed_keyword``
        (stop at every failing keyword) and ``uncaught_failed_keyword`` (only
        failures not caught by a wrapping ``TRY/EXCEPT`` or ``Run Keyword And
        …`` keyword). Empty disables exception stops entirely."""
        self._exception_filters = set(filters)

    def set_stop_on_entry(self, enabled: bool) -> None:
        self._stop_on_entry = enabled

    def detach(self) -> None:
        """Stop pausing for the rest of the run (the `.detach` command).

        Clears all breakpoints/stepping/exception filters and latches a flag so
        nothing — not even an embedded `Breakpoint` — pauses again. The run
        itself keeps going and finishes normally.
        """
        self._detached = True
        self._breakpoints.clear()
        self._exception_filters.clear()
        self._stepping = None
        self._stop_on_entry = False

    def request_pause(self) -> None:
        """Pause at the next executed keyword (on-demand pause)."""
        self._pause_requested = True

    @property
    def stack(self) -> List[StackFrame]:
        """Current call stack, outermost frame first."""
        return self._stack

    @property
    def breakpoints(self) -> List[Breakpoint]:
        """The registered breakpoints (the live list)."""
        return self._breakpoints

    @property
    def line_breakpoints(self) -> Dict[str, Set[int]]:
        """Active line breakpoints, keyed by normalised source path (derived)."""
        out: Dict[str, Set[int]] = {}
        for bp in self._breakpoints:
            if bp.kind == "line" and bp.source is not None and bp.line is not None:
                out.setdefault(bp.source, set()).add(bp.line)
        return out

    @property
    def keyword_breakpoints(self) -> Set[str]:
        """Active keyword-name breakpoints (derived)."""
        return {bp.name for bp in self._breakpoints if bp.kind == "keyword" and bp.name is not None}

    @property
    def exception_filters(self) -> Set[str]:
        """Active exception-breakpoint filter ids."""
        return self._exception_filters

    @contextlib.contextmanager
    def suppress_pausing(self) -> Iterator[None]:
        """Suppress pause decisions while a keyword evaluated *at a stop* runs.

        A front-end wraps its inline evaluation (running a keyword the user typed
        at the prompt) in this, so the evaluated keyword's own start/end events
        don't re-trigger a breakpoint or step. Re-entrant — nested evals nest.
        """
        previous = self._suppressed
        self._suppressed = True
        try:
            yield
        finally:
            self._suppressed = previous

    # --- inspection (per-frame scopes / variables) --------------------------

    def get_scopes(self, frame: StackFrame) -> List[Scope]:
        """The variable scopes visible from `frame`, narrowest-to-broadest.

        `Local` is the frame's own scope (captured at frame entry); `Test`,
        `Suite` and `Global` are read live from the shared execution context.
        Each scope is de-duplicated against the broader enclosing ones, so a
        value only shows in the innermost scope that introduces it.
        """
        context = self._deref(frame.context)
        variables = getattr(context, "variables", None)
        if variables is None:
            return []

        local_dict = self._as_dict(self._deref(frame.variables))
        test_store = getattr(variables, "_test", None)
        suite_store = getattr(variables, "_suite", None)
        global_store = getattr(variables, "_global", None)
        suite_dict = self._as_dict(suite_store)
        global_dict = self._as_dict(global_store)

        scopes: List[Scope] = []
        if frame.variables is not None and frame.variables() is not None:
            scopes.append(Scope("Local", self._diff(local_dict, self._parent_local_dict(frame, variables))))
        if test_store is not None:
            scopes.append(Scope("Test", self._diff(self._as_dict(test_store), suite_dict, visible=local_dict)))
        if suite_store is not None:
            scopes.append(Scope("Suite", self._diff(suite_dict, global_dict, visible=local_dict)))
        if global_store is not None:
            scopes.append(Scope("Global", self._diff(global_dict, {}, visible=local_dict)))
        return scopes

    def set_variable(self, frame: StackFrame, name: str, value: str, *, evaluate: bool = True) -> str:
        """Set `name` (e.g. ``${x}``) in `frame`'s scope; return the new repr.

        `value` is always variable-substituted. With ``evaluate=True`` (the
        default, matching the DAP debugger) it is then evaluated as a Robot
        expression so ``${y} + 1`` computes; with ``evaluate=False`` the
        substituted string is stored literally (the CLI ``.set`` behaviour,
        like ``Set Variable``). Raises ``NameError`` if the variable is unknown.
        """
        store = self._frame_store(frame)
        # The store is keyed by bare base name; `${x}` and `${x}[0]` both check
        # `x` (item assignment isn't supported and fails at the store below).
        key = name.split("}", 1)[0][2:] if _IS_VARIABLE_RE.match(name) else name
        if key not in store:
            raise NameError(f"Variable '{name}' not found.")

        substituted = store.replace_string(value)
        new_value = _evaluate_value(substituted, store) if evaluate else substituted
        store[name] = new_value
        return _repr.repr(new_value)

    def evaluate_expression(self, frame: StackFrame, expression: str) -> Any:
        """Evaluate `expression` in `frame`'s scope and return the value.

        A bare variable reference (``${x}``, ``@{x}``, ``${x}[0]``) returns the
        raw value with its type preserved (`replace_scalar` resolves item access
        too); anything else is variable-substituted then evaluated as a Robot
        expression (so ``${x} + 1`` works).
        """
        store = self._frame_store(frame)
        expression = expression.strip()
        if _IS_VARIABLE_RE.match(expression):
            return store.replace_scalar(expression)
        return _evaluate_value(store.replace_string(expression), store)

    def _frame_store(self, frame: StackFrame) -> Any:
        store = self._deref(frame.variables)
        if store is None:
            context = self._deref(frame.context)
            store = getattr(getattr(context, "variables", None), "current", None)
        if store is None:
            raise RuntimeError("no variable store available for this frame")
        return store

    # --- inspection helpers -------------------------------------------------

    @staticmethod
    def _deref(ref: Any) -> Any:
        return ref() if ref is not None else None

    @staticmethod
    def _as_dict(store: Any) -> Dict[str, Any]:
        if store is None:
            return {}
        try:
            return dict(store.as_dict())
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return {}

    def _parent_local_dict(self, frame: StackFrame, variables: Any) -> Dict[str, Any]:
        # The enclosing frame's captured local scope, else test/suite/global.
        index = next((i for i, f in enumerate(self._stack) if f is frame), -1)
        if index > 0:
            parent_store = self._deref(self._stack[index - 1].variables)
            if parent_store is not None:
                return self._as_dict(parent_store)
        for attr in ("_test", "_suite", "_global"):
            store = getattr(variables, attr, None)
            if store is not None:
                return self._as_dict(store)
        return {}

    @staticmethod
    def _diff(
        this: Mapping[str, Any],
        parent: Mapping[str, Any],
        visible: Optional[Mapping[str, Any]] = None,
    ) -> List[Variable]:
        result: List[Variable] = []
        for k, v in this.items():
            if visible is not None and k not in visible:
                continue
            try:
                if k in parent and parent[k] == v:
                    continue
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass
            result.append(Variable(name=k, value=_repr.repr(v), type=type(v).__name__))
        return result

    # --- keyword-observer interface (fed by the interpreter's logger) -------

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        self._refresh_parent_scope()
        frame = self._make_frame(data, result)

        # Fresh execution shallower than a fenced failure means its unwind is
        # over (e.g. a sibling keyword after a caught+continued fail); drop the
        # fence so a genuinely new failure can stop again. A setup/teardown
        # running mid-unwind is NOT the end of that unwind — the enclosing
        # keyword still propagates the original failure — so it must not clear
        # the fence (else that same failure stops again at each level above).
        if (
            not self._suppressed
            and self._fail_depth_floor is not None
            and len(self._stack) < self._fail_depth_floor
            and frame.type not in _SETUP_TEARDOWN_FRAME_TYPES
        ):
            self._fail_depth_floor = None

        self._stack.append(frame)

        if self._suppressed or not frame.executed:
            return

        reason = self._stop_reason(frame)
        if reason is not None:
            self._pause(reason, frame)

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self._stack:
            return
        frame = self._stack[-1]
        status = getattr(result, "status", None)
        if status == _FAIL:
            self._maybe_exception_stop(frame, result)  # may pause / raise DebugTerminated
        elif (
            status == _PASS
            and self._fail_depth_floor is not None
            and len(self._stack) <= self._fail_depth_floor
            and frame.type not in _SETUP_TEARDOWN_FRAME_TYPES
        ):
            # something at/above the fenced depth passed ⇒ the failure recovered
            # (e.g. a TRY/EXCEPT ROOT ending PASS); re-arm for later failures. A
            # passing setup/teardown is NOT a recovery (the failure still unwinds
            # through the enclosing keyword), so it doesn't clear the fence.
            self._fail_depth_floor = None
        self._stack.pop()

    # --- exception breakpoints ----------------------------------------------

    def _maybe_exception_stop(self, frame: StackFrame, result: "result.Keyword") -> None:
        if self._suppressed or not self._exception_filters:
            return
        # Only an actual keyword call is the origin of a failure; a control
        # structure ending FAIL is the same failure propagating through it.
        if not frame.executed or frame.type not in _KEYWORD_FRAME_TYPES:
            return
        # De-dup: a FAIL shallower than the fenced leaf is that same exception
        # unwinding through an enclosing keyword — already stopped at the leaf.
        if self._fail_depth_floor is not None and len(self._stack) < self._fail_depth_floor:
            return

        active = {"failed_keyword"}
        if self._is_uncaught():
            active.add("uncaught_failed_keyword")
        if not (active & self._exception_filters):
            return

        self._fail_depth_floor = len(self._stack)
        self._pause(StopReason.EXCEPTION, frame, self._exception_description(result))

    def _is_uncaught(self) -> bool:
        # Caught if wrapped by a `Run Keyword And …` catcher, or currently
        # inside the TRY branch of a TRY/EXCEPT (the TRY frame is on the stack
        # only while its body runs). Structural, not message-based — RF 5/6 give
        # no failure message at the end hook. Conservative: a TRY without a
        # matching EXCEPT is still treated as catching (favours no spurious stop).
        for frame in self._stack[:-1]:
            if frame.short_name in _CATCHING_KEYWORDS or frame.type == "TRY":
                return False
        return True

    @staticmethod
    def _exception_description(result: "result.Keyword") -> str:
        message = (getattr(result, "message", "") or "").strip()
        return f"Keyword failed: {message}" if message else "Keyword failed."

    # --- exception breakpoints: test / suite ends ---------------------------

    def start_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        # Push the SUITE frame so it sits at the bottom of the call stack (nested
        # suites stack in order). Popped in `end_suite`.
        self._stack.append(self._make_exec_frame(data, result, "SUITE"))

    def start_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        # Push the TEST frame above its suite; popped in `end_test`.
        self._stack.append(self._make_exec_frame(data, result, "TEST"))

    def end_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        self._end_exec(result, "failed_test")

    def end_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        self._end_exec(result, "failed_suite")

    def _end_exec(self, result: Any, filter_id: str) -> None:
        # The SUITE/TEST frame pushed at the matching start is on top of the stack.
        if not self._suppressed:
            # A test/suite end means any in-flight keyword unwind is over.
            self._fail_depth_floor = None
            if filter_id in self._exception_filters and getattr(result, "status", None) == _FAIL and self._stack:
                frame = self._stack[-1]
                self._pause(StopReason.EXCEPTION, frame, self._exec_description(frame.type, result))
        if self._stack:
            self._stack.pop()

    def _make_exec_frame(self, data: Any, result: Any, frame_type: str) -> StackFrame:
        name = getattr(result, "name", None) or getattr(data, "name", None) or frame_type
        source = getattr(data, "source", None) or getattr(result, "source", None)
        line = getattr(data, "lineno", None)
        if line is None:
            line = getattr(result, "lineno", None)
        context = EXECUTION_CONTEXTS.current
        context_ref = weakref.ref(context) if context is not None else None
        variables_ref: Optional[Any] = None
        if context is not None:
            try:
                variables_ref = weakref.ref(context.variables.current)
            except TypeError:
                variables_ref = None
        return StackFrame(
            name=str(name),
            type=frame_type,
            source=str(source) if source is not None else None,
            line=line,
            depth=len(self._stack),
            executed=True,
            context=context_ref,
            variables=variables_ref,
        )

    @staticmethod
    def _exec_description(frame_type: str, result: Any) -> str:
        label = "Test" if frame_type == "TEST" else "Suite"
        message = (getattr(result, "message", "") or "").strip()
        return f"{label} failed: {message}" if message else f"{label} failed."

    def _refresh_parent_scope(self) -> None:
        # The logger's start hook fires *before* Robot pushes a user keyword's
        # own variable scope (verified RF 5/6/7 — unlike listeners, which fire
        # after). So a frame's scope captured at *its* start is the caller's.
        # By the time its first child starts, `current` is the frame's own
        # scope — refresh the top-of-stack (the new child's parent) from it.
        if not self._stack:
            return
        context = EXECUTION_CONTEXTS.current
        if context is None:
            return
        try:
            self._stack[-1].variables = weakref.ref(context.variables.current)
            self._stack[-1].context = weakref.ref(context)
        except TypeError:
            pass

    # --- pause decision -----------------------------------------------------

    def _stop_reason(self, frame: StackFrame) -> Optional[StopReason]:
        if self._detached:
            return None
        if self._pause_requested:
            self._pause_requested = False
            return StopReason.PAUSE
        if self._breakpoint_stop(frame):
            return StopReason.BREAKPOINT
        if self._stepping is not None and self._stepping_stops(frame):
            return StopReason.STEP
        if self._stop_on_entry:
            self._stop_on_entry = False
            return StopReason.ENTRY
        return None

    def _stepping_stops(self, frame: StackFrame) -> bool:
        """Whether the active stepping mode wants to stop at `frame`."""
        if self._stepping == ResumeAction.UNTIL:
            # `.until`: stop when the frame returns (shallower) or a *later* line
            # in the same frame is reached — runs past the rest of the current
            # line (incl. loop iterations on the same line).
            if len(self._stack) < self._step_stop_depth:
                return True
            return (
                len(self._stack) == self._step_stop_depth
                and frame.line is not None
                and (self._until_line is None or frame.line > self._until_line)
            )
        # STEP_IN (_ANY_DEPTH) / STEP_OVER (same depth) / STEP_OUT (one shallower)
        return len(self._stack) <= self._step_stop_depth

    def _breakpoint_stop(self, frame: StackFrame) -> bool:
        """Whether `frame` triggers a breakpoint stop. Side effects: hit counting,
        logpoint emit (log + continue), one-shot removal; records the matched
        breakpoint in `_stopped_breakpoint` for the front-end (`.commands`)."""
        self._stopped_breakpoint = None
        if frame.name == _BREAKPOINT_MARKER:  # embedded `Breakpoint` keyword
            return True
        bp = self._match_breakpoint(frame)
        if bp is None:
            return False
        if bp.condition:
            try:
                triggered = bool(self.evaluate_expression(frame, bp.condition))
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                triggered = True  # a failing condition stops, so it gets noticed
            if not triggered:
                return False
        bp.hits += 1
        if bp.ignore_count and bp.hits <= bp.ignore_count:
            return False
        if bp.log_message is not None:  # logpoint: log + continue, never stop
            self._emit_logpoint(frame, bp.log_message)
            return False
        if bp.temporary:
            self._breakpoints.remove(bp)
        self._stopped_breakpoint = bp
        return True

    def _match_breakpoint(self, frame: StackFrame) -> Optional[Breakpoint]:
        for bp in self._breakpoints:
            if not bp.enabled:
                continue
            if bp.kind == "keyword" and bp.name in (frame.short_name, frame.name):
                return bp
            if (
                bp.kind == "line"
                and frame.source is not None
                and frame.line is not None
                and bp.source == _normalize_source(frame.source)
                and bp.line == frame.line
            ):
                return bp
        return None

    def _emit_logpoint(self, frame: StackFrame, message: str) -> None:
        try:
            text = self._frame_store(frame).replace_string(message)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            text = message
        if self._frontend is not None:
            self._frontend.on_output(text)

    def _pause(self, reason: StopReason, frame: StackFrame, description: str = "") -> None:
        if self._frontend is None:
            # No UI attached: keep running (don't block).
            self._stepping = None
            return
        stop = StopEvent(
            reason=reason,
            frame=frame,
            stack=list(self._stack),
            description=description,
            breakpoint=self._stopped_breakpoint,
        )
        action = self._frontend.wait_at_stop(stop)
        self._apply(action)
        self._frontend.on_continued()

    def _apply(self, action: ResumeAction) -> None:
        depth = len(self._stack)  # current (paused) frame is on the stack
        if action == ResumeAction.CONTINUE:
            self._stepping = None
        elif action == ResumeAction.STEP_IN:
            self._stepping = ResumeAction.STEP_IN
            self._step_stop_depth = _ANY_DEPTH
        elif action == ResumeAction.STEP_OVER:
            self._stepping = ResumeAction.STEP_OVER
            self._step_stop_depth = depth
        elif action == ResumeAction.STEP_OUT:
            self._stepping = ResumeAction.STEP_OUT
            self._step_stop_depth = depth - 1
        elif action == ResumeAction.UNTIL:
            self._stepping = ResumeAction.UNTIL
            self._step_stop_depth = depth
            self._until_line = self._stack[-1].line if self._stack else None
        elif action == ResumeAction.TERMINATE:
            raise DebugTerminated

    # --- frame construction (version-robust read of data/result) ------------

    def _make_frame(self, data: "running.Keyword", result: "result.Keyword") -> StackFrame:
        raw_type = getattr(data, "type", None) or getattr(result, "type", None) or "KEYWORD"
        # Keyword frames get their qualified name; control structures aren't
        # keywords (`result_qualified_name` returns None) so they're labelled by
        # type — `FOR`, `IF`, `RETURN`, …
        name = result_qualified_name(result) or raw_type

        source = getattr(data, "source", None)
        if source is None:
            source = getattr(result, "source", None)
        line = getattr(data, "lineno", None)
        if line is None:
            line = getattr(result, "lineno", None)
        status = getattr(result, "status", None)

        context = EXECUTION_CONTEXTS.current
        context_ref = weakref.ref(context) if context is not None else None
        variables_ref: Optional[Any] = None
        if context is not None:
            try:
                variables_ref = weakref.ref(context.variables.current)
            except TypeError:
                variables_ref = None

        return StackFrame(
            name=str(name),
            type=str(raw_type),
            source=str(source) if source is not None else None,
            line=line,
            depth=len(self._stack),
            executed=(status != _NOT_RUN),
            context=context_ref,
            variables=variables_ref,
        )

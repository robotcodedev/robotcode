"""Interactive Robot Framework interpreter — REPL prompt and CLI debugger.

The ``ConsoleInterpreter`` is the REPL's plain implementation: it wraps
Robot's runtime, reads lines from stdin (via ``input()``), routes
dot-commands through `@dot_command`-decorated methods, and emits log
output via ``click.style`` + ``app.echo``. The prompt_toolkit-aware
version overrides only the methods that benefit from prompt_toolkit's
richer surface (see ``prompt_toolkit_interpreter`` for that subclass).

It is also the debug core's `Frontend`: when a `DebugController` is
attached (`set_controller`), a pause calls `wait_at_stop`, which renders
the stop and runs a nested prompt over this same dot-command surface — so
the session commands (`.kw`, `.doc`, `.vars`, …) and the debugger commands
(`.step`, `.where`, `.print`, …) are one set, available at one prompt.
"""

import argparse
import inspect
import os
import pprint
import re
import reprlib
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, TypeVar, Union

import click
from robot import result, running
from robot.running import Keyword
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.plugin import Application
from robotcode.robot.diagnostics.library_doc import (
    REST_DOC_FORMAT,
    ROBOT_DOC_FORMAT,
    LibraryDoc,
    convert_from_rest,
    get_library_doc_from_library,
    get_resource_doc_from_resource,
)
from robotcode.robot.utils import get_robot_version_str
from robotcode.robot.utils.markdownformatter import MarkDownFormatter

from .__version__ import __version__
from ._debug.types import Breakpoint, ResumeAction, StackFrame, StopEvent
from ._indent import compute_indent
from ._keyword_lookup import (
    _LIB_KEYWORDS_ATTR,
    iter_keyword_owners,
    lookup_keyword_owner,
    lookup_library,
    lookup_resource,
)
from ._session_export import render_robot_file
from .base_interpreter import BaseInterpreter, is_true

if TYPE_CHECKING:
    from ._debug.controller import DebugController

F = TypeVar("F", bound=Callable[..., Any])

# Line shape: optional whitespace, dot, identifier, optional space + free-form rest.
# No Robot syntax legitimately starts with a dot, so the prefix is collision-free.
_COMMAND_RE = re.compile(r"^\s*\.(\w+)(?:\s+(.*))?$")

# A `.break` location of the form `path:line` (vs a bare keyword name).
_LINE_BREAK_RE = re.compile(r"^(?P<path>.+):(?P<line>\d+)$")

# `.catch` shorthands → exception-breakpoint filter ids.
_CATCH_SHORTHANDS = {
    "uncaught": "uncaught_failed_keyword",
    "uncaught_failed_keyword": "uncaught_failed_keyword",
    "all": "failed_keyword",
    "keyword": "failed_keyword",
    "failed_keyword": "failed_keyword",
    "test": "failed_test",
    "failed_test": "failed_test",
    "suite": "failed_suite",
    "failed_suite": "failed_suite",
}

# REPL-only setting-import aliases: a top-level `Library`/`Resource`/`Variables`
# keyword call (the `*** Settings ***` muscle-memory form) is rewritten to the
# matching BuiltIn `Import …` keyword. (`_session_export._IMPORT_HEADS` knows the
# same bare names so `.save` hoists them back into a `*** Settings ***` block.)
_SETTING_IMPORT_ALIASES = {
    "library": "Import Library",
    "resource": "Import Resource",
    "variables": "Import Variables",
}

# `.help` groups, in display order. A command's group is set on `@dot_command`.
_GROUP_ORDER = ("Session", "Debugger")

# Compact value rendering for `.print` / evaluation results.
_repr = reprlib.Repr()
_repr.maxstring = 200
_repr.maxother = 200
_repr.maxlist = _repr.maxtuple = _repr.maxset = _repr.maxdeque = 20
_repr.maxdict = 50


def dot_command(name: str, *aliases: str, group: str = "Session") -> Callable[[F], F]:
    """Mark a ``ConsoleInterpreter`` method as a dot-command handler.

    Method signature: ``def _name(self, arg: str) -> None``. ``name`` is
    the canonical long form (eligible for prefix abbreviation in the
    dispatcher); ``aliases`` are exact short forms that always win
    (``.exit`` / ``.quit``, ``.continue`` / ``.c``). ``group`` places the
    command in a `.help` section. The first non-blank docstring line is
    the ``.help`` summary; the full docstring is shown by ``.help <name>``.
    """

    def decorator(method: F) -> F:
        method._dot_command = (name, aliases, group)  # type: ignore[attr-defined]
        return method

    return decorator


# Variables that Robot itself sets in every suite — filtered out by
# `.vars --user` so the listing focuses on what the user assigned.
# Robot's built-in variables, matched by exact name or a `<PREFIX>_` / `<PREFIX> `
# boundary (see `_is_robot_internal`) so a user variable like `${TESTDATA}` is NOT
# mistaken for an internal one just because it starts with `TEST`.
_ROBOT_INTERNAL_PREFIXES = (
    "CURDIR",
    "DEBUG_FILE",
    "EXECDIR",
    "FAILED",
    "KEYWORD",
    "LOG",
    "OPTIONS",
    "OUTPUT",
    "PASSED",
    "PREV",
    "REPORT",
    "ROBOT",
    "SPACE",
    "SUITE",
    "TASK",
    "TEMPDIR",
    "TEST",
    "TIMEOUT",
)


def _is_robot_internal(bare: str) -> bool:
    """Whether a bare variable name is one of Robot's built-ins (boundary match)."""
    return any(bare == p or bare.startswith((p + "_", p + " ")) for p in _ROBOT_INTERNAL_PREFIXES)


# Destructive commands that must never be reachable via prefix abbreviation — only
# their full long name resolves, so a stray `.a`/`.ab` can't abort the run.
_NO_PREFIX_ABBREV = frozenset({"abort"})


def _format_doc_to_md(text: str, doc_format: str) -> str:
    """Convert a Robot docstring body to Markdown.

    ``ROBOT`` and ``REST`` formats go through their respective
    converters; anything else (``TEXT``, custom) passes through.
    """
    if doc_format == ROBOT_DOC_FORMAT:
        return MarkDownFormatter().format(text)
    if doc_format == REST_DOC_FORMAT:
        return convert_from_rest(text)
    return text


def _diagnostics_keyword_doc(owner: Any, is_resource: bool, kw_name: str) -> Optional[Any]:
    """The diagnostics `KeywordDoc` for `kw_name` from a loaded owner.

    The runtime keyword object (a `StaticKeyword` on RF 7+, an old-style
    handler before that) carries `name` / `args` / `doc` strings but no
    `to_markdown`. The diagnostics `KeywordDoc` does, with proper
    signature + arg table rendering. We get it by converting the
    already-loaded `owner` instance in place — no reimport or re-parse —
    and looking the keyword up by name (which also matches embedded
    keywords). Returns ``None`` when the conversion or lookup fails, so
    the caller can fall back to a runtime-only rendering.
    """
    try:
        lib_doc: LibraryDoc = (
            get_resource_doc_from_resource(owner)
            if is_resource
            else get_library_doc_from_library(owner, name=str(owner.name))
        )
        matches = list(lib_doc.keywords.get_all(kw_name))
    except Exception:
        return None
    return matches[0] if matches else None


def _render_runtime_keyword_md(kw: Any, kw_name: str) -> str:
    """Hand-built fallback keyword page for resources / dynamic libs.

    Used only when the diagnostics loader can't surface a `KeywordDoc`
    for this keyword. Renders name + signature + tags + doc + source
    in a shape close to what `KeywordDoc.to_markdown` produces.
    """
    md: List[str] = [f"### {kw_name}", ""]

    spec = getattr(kw, "args", None) or getattr(kw, "arguments", None)
    if spec is not None:
        try:
            sig = str(spec)
        except Exception:
            sig = ""
        if sig:
            md.append(f"`{kw_name}    {sig}`")
            md.append("")

    tags = list(getattr(kw, "tags", None) or [])
    if tags:
        md.append("_Tags: " + ", ".join(str(t) for t in tags) + "_")
        md.append("")

    doc = getattr(kw, "doc", None) or ""
    if doc:
        md.append(_format_doc_to_md(doc, getattr(kw, "doc_format", ROBOT_DOC_FORMAT)))

    source = getattr(kw, "source", None)
    if source:
        md.append("")
        md.append(f"_Source: {source}_")
    return "\n".join(md)


def _first_doc_line(method: Any) -> str:
    """First non-blank line of a method's docstring — used as the
    `.help` summary."""
    doc = inspect.getdoc(method) or ""
    for line in doc.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _split_command_args(arg: str) -> List[str]:
    """Tokenise a dot-command argument string the way shells do — but
    keep backslashes literal so Windows paths (``C:\\Users\\…``) survive
    unmangled. Quotes still work for spaces in paths."""
    lex = shlex.shlex(arg, posix=True)
    lex.whitespace_split = True
    lex.escape = ""
    lex.commenters = ""
    return list(lex)


def _build_save_parser() -> argparse.ArgumentParser:
    # `exit_on_error=False` so a bad invocation reports "Usage: …" via
    # `_save` instead of tearing down the REPL on argparse's sys.exit.
    p = argparse.ArgumentParser(prog=".save", add_help=False, exit_on_error=False)
    p.add_argument("-a", "--append", action="store_true", help="Append to FILENAME instead of overwriting.")
    p.add_argument("-t", "--test-name", default="", help="Override the generated test-case name.")
    p.add_argument("filename")
    return p


class ConsoleInterpreter(BaseInterpreter):
    """Plain-mode interactive Robot Framework interpreter.

    `read_line` calls `input()`, `show_doc` falls through to
    `app.echo_via_pager(..., color=False)`. `PromptToolkitConsoleInterpreter`
    overrides both to drive a prompt_toolkit `Application`.

    Constructor takes no ``backend`` argument — the choice is made
    one level up in `cli.py` by picking either this class or the
    prompt_toolkit subclass. `no_history` is accepted here so the
    signature stays uniform between the two interpreters, but the
    plain implementation has nothing to persist.
    """

    # The prompt shown while paused at a debug stop (vs the `>>> ` REPL prompt).
    DEBUG_PROMPT = "(rdb) "

    # Whether `show_doc` opens a scrollable fullscreen viewer (prompt_toolkit) vs
    # plain inline/paged output. `.source` uses it to pick the viewer or an inline
    # window. Overridden to True in `PromptToolkitConsoleInterpreter`.
    has_scrollable_viewer = False

    def __init__(
        self,
        app: Optional[Application],
        files: Optional[List[Path]] = None,
        show_keywords: bool = False,
        inspect: Optional[bool] = False,
        no_history: bool = False,
    ) -> None:
        del no_history  # plain mode has no history file to honour the flag against
        super().__init__()

        self.app = app
        self.files = files
        self.show_keywords = show_keywords
        self.inspect = inspect

        self.executed_files: List[Path] = []
        # REPL inputs that parsed cleanly — `.save` exports them as a
        # runnable `.robot` file. Each entry may be multi-line.
        self._session_lines: List[str] = []

        # Debug-frontend state. `_controller`/`_debug_completer` are wired by
        # `set_controller` when a debugger is attached; `_stop`/`_frame_no`/
        # `_pending_action` are managed by `wait_at_stop` and are meaningful only
        # while paused at a stop. The debugger dot-commands act on these.
        self._controller: Optional["DebugController"] = None
        self._stop: Optional[StopEvent] = None
        self._frame_no = 0  # selected frame in the backtrace, #0 = innermost
        self._pending_action: Optional[ResumeAction] = None
        # Expressions registered with `.display`, auto-evaluated + shown at every
        # stop until `.undisplay` (persistent across the run).
        self._display_exprs: List[str] = []
        # Frame-aware completer for the debug prompt (None in plain mode).
        self._debug_completer: Any = None

    # ------------------------------------------------------------------
    # Dot-command dispatch — the table is computed once per interpreter
    # class (`cls.__dict__.get` skips the base's cache when looking from
    # a subclass, so `PromptToolkitConsoleInterpreter` builds its own
    # the first time `.history` is dispatched).
    # ------------------------------------------------------------------

    @classmethod
    def _dot_command_table(cls) -> Dict[str, str]:
        """Per-class ``{name: method_attr_name}`` for every ``@dot_command`` name
        (long form *and* aliases). Derived from `_dot_command_index` so the
        command set has a single source of truth."""
        long_to_attr, alias_to_long, _s, _g, _a = cls._dot_command_index()
        table = dict(long_to_attr)
        for alias, long in alias_to_long.items():
            table[alias] = long_to_attr[long]
        return table

    @classmethod
    def _dot_command_index(
        cls,
    ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str], Dict[str, str], Dict[str, List[str]]]:
        """Per-class ``(long->attr, alias->long, long->summary, long->group,
        long->aliases)`` — drives resolution and the grouped `.help` listing."""
        cached = cls.__dict__.get("_DOT_COMMAND_INDEX")
        if cached is not None:
            return cached  # type: ignore[no-any-return]
        long_to_attr: Dict[str, str] = {}
        alias_to_long: Dict[str, str] = {}
        summaries: Dict[str, str] = {}
        groups: Dict[str, str] = {}
        aliases_of: Dict[str, List[str]] = {}
        for klass in reversed(cls.__mro__):
            for attr_name, attr in vars(klass).items():
                spec = getattr(attr, "_dot_command", None)
                if spec is None:
                    continue
                long, aliases, group = spec
                long_to_attr[long] = attr_name
                summaries[long] = _first_doc_line(attr)
                groups[long] = group
                aliases_of[long] = list(aliases)
                for alias in aliases:
                    alias_to_long[alias] = long
        index = (long_to_attr, alias_to_long, summaries, groups, aliases_of)
        cls._DOT_COMMAND_INDEX = index  # type: ignore[attr-defined]
        return index

    def _resolve_dot_command(self, token: str) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a command token to a method attr name, or an error message.

        Exact short aliases win first, then exact long names, then unambiguous
        prefix abbreviation of a long name. Destructive commands (`.abort`) are
        excluded from prefix abbreviation so a stray `.a`/`.ab` can't kill the run
        — they must be spelled in full.
        """
        long_to_attr, alias_to_long, _s, _g, _a = type(self)._dot_command_index()
        if token in alias_to_long:
            return long_to_attr[alias_to_long[token]], None
        if token in long_to_attr:
            return long_to_attr[token], None
        matches = sorted(ln for ln in long_to_attr if ln.startswith(token) and ln not in _NO_PREFIX_ABBREV)
        if len(matches) == 1:
            return long_to_attr[matches[0]], None
        if len(matches) > 1:
            return None, f"Ambiguous dot-command .{token} — matches: {', '.join('.' + m for m in matches)}"
        return None, f"Unknown dot-command: .{token}. Try .help."

    def _dispatch_dot_command(self, line: str) -> bool:
        """Run ``line`` as a dot-command. Returns ``True`` when the line
        matched the dot-command shape (handled or unknown — caller treats
        it as consumed), ``False`` when ``line`` is a normal Robot step.
        """
        m = _COMMAND_RE.match(line)
        if not m:
            return False
        name = m.group(1)
        arg = (m.group(2) or "").strip()
        attr_name, error = self._resolve_dot_command(name)
        if attr_name is None:
            if self.app is not None:
                self.app.echo(error or f"Unknown dot-command: .{name}. Try .help.")
            return True
        getattr(self, attr_name)(arg)
        return True

    # ------------------------------------------------------------------
    # I/O — the prompt_toolkit subclass overrides both to drive its own
    # Application; the plain implementation here uses stdlib `input()`
    # and pages markdown through the Application's pager helper.
    # ------------------------------------------------------------------

    def read_line(
        self, prompt: str, *, multiline_continuation: bool = False, prefill: str = "", completer: Any = None
    ) -> str:
        del multiline_continuation, prefill, completer  # no editor/prefill/completion in plain mode
        return input(prompt)

    def make_completer(
        self, command_names: List[str], context_provider: Callable[[], Tuple[Any, Any]]
    ) -> Optional[Any]:
        """Build a completer for a nested debug prompt. Plain mode has none —
        the prompt_toolkit subclass returns a frame-aware `_RobotCompleter`."""
        del command_names, context_provider
        return None

    def show_doc(self, title: str, markdown: str, *, scroll_to: Optional[str] = None) -> None:
        """Display markdown to the user.

        Plain mode pages the raw markdown source with colour off — the
        backend choice signals "low-fi terminal", so we don't surface
        rich-rendered markdown the user explicitly opted out of. The
        prompt_toolkit interpreter overrides this with the scrollable
        doc-viewer Float. ``scroll_to`` is honoured only by that viewer;
        the pager ignores it.
        """
        del scroll_to  # only the scrollable viewer (prompt_toolkit) uses it
        body = f"{title}\n{'=' * len(title)}\n\n{markdown}"
        if self.app is not None:
            self.app.echo_via_pager(body, color=False)

    def show_banner(self) -> None:
        """Print a Python-REPL-style banner before the first prompt.

        Skipped when stdin isn't a TTY (input piped/redirected) or
        when running non-interactively from ``--files`` without
        ``--inspect`` — neither case ever reaches an interactive prompt.
        """
        if self.app is None or not sys.stdin.isatty():
            return
        if self.files and not self.inspect:
            return

        py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        rf = get_robot_version_str()
        header = f"RobotCode REPL {__version__} (Robot Framework {rf}, Python {py} on {sys.platform})"
        self.app.echo(click.style(header, bold=True))
        self.app.echo('Type ".help" for commands, ".exit" to quit.')

    def run(self) -> Any:
        self.show_banner()
        # Seed ``${_}`` so it resolves to ``None`` even before the first
        # keyword runs, rather than raising "Variable not found".
        self.set_last_result(None)
        return super().run()

    # ------------------------------------------------------------------
    # Debug frontend — the interpreter *is* the debug core's `Frontend`.
    # A pause calls `wait_at_stop`, which renders the stop and runs a
    # nested prompt over the same dot-command surface as the REPL.
    # ------------------------------------------------------------------

    def set_controller(self, controller: "DebugController") -> None:
        """Attach the debug controller and build the debug-prompt completer.

        The completer offers the dot-commands (canonical long names) plus
        keyword/variable completion against the *selected* frame (plain mode
        has none).
        """
        self._controller = controller
        self._debug_completer = self.make_completer(
            list(type(self)._dot_command_index()[0]), self._debug_completer_context
        )

    def wait_at_stop(self, stop: StopEvent) -> ResumeAction:
        """Render the stop, then run a nested prompt until the user resumes.

        Dot-commands route through the shared dispatcher; the debugger
        commands (`.continue`/`.step`/…) set `_pending_action`, which ends
        the loop. Anything else is evaluated as a keyword in the paused
        context. EOF / Ctrl-C at the prompt continues the run.
        """
        self._stop = stop
        self._frame_no = 0  # innermost frame selected
        self._pending_action = None
        # A breakpoint with attached `.commands` replays them at the hit; a
        # leading `silent` suppresses the stop banner (pdb semantics).
        bp = stop.breakpoint
        silent = bool(bp is not None and bp.commands and bp.commands[0] == "silent")
        if not silent:
            self._render_stop(stop)
        # try/finally so the stop state is always cleared, even if `.abort`
        # (SystemExit) or a Ctrl-C during an at-stop evaluation unwinds through
        # the loop — otherwise a stale `_stop` would leave the interactive shell
        # prompt wedged in a phantom debug state after the run returns.
        try:
            if bp is not None and bp.commands:
                self._replay_commands(bp.commands)
            while self._pending_action is None:
                try:
                    line = self.read_line(self.DEBUG_PROMPT, completer=self._debug_completer)
                except (EOFError, KeyboardInterrupt):
                    self._echo("")
                    self._pending_action = ResumeAction.CONTINUE
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    if line.startswith("."):
                        self._dispatch_dot_command(line)
                    else:
                        self._evaluate_at_stop(line)
                except Exception as e:  # a throwing command must not eject the debug prompt
                    # `.abort` (SystemExit), Ctrl-C, and DebugTerminated are
                    # BaseException, not Exception, so they still propagate.
                    self._echo(f"! {e}")
            return self._pending_action
        finally:
            self._stop = None
            self._pending_action = None

    def _replay_commands(self, commands: List[str]) -> None:
        """Replay a breakpoint's attached commands at the stop (pdb `commands`).

        `silent` (first entry) only suppresses the banner; a resuming command
        (`.continue`/`.step`/…) sets `_pending_action` and ends the replay so the
        run continues without an interactive prompt."""
        for cmd in commands:
            if cmd == "silent" or self._pending_action is not None:
                continue
            if cmd.startswith("."):
                self._dispatch_dot_command(cmd)
            else:
                self._evaluate_at_stop(cmd)

    def on_output(self, text: str, category: str = "console") -> None:
        del category
        self._echo(text)

    def on_continued(self) -> None:
        pass

    def on_exited(self, exit_code: int) -> None:
        pass

    # --- debug prompt helpers ----------------------------------------------

    def _echo(self, text: str) -> None:
        if self.app is not None:
            self.app.echo(text)

    def _require_stop(self) -> bool:
        """Guard for commands that only mean something while paused."""
        if self._stop is None:
            self._echo("not at a breakpoint")
            return False
        return True

    def _require_controller(self) -> bool:
        """Guard for commands that need a wired debug controller. (Distinct from
        the attach/detach *state* — a detached controller is still wired.)"""
        if self._controller is None:
            self._echo("no debugger available")
            return False
        return True

    def _debug_completer_context(self) -> Tuple[Any, Any]:
        """`(namespace_context, variables_store)` for the selected frame — what
        the debug completer completes keywords/variables against."""
        if self._stop is None:
            return (None, None)
        frame = self._selected_frame()
        context = frame.context() if frame.context is not None else None
        variables = frame.variables() if frame.variables is not None else None
        return (context, variables)

    @staticmethod
    def _location(frame: StackFrame) -> str:
        if frame.source is None:
            return ""
        try:
            path = os.path.relpath(frame.source)
        except ValueError:  # e.g. a different drive than the cwd on Windows
            path = frame.source
        return f"{path}:{frame.line}" if frame.line is not None else path

    def _render_stop(self, stop: StopEvent) -> None:
        self._echo("")  # break off any in-progress runner console status line
        parts = [f"* {stop.reason.value}", stop.frame.name]
        loc = self._location(stop.frame)
        if loc:
            parts.append(f"({loc})")
        line = "  ".join(parts)
        if stop.description:
            line += f"  — {stop.description}"
        self._echo(line)
        self._show_displays()

    def _show_displays(self) -> None:
        """Auto-evaluate the `.display` expressions in the selected frame at a stop."""
        if not self._display_exprs or self._controller is None:
            return
        frame = self._selected_frame()
        for expr in self._display_exprs:
            try:
                value = self._controller.evaluate_expression(frame, expr)
            except Exception as e:  # a display must never break the stop render
                self._echo(f"{expr} = ! {e}")
            else:
                self._echo(f"{expr} = {_repr.repr(value)}")

    def _source_window_lines(
        self, source: Optional[str], line: Optional[int], *, before: Optional[int] = 5, after: Optional[int] = 5
    ) -> Optional[List[str]]:
        """Numbered source lines around `line`, marking `line` with `->`.

        `before`/`after` bound the window; ``None`` means unbounded in that
        direction (`before=None` → from line 1; `after=None` → to EOF — used to
        load a whole file into the viewer). Returns ``None`` (after echoing a
        short message) when the source path/line is missing, the file can't be
        read, or `line` is past EOF."""
        if not source or line is None:
            self._echo("(no source available)")
            return None
        try:
            text = Path(source).read_text(encoding="utf-8")
        except OSError as e:
            self._echo(f"(source unavailable: {e})")
            return None
        file_lines = text.splitlines()
        if line > len(file_lines):
            self._echo(f"(line {line} is beyond the end of {os.path.basename(source)})")
            return None
        start = 1 if before is None else max(1, line - before)
        end = len(file_lines) if after is None else min(len(file_lines), line + after)
        return [f"{'->' if n == line else '  '} {n:>4}  {file_lines[n - 1]}" for n in range(start, end + 1)]

    def _render_source_window(
        self, source: Optional[str], line: Optional[int], *, before: int = 5, after: int = 5
    ) -> None:
        """Echo a `[line-before, line+after]` window of `source`, marking `line`.

        `.list` centers on the current stop (±5). `.source` (plain backend) starts
        at a keyword's definition line (`before=0`) and shows the body downward."""
        for text_line in self._source_window_lines(source, line, before=before, after=after) or []:
            self._echo(text_line)

    def _selected_frame(self) -> StackFrame:
        stack = self._stop.stack  # type: ignore[union-attr]  # only called while stopped
        return stack[len(stack) - 1 - self._frame_no]

    def _frame_line(self, frame_no: int, frame: StackFrame, width: int) -> str:
        marker = ">" if frame_no == self._frame_no else " "
        return f"{marker} #{frame_no}  {frame.name:<{width}}  {self._location(frame)}".rstrip()

    def _move_frame(self, frame_no: int) -> None:
        stack = self._stop.stack if self._stop else []
        if not stack:
            return
        self._frame_no = max(0, min(frame_no, len(stack) - 1))
        width = max(len(f.name) for f in stack)
        self._echo(self._frame_line(self._frame_no, self._selected_frame(), width))

    def _evaluate_at_stop(self, line: str) -> None:
        """Run `line` as Robot keyword(s) in the paused context.

        Wrapped in `suppress_pausing()` so the evaluated keyword's own events
        don't re-trigger a stop, and in `forward_events(echo_messages=True)` so
        its log output surfaces at the prompt (suite output is muted otherwise).
        """
        try:
            test, errors = self.get_test_body_from_string(line)
        except Exception as e:  # surface any parse failure to the prompt
            self._echo(f"! {e}")
            return
        if errors:
            for err in errors:
                self._echo(f"! {err}")
            return
        if not test.body:
            return
        with self._controller.suppress_pausing(), self.forward_events(echo_messages=True):  # type: ignore[union-attr]
            for kw in test.body:
                self.set_last_result(self.run_keyword(kw))
        self._echo(f"=> {_repr.repr(self.last_result)}")

    # ------------------------------------------------------------------
    # Robot integration
    # ------------------------------------------------------------------

    def set_last_result(self, result: Any) -> None:
        """Mirror the last keyword's return value into Robot as ``${_}``.

        Every keyword updates ``${_}`` — including those returning
        ``None`` (e.g. ``Log``), so ``${_}`` always reflects the most
        recent keyword's result rather than the last non-``None`` one.
        """
        super().set_last_result(result)
        ctx = EXECUTION_CONTEXTS.current
        if ctx is None:
            return
        try:
            ctx.variables["${_}"] = result
        except Exception:
            # Locked scope / shutdown phase — drop the binding rather
            # than crash the REPL.
            pass

    def _alias_setting_imports(self, test: "running.TestCase") -> None:
        """REPL-only: rewrite top-level ``Library`` / ``Resource`` / ``Variables``
        keyword calls into the BuiltIn ``Import …`` keywords.

        Lets ``*** Settings ***`` muscle memory (``Library    Browser``) work at
        the ``>>>`` prompt — both for a single line and for every import line of
        a multi-line / file input. Applied only on this interactive/file input
        path; the ``(rdb)`` prompt parses via ``_evaluate_at_stop`` and is
        intentionally *not* aliased.
        """
        for item in test.body:
            if isinstance(item, Keyword) and item.name is not None:
                target = _SETTING_IMPORT_ALIASES.get(item.name.strip().lower())
                if target is not None:
                    item.name = target

    def get_input(self) -> Iterator[Optional[Keyword]]:
        if self.executed_files and not self.files and not self.inspect:
            raise EOFError

        if self.files:
            file = self.files.pop(0)

            self.executed_files.append(file)

            text = file.read_text(encoding="utf-8")

            test, errors = self.get_test_body_from_string(text)
            if errors:
                return

            self._alias_setting_imports(test)
            for kw in test.body:
                yield kw
        else:
            lines: List[str] = []
            last_one = False
            while True:
                prompt = ""
                if sys.stdin.isatty():
                    prompt = ">>> " if not lines else "... "

                prefill = compute_indent(lines) if lines else ""
                try:
                    text = self.read_line(
                        prompt,
                        multiline_continuation=bool(lines),
                        prefill=prefill,
                    )
                    if len(lines) == 0 and text == "":
                        break
                    # Only at the start of a fresh input — inside a
                    # multi-line block `.foo` could be a user keyword
                    # name and shouldn't be shadowed.
                    if not lines and text.lstrip().startswith(".") and self.app is not None:
                        if self._dispatch_dot_command(text):
                            return
                except KeyboardInterrupt:
                    if len(lines) > 0:
                        lines = []
                        last_one = False
                        continue
                    raise

                lines.append(text)

                test, errors = self.get_test_body_from_string("\n".join(lines))

                if len(lines) > 1 and lines[-1] == "" and text == "":
                    last_one = True

                if errors:
                    if not last_one:
                        continue

                # Record cleanly-parsed inputs for `.save`. Error-only
                # inputs are skipped so the exported file stays runnable.
                if test.body:
                    self._session_lines.append("\n".join(lines))

                self._alias_setting_imports(test)
                for kw in test.body:
                    yield kw

                break

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        if self.app is None:
            return

        if not self.app.config.verbose and level in ["DEBUG", "TRACE"]:
            return

        std_err = level in ["ERROR", "FAIL"]

        if level == "INFO":
            level = click.style("INFO", fg="green")
        elif level == "WARN":
            level = click.style("WARN", fg="yellow")
        elif level == "ERROR":
            level = click.style("ERROR", fg="red")
        elif level == "FAIL":
            level = click.style("FAIL", fg="red", bold=True)
        elif level == "SKIP":
            level = click.style("SKIP", dim=True)
        elif level == "DEBUG":
            level = click.style("DEBUG", fg="bright_black")
        elif level == "TRACE":
            level = click.style("TRACE", fg="bright_black", dim=True)

        if is_true(html):
            message = f"*HTML*{message}"

        self.app.echo(f"{'  ' * self.indent}[ {level} ] {message}", file=sys.__stderr__ if std_err else sys.__stdout__)

    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        if self.app is not None and self.app.config.verbose:
            self.log_message(message, level, html, timestamp)

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self.show_keywords:
            return

        if self.app is None:
            return

        self.app.echo(
            f"{'  ' * self.indent}KEYWORD {result.libname}.{result.kwname}  {'  '.join(result.args)}",
            file=sys.__stdout__,
        )
        self.indent += 1

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self.show_keywords:
            return

        if self.app is None:
            return

        self.indent -= 1

    # ------------------------------------------------------------------
    # Dot-command handlers — registered via `@dot_command` and dispatched
    # through `_dispatch_dot_command` above.
    # ------------------------------------------------------------------

    @dot_command("help")
    def _help(self, arg: str) -> None:
        """List dot-commands. `.help <cmd>` shows details for one.

        Without an argument: print the summary table of all dot-commands.
        With an argument: print the detailed help for that command (the
        leading dot is optional).

        Examples:
          .help
          .help save
          .help .history
        """
        long_to_attr, _alias_to_long, summaries, groups, aliases_of = type(self)._dot_command_index()
        target = arg.strip().lstrip(".")
        if target:
            attr_name, error = self._resolve_dot_command(target)
            if attr_name is None:
                if self.app is not None:
                    self.app.echo(error or f"Unknown dot-command: .{target}. Try .help.")
                return
            method = getattr(self, attr_name)
            detail = inspect.getdoc(method) or "(no further details)"
            summary = _first_doc_line(method)
            body = f"**{summary}**\n\n```\n{detail}\n```"
            long = next((ln for ln, at in long_to_attr.items() if at == attr_name), target)
            self.show_doc(f".{long}", body)
            return

        by_group: Dict[str, List[str]] = {}
        for long in long_to_attr:
            by_group.setdefault(groups[long], []).append(long)

        md_lines: List[str] = ["## Dot-commands", ""]
        for group in (*_GROUP_ORDER, *sorted(g for g in by_group if g not in _GROUP_ORDER)):
            longs = by_group.get(group)
            if not longs:
                continue
            md_lines.append(f"### {group}")
            for long in sorted(longs):
                alias_str = ", ".join(f"`.{a}`" for a in sorted(aliases_of.get(long, [])))
                head = f"`.{long}`" + (f" ({alias_str})" if alias_str else "")
                md_lines.append(f"- {head} — {summaries[long] or '(no description)'}")
            md_lines.append("")
        md_lines.append("Type `.help <command>` for usage details.")
        md_lines.append("")
        md_lines.append("**Shortcuts**: F1=help · Tab=complete · ^R=search · ^L=clear · ^D=exit")
        self.show_doc("Dot-commands", "\n".join(md_lines))

    @dot_command("imports")
    def _imports(self, arg: str) -> None:
        """List loaded libraries and resource files.

        List every library and resource file the active REPL session has
        imported, along with the number of keywords each contributes and
        its source path.

        Usage:
          .imports
        """
        del arg
        if self.app is None:
            return
        ctx = EXECUTION_CONTEXTS.current
        if ctx is None:
            self.app.echo("(no active context)")
            return
        store = getattr(ctx.namespace, "_kw_store", None)
        if store is None:
            self.app.echo("(no keyword store)")
            return

        rows: List[Tuple[str, str, str, int]] = []
        for src in store.libraries.values():
            name = str(getattr(src, "name", "?"))
            source = str(getattr(src, "source", None) or "(built-in)")
            kws = list(getattr(src, _LIB_KEYWORDS_ATTR, ()) or ())
            rows.append(("Library", name, source, len(kws)))
        for src in store.resources.values():
            name = str(getattr(src, "name", "?"))
            source = str(getattr(src, "source", None) or "?")
            kws = list(getattr(src, _LIB_KEYWORDS_ATTR, ()) or ())
            rows.append(("Resource", name, source, len(kws)))

        if not rows:
            self.app.echo("(nothing imported)")
            return

        name_w = max(len(r[1]) for r in rows)
        for kind, name, source, count in rows:
            self.app.echo(f"  {kind:<8} {name:<{name_w}}  {count:>4} kw   {source}")

    @dot_command("vars", "v")
    def _vars(self, arg: str) -> None:
        """Show variables in scope. Use --user to skip Robot internals.

        Print every variable visible in the current scope along with a
        truncated `repr()` of its value. While paused at a debug stop, this
        instead lists the selected frame's variables grouped by scope
        (`Local`/`Test`/`Suite`/`Global`).

        Usage:
          .vars [--user]

        Options:
          --user   Hide Robot's built-in variables (`${SUITE_NAME}`,
                   `${OUTPUT_DIR}`, `${TEMPDIR}`, …) so the listing focuses
                   on what the user assigned in the session. Has no effect at a
                   debug stop, where variables are grouped by scope instead.
        """
        if self.app is None:
            return
        if self._stop is not None:
            self._show_frame_scopes()
            return
        ctx = EXECUTION_CONTEXTS.current
        if ctx is None:
            self.app.echo("(no active context)")
            return
        only_user = "--user" in arg.split()

        rows: List[Tuple[str, str]] = []
        for decorated, value in ctx.variables.as_dict().items():
            name = str(decorated)
            bare = name
            if len(name) > 2 and name[0] in "$@&%" and name[1] == "{" and name[-1] == "}":
                bare = name[2:-1]
            if only_user and _is_robot_internal(bare):
                continue
            try:
                rep = repr(value)
            except Exception:
                rep = "<unprintable>"
            if len(rep) > 60:
                rep = rep[:59] + "…"
            rows.append((name, rep))

        if not rows:
            self.app.echo("(no variables)")
            return
        name_w = max(len(r[0]) for r in rows)
        for name, rep in rows:
            self.app.echo(f"  {name:<{name_w}}  {rep}")

    def _show_frame_scopes(self) -> None:
        """`.vars` at a debug stop — the selected frame's scopes, via the controller."""
        scopes = self._controller.get_scopes(self._selected_frame()) if self._controller is not None else []
        if not scopes:
            self._echo("(no variables)")
            return
        for scope in scopes:
            self._echo(f"{scope.name}:")
            if not scope.variables:
                self._echo("    (none)")
            for var in scope.variables:
                self._echo(f"    {var.name} = {var.value}")

    @dot_command("kw")
    def _kw(self, arg: str) -> None:
        """Show or search keyword documentation: .kw [name-or-text]

        With a keyword name, shows its full documentation: signature
        (arguments with their types and defaults), description, tags, and
        where it comes from. Names are resolved just like in a Robot
        Framework suite, so the `Owner.Keyword` form works too.

        With no argument, lists every keyword grouped by the library or
        resource it belongs to. With text that isn't an exact keyword
        name, lists the keywords whose name contains that text.

        Usage:
          .kw                 list every loaded keyword
          .kw <text>          list keywords whose name contains <text>
          .kw <keyword-name>  show full documentation for one keyword

        Examples:
          .kw
          .kw append
          .kw Get From Dictionary
          .kw BuiltIn.Log
        """
        if self.app is None:
            return
        if not arg:
            self._list_keywords(None)
            return

        doc = self._keyword_doc(arg)
        if doc is None:
            # Not an exact keyword — treat the argument as a search filter.
            self._list_keywords(arg)
            return
        self.show_doc(*doc)

    def _keyword_doc(self, name: str) -> Optional[Tuple[str, str]]:
        """`(title, markdown)` for an exactly-named keyword, or ``None``.

        Shared by `.kw <name>` and the doc-viewer link resolver. Prefers
        the diagnostics `KeywordDoc` (proper signature + arg table +
        types); falls back to a hand-built page from the runtime object
        when that conversion can't surface one.
        """
        found = lookup_keyword_owner(name)
        if found is None:
            return None
        owner, runtime_kw, is_resource = found
        kw_name = getattr(runtime_kw, "name", name)
        diag_kw = _diagnostics_keyword_doc(owner, is_resource, kw_name)
        if diag_kw is not None:
            return kw_name, diag_kw.to_markdown(header_level=1)
        return kw_name, _render_runtime_keyword_md(runtime_kw, kw_name)

    def _list_keywords(self, pattern: Optional[str]) -> None:
        """List loaded keywords grouped by owner, optionally filtered by a
        case-insensitive substring of the keyword name."""
        if self.app is None:
            return
        needle = pattern.casefold() if pattern else None

        sections: List[str] = []
        total = 0
        for owner_name, is_resource, names in iter_keyword_owners():
            if needle is not None:
                names = [n for n in names if needle in n.casefold()]
            if not names:
                continue
            kind = "Resource" if is_resource else "Library"
            sections.append(f"## {owner_name} ({kind})")
            sections.extend(self._keyword_list_entry(owner_name, n) for n in names)
            sections.append("")
            total += len(names)

        if total == 0:
            if pattern:
                self.app.echo(f"No keywords found matching {pattern!r}.")
            else:
                self.app.echo("(no keywords loaded)")
            return

        title = f"Keywords matching '{pattern}'" if pattern else "Keywords"
        self.show_doc(title, f"# {title}\n\n" + "\n".join(sections))

    def _keyword_list_entry(self, owner_name: str, kw_name: str) -> str:
        """One bullet line for `_list_keywords`. Plain text here; the
        prompt_toolkit backend overrides this to emit a follow-able link
        into the keyword's documentation."""
        del owner_name
        return f"- {kw_name}"

    @dot_command("doc")
    def _doc(self, arg: str) -> None:
        """Show the documentation for a library or resource: .doc <name>

        Shows the full page for a library or resource file: its
        introduction, followed by every keyword with its signature,
        arguments, and description.

        Only libraries and resources the current session has imported can
        be shown, addressed by their name in the suite's namespace. For a
        library imported with an alias (`AS`, or the older `WITH NAME`),
        that means the alias rather than the original library name; for a
        resource, its file name without the extension.

        Usage:
          .doc <library-or-resource-name>

        Examples:
          .doc BuiltIn
          .doc Collections
          .doc MyResource
        """
        if self.app is None:
            return
        if not arg:
            self.app.echo("Usage: .doc <library-or-resource-name>")
            return

        lib_doc, error = self._resolve_doc_target(arg)
        if lib_doc is None:
            self.app.echo(error or f"Could not load {arg!r}.")
            return

        self.show_doc(lib_doc.name, lib_doc.to_markdown(only_doc=False, header_level=1))

    def _resolve_doc_target(self, arg: str) -> Tuple[Optional[LibraryDoc], Optional[str]]:
        """Build the `LibraryDoc` for an imported library or resource.

        Only items currently loaded in `EXECUTION_CONTEXTS.current` are
        considered — `.doc` reflects what the user has imported. The
        library and resource sections of the store are looked up
        separately, so the instance type is known and no file-name
        guessing is needed; it is converted in place without reimporting
        or re-parsing.
        """
        library = lookup_library(arg)
        if library is not None:
            try:
                return get_library_doc_from_library(library, name=str(library.name)), None
            except Exception as e:
                return None, f"Could not render documentation for {arg!r}: {e}"

        resource = lookup_resource(arg)
        if resource is not None:
            try:
                return get_resource_doc_from_resource(resource), None
            except Exception as e:
                return None, f"Could not render documentation for {arg!r}: {e}"

        return None, f"{arg!r} is not loaded. Import it as a library or resource first."

    @dot_command("clear")
    def _clear(self, arg: str) -> None:
        """Clear the screen.

        Erase the terminal screen and move the cursor back to the top.
        """
        del arg
        if self.app is None:
            return
        # Standard "erase display + cursor home" ANSI sequence.
        self.app.echo("\x1b[2J\x1b[H", nl=False)

    @dot_command("cwd")
    def _cwd(self, arg: str) -> None:
        """Show the current working directory.

        Print the current working directory — the base path that relative
        `Import Resource`, `Import Library`, and file-based variable
        references resolve against.
        """
        del arg
        if self.app is None:
            return
        try:
            self.app.echo(str(Path.cwd()))
        except OSError as e:
            self.app.echo(f"(working directory unavailable: {e})")

    @dot_command("exit", "quit")
    def _exit(self, arg: str) -> None:
        """Exit the REPL.

        Leave the REPL. Equivalent to pressing Ctrl-D on an empty prompt.
        `.exit` and `.quit` are aliases. At a debug stop "exit" is ambiguous,
        so it points you at the resume/abort commands instead of leaving.
        """
        del arg
        if self._stop is not None:
            self._echo("at a debug stop — use .continue or .detach to resume, or .abort to quit the run")
            return
        raise EOFError

    @dot_command("save")
    def _save(self, arg: str) -> None:
        """Save session as a .robot file: .save [-a] [-t NAME] FILENAME

        Save the current REPL session as a runnable `.robot` file. Only
        lines Robot could parse are exported; lines that failed are
        skipped so the result stays runnable with `robot <filename>`.

        Imports become a `*** Settings ***` section (so
        `Import Library    Collections` becomes `Library    Collections`),
        and everything else goes into a single `*** Test Cases ***` block.

        Usage:
          .save [-a] [-t NAME] FILENAME

        Options:
          -a, --append             Append to FILENAME instead of overwriting.
                                   Robot accepts repeated section headers, so
                                   the appended file stays runnable; tidy up
                                   by hand if you want a single layout.
          -t NAME, --test-name NAME
                                   Override the default test-case name. By
                                   default the test is called
                                   `REPL Session <ISO-timestamp>`.

        Examples:
          .save scratch.robot
          .save -t Smoke smoke.robot
          .save -a -t "Login flow" suite.robot
        """
        if self.app is None:
            return
        parser = _build_save_parser()
        try:
            opts = parser.parse_args(_split_command_args(arg))
        except (argparse.ArgumentError, SystemExit, ValueError):
            self.app.echo("Usage: .save [-a] [-t NAME] FILENAME")
            return

        lines: List[str] = list(self._session_lines or [])
        if not lines:
            self.app.echo("Nothing to save — the session has no recorded inputs yet.")
            return

        content = render_robot_file(lines, test_name=opts.test_name)
        path = Path(opts.filename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if opts.append and path.exists():
                # Pasted verbatim — Robot's parser accepts repeated section
                # headers (`*** Test Cases ***` etc.) by concatenation, so
                # the appended file stays runnable even though the layout
                # has duplicated sections. Users can tidy up afterwards.
                existing = path.read_text(encoding="utf-8")
                path.write_text(existing.rstrip() + "\n\n" + content, encoding="utf-8")
            else:
                path.write_text(content, encoding="utf-8")
        except OSError as e:
            self.app.echo(f"Could not write {opts.filename}: {e}")
            return

        self.app.echo(f"Wrote {path} ({len(lines)} entries)")

    # ------------------------------------------------------------------
    # Debugger dot-commands — active while paused at a stop (`group=
    # "Debugger"`). The navigation/inspection commands need a stop; the
    # breakpoint commands only need an attached controller.
    # ------------------------------------------------------------------

    @dot_command("continue", "c", group="Debugger")
    def _continue(self, arg: str) -> None:
        """Resume until the next breakpoint, stop, or the end of the run."""
        del arg
        if self._require_stop():
            self._pending_action = ResumeAction.CONTINUE

    @dot_command("step", "s", group="Debugger")
    def _step(self, arg: str) -> None:
        """Step into: stop at the next keyword, descending into calls."""
        del arg
        if self._require_stop():
            self._pending_action = ResumeAction.STEP_IN

    @dot_command("next", "n", group="Debugger")
    def _next(self, arg: str) -> None:
        """Step over: stop at the next keyword in the current frame."""
        del arg
        if self._require_stop():
            self._pending_action = ResumeAction.STEP_OVER

    @dot_command("return", "r", group="Debugger")
    def _return(self, arg: str) -> None:
        """Continue until the current keyword returns, then stop."""
        del arg
        if self._require_stop():
            self._pending_action = ResumeAction.STEP_OUT

    @dot_command("until", group="Debugger")
    def _until(self, arg: str) -> None:
        """Continue until a later line in the current frame (past loops), or it returns."""
        del arg
        if self._require_stop():
            self._pending_action = ResumeAction.UNTIL

    @dot_command("where", "w", group="Debugger")
    def _where(self, arg: str) -> None:
        """Show the call stack (innermost frame as #0; `>` marks the selected one)."""
        del arg
        if not self._require_stop():
            return
        stack = self._stop.stack if self._stop else []
        if not stack:
            self._echo("(no stack)")
            return
        width = max(len(f.name) for f in stack)
        for frame_no, frame in enumerate(reversed(stack)):
            self._echo(self._frame_line(frame_no, frame, width))

    def _show_source(
        self,
        source: str,
        line: int,
        *,
        title: str,
        plain_header: Optional[str] = None,
        plain_before: int,
        plain_after: int,
    ) -> None:
        """Render source for `.list` / `.source`, picking the backend's surface.

        prompt_toolkit: the **whole file** in the scrollable viewer, marked at
        `line` (`->`) and opened scrolled to it. Plain: an inline window
        (`plain_before`/`plain_after` lines around `line`), optionally preceded
        by `plain_header`."""
        if self.has_scrollable_viewer:
            lines = self._source_window_lines(source, line, before=None, after=None)
            if lines is not None:
                self.show_doc(title, "```\n" + "\n".join(lines) + "\n```", scroll_to=f"-> {line:>4}")
        else:
            if plain_header is not None:
                self._echo(plain_header)
            self._render_source_window(source, line, before=plain_before, after=plain_after)

    @dot_command("list", "l", group="Debugger")
    def _list(self, arg: str) -> None:
        """Show the source at the current stop.

        prompt_toolkit: the whole file in the scrollable viewer, scrolled to the
        current line (marked `->`). Plain backend: a ±5-line inline window."""
        del arg
        if not self._require_stop():
            return
        frame = self._selected_frame()
        if frame.source is None or frame.line is None:
            self._render_source_window(frame.source, frame.line)  # inline fallback message
            return
        title = f"{frame.short_name}  ({os.path.basename(str(frame.source))}:{frame.line})"
        self._show_source(str(frame.source), int(frame.line), title=title, plain_before=5, plain_after=5)

    @dot_command("source", group="Debugger")
    def _source(self, arg: str) -> None:
        """Show a keyword's source — `.source Open Browser`.

        On prompt_toolkit it opens the scrollable doc viewer at the keyword's
        definition (marked with `->`). On the plain backend it prints inline from
        the definition line downward; a trailing count sets how many lines
        (default 10) — `.source Open Browser 25`.
        """
        if not arg:
            self._echo("usage: .source <keyword-name> [lines]")
            return
        # Split off a trailing line-count (the plain-backend window size). Keyword
        # names contain spaces, so only a trailing integer token counts.
        name, count = arg, 10
        head = arg.rsplit(None, 1)
        if len(head) == 2 and head[1].isdigit():
            name, count = head[0], max(1, int(head[1]))
        found = lookup_keyword_owner(name)
        if found is None:
            self._echo(f"keyword {name!r} not found")
            return
        owner, runtime_kw, is_resource = found
        kw_name = getattr(runtime_kw, "name", name)
        diag = _diagnostics_keyword_doc(owner, is_resource, kw_name)
        source = getattr(diag, "source", None) if diag is not None else None
        line = getattr(diag, "line_no", None) if diag is not None else None
        if source is None:
            source = getattr(runtime_kw, "source", None)
        if source is None or line is None:
            self._echo(f"(no source available for {kw_name})")
            return
        source, line = str(source), int(line)
        header = f"{kw_name}  ({os.path.basename(source)}:{line})"
        # Viewer: whole file scrolled to the definition. Plain: inline from the
        # definition downward (`count` lines, default 10), preceded by the header.
        self._show_source(source, line, title=header, plain_header=header, plain_before=0, plain_after=count - 1)

    @dot_command("up", "u", group="Debugger")
    def _up(self, arg: str) -> None:
        """Select the calling (outer) frame."""
        del arg
        if self._require_stop():
            self._move_frame(self._frame_no + 1)

    @dot_command("down", "d", group="Debugger")
    def _down(self, arg: str) -> None:
        """Select the called (inner) frame."""
        del arg
        if self._require_stop():
            self._move_frame(self._frame_no - 1)

    @dot_command("frame", "f", group="Debugger")
    def _frame(self, arg: str) -> None:
        """Select a frame by number — `.frame 2` (#0 is the innermost)."""
        if not self._require_stop():
            return
        try:
            target = int(arg)
        except ValueError:
            top = len(self._stop.stack) - 1 if self._stop else 0
            self._echo(f"usage: .frame <n>  (0..{top})")
            return
        self._move_frame(target)

    @dot_command("print", "p", group="Debugger")
    def _print(self, arg: str) -> None:
        """Evaluate a variable or expression in the selected frame — `.print ${x}`."""
        if not self._require_stop():
            return
        if not arg:
            self._echo("usage: .print <variable-or-expression>")
            return
        try:
            value = self._controller.evaluate_expression(self._selected_frame(), arg)  # type: ignore[union-attr]
        except Exception as e:  # surface lookup/eval failures to the prompt
            self._echo(f"! {e}")
            return
        self._echo(f"{arg} = {_repr.repr(value)}")

    @dot_command("pprint", "pp", group="Debugger")
    def _pprint(self, arg: str) -> None:
        """Pretty-print a variable or expression in the selected frame — `.pprint ${x}`."""
        if not self._require_stop():
            return
        if not arg:
            self._echo("usage: .pprint <variable-or-expression>")
            return
        try:
            value = self._controller.evaluate_expression(self._selected_frame(), arg)  # type: ignore[union-attr]
        except Exception as e:  # surface lookup/eval failures to the prompt
            self._echo(f"! {e}")
            return
        self._echo(pprint.pformat(value))

    @dot_command("whatis", group="Debugger")
    def _whatis(self, arg: str) -> None:
        """Show the type of a variable or expression in the selected frame — `.whatis ${x}`."""
        if not self._require_stop():
            return
        if not arg:
            self._echo("usage: .whatis <variable-or-expression>")
            return
        try:
            value = self._controller.evaluate_expression(self._selected_frame(), arg)  # type: ignore[union-attr]
        except Exception as e:  # surface lookup/eval failures to the prompt
            self._echo(f"! {e}")
            return
        self._echo(f"{arg}: {type(value).__name__}")

    @dot_command("display", group="Debugger")
    def _display(self, arg: str) -> None:
        """Show an expression's value at every stop — `.display ${x}`; bare `.display` lists them."""
        if not arg:
            if not self._display_exprs:
                self._echo("(no display expressions)")
                return
            if self._stop is not None:
                self._show_displays()
            else:
                for expr in self._display_exprs:
                    self._echo(expr)
            return
        if arg not in self._display_exprs:
            self._display_exprs.append(arg)
        self._echo(f"displaying {arg}")

    @dot_command("undisplay", group="Debugger")
    def _undisplay(self, arg: str) -> None:
        """Stop displaying an expression — `.undisplay ${x}`; bare `.undisplay` clears all."""
        if not arg:
            self._display_exprs.clear()
            self._echo("display list cleared")
            return
        if arg in self._display_exprs:
            self._display_exprs.remove(arg)
            self._echo(f"no longer displaying {arg}")
        else:
            self._echo(f"not displaying: {arg}")

    @dot_command("set", group="Debugger")
    def _set(self, arg: str) -> None:
        """Set a scalar variable in the selected frame — `.set ${x} <value>`.

        The value is variable-substituted and stored as-is (like `Set Variable`):
        `.set ${name} hello` sets the string; use `${{ ... }}` for Python. Only
        whole scalar variables (`${...}`) are supported — not list/dict variables
        (`@{...}`/`&{...}`) or item access (`${x}[0]`). The assignment lands in
        the selected frame's local scope.
        """
        if not self._require_stop():
            return
        parts = arg.split(None, 1)
        if len(parts) < 2:
            self._echo("usage: .set ${name} <value>")
            return
        name, value = parts[0], parts[1]
        if not (name.startswith("${") and name.endswith("}")) or "[" in name:
            self._echo(f"! .set only supports whole scalar variables (${{...}}), not {name}")
            return
        try:
            new_repr = self._controller.set_variable(  # type: ignore[union-attr]
                self._selected_frame(), name, value, evaluate=False
            )
        except Exception as e:  # surface NameError / unknown-variable to the prompt
            self._echo(f"! {e}")
            return
        self._echo(f"{name} = {new_repr}")

    def _add_breakpoint(self, arg: str, *, temporary: bool) -> None:
        if not self._require_controller():
            return
        if not arg:
            self._echo("usage: .break <file:line | keyword name> [, <condition>]")
            return
        spec, condition = arg, None
        if "," in arg:  # `.break <loc>, <condition>`
            spec, rest = arg.split(",", 1)
            spec, condition = spec.strip(), (rest.strip() or None)
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        m = _LINE_BREAK_RE.match(spec)
        if m:
            bp = controller.add_line_breakpoint(
                m.group("path"), int(m.group("line")), condition=condition, temporary=temporary
            )
            where = spec
        else:
            bp = controller.add_keyword_breakpoint(spec, condition=condition, temporary=temporary)
            where = f"keyword {spec!r}"
        label = "temporary breakpoint" if temporary else "breakpoint"
        cond = f" if {condition}" if condition else ""
        self._echo(f"{label} {bp.id} at {where}{cond}")

    @dot_command("break", "b", group="Debugger")
    def _break(self, arg: str) -> None:
        """Add a breakpoint — `.break file:line` / `.break Keyword Name` / `.break <loc>, <condition>`."""
        self._add_breakpoint(arg, temporary=False)

    @dot_command("tbreak", group="Debugger")
    def _tbreak(self, arg: str) -> None:
        """Add a one-shot breakpoint, removed after it first stops — same syntax as `.break`."""
        self._add_breakpoint(arg, temporary=True)

    @dot_command("breakpoints", "bp", group="Debugger")
    def _breakpoints(self, arg: str) -> None:
        """List the active breakpoints (numbered) and exception filters."""
        del arg
        if not self._require_controller():
            return
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        bps = controller.breakpoints
        for bp in bps:
            loc = bp.name if bp.kind == "keyword" else f"{os.path.basename(bp.source or '?')}:{bp.line}"
            flags: List[str] = []
            if not bp.enabled:
                flags.append("disabled")
            if bp.temporary:
                flags.append("temp")
            if bp.condition:
                flags.append(f"if {bp.condition}")
            if bp.ignore_count:
                flags.append(f"ignore {bp.ignore_count}")
            if bp.log_message is not None:
                flags.append("logpoint")
            if bp.commands:
                flags.append(f"{len(bp.commands)} cmds")
            suffix = ("  " + ", ".join(flags)) if flags else ""
            self._echo(f"  #{bp.id}  {bp.kind:<7} {loc}{suffix}")
        filters = controller.exception_filters
        if filters:
            self._echo(f"  catch    {', '.join(sorted(filters))}")
        if not bps and not filters:
            self._echo("(no breakpoints)")

    def _bp_by_arg(self, token: str) -> Optional[Breakpoint]:
        """Resolve a breakpoint-number token to a `Breakpoint`, echoing on miss."""
        controller = self._controller
        assert controller is not None  # callers guard with _require_controller
        try:
            bp_id = int(token)
        except (TypeError, ValueError):
            self._echo(f"not a breakpoint number: {token}")
            return None
        bp = controller.get_breakpoint(bp_id)
        if bp is None:
            self._echo(f"no breakpoint {bp_id}")
        return bp

    @dot_command("condition", group="Debugger")
    def _condition(self, arg: str) -> None:
        """Set or clear a breakpoint condition — `.condition <n> <expr>` (bare `.condition <n>` clears it)."""
        if not self._require_controller():
            return
        parts = arg.split(None, 1)
        if not parts:
            self._echo("usage: .condition <breakpoint-number> [<expression>]")
            return
        bp = self._bp_by_arg(parts[0])
        if bp is None:
            return
        bp.condition = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        if bp.condition:
            self._echo(f"breakpoint {bp.id}: condition {bp.condition}")
        else:
            self._echo(f"breakpoint {bp.id}: condition cleared")

    @dot_command("ignore", group="Debugger")
    def _ignore(self, arg: str) -> None:
        """Skip a breakpoint's next N hits — `.ignore <n> <count>`."""
        if not self._require_controller():
            return
        parts = arg.split()
        if len(parts) != 2:
            self._echo("usage: .ignore <breakpoint-number> <count>")
            return
        bp = self._bp_by_arg(parts[0])
        if bp is None:
            return
        try:
            count = int(parts[1])
        except ValueError:
            self._echo(f"not a count: {parts[1]}")
            return
        bp.ignore_count = max(0, count)
        bp.hits = 0  # the next `count` triggering hits are skipped from now
        if bp.ignore_count:
            self._echo(f"breakpoint {bp.id}: ignoring the next {bp.ignore_count} hit(s)")
        else:
            self._echo(f"breakpoint {bp.id}: no longer ignored")

    @dot_command("delete", group="Debugger")
    def _delete(self, arg: str) -> None:
        """Remove a breakpoint — `.delete <n>`; bare `.delete` removes all."""
        if not self._require_controller():
            return
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        if not arg.strip():
            count = len(controller.breakpoints)
            controller.breakpoints.clear()
            self._echo(f"removed {count} breakpoint(s)")
            return
        bp = self._bp_by_arg(arg.strip())
        if bp is None:
            return
        controller.remove_breakpoint(bp.id)
        self._echo(f"deleted breakpoint {bp.id}")

    def _set_bp_enabled(self, arg: str, enabled: bool) -> None:
        if not self._require_controller():
            return
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        word = "enabled" if enabled else "disabled"
        if not arg.strip():
            for existing in controller.breakpoints:
                existing.enabled = enabled
            self._echo(f"all breakpoints {word}")
            return
        bp = self._bp_by_arg(arg.strip())
        if bp is None:
            return
        bp.enabled = enabled
        self._echo(f"breakpoint {bp.id} {word}")

    @dot_command("disable", group="Debugger")
    def _disable(self, arg: str) -> None:
        """Disable a breakpoint — `.disable <n>`; bare `.disable` disables all."""
        self._set_bp_enabled(arg, False)

    @dot_command("enable", group="Debugger")
    def _enable(self, arg: str) -> None:
        """Enable a breakpoint — `.enable <n>`; bare `.enable` enables all."""
        self._set_bp_enabled(arg, True)

    @dot_command("commands", group="Debugger")
    def _commands(self, arg: str) -> None:
        """Attach commands to a breakpoint, replayed at each hit — `.commands <n>`, end with `end`.

        Enter one command per line; `end` finishes. A leading `silent` suppresses
        the stop banner; a resuming command (`.continue`/…) makes the breakpoint
        run the commands and carry on without prompting. Bare list clears them.
        """
        if not self._require_controller():
            return
        if not arg.strip():
            self._echo("usage: .commands <breakpoint-number>")
            return
        bp = self._bp_by_arg(arg.strip())
        if bp is None:
            return
        self._echo(f"enter commands for breakpoint {bp.id}, one per line; `end` to finish:")
        collected: List[str] = []
        while True:
            try:
                line = self.read_line("(com) ")
            except (EOFError, KeyboardInterrupt):
                break
            line = line.strip()
            if line == "end":
                break
            if line:
                collected.append(line)
        bp.commands = collected
        if collected:
            self._echo(f"breakpoint {bp.id}: {len(collected)} command(s)")
        else:
            self._echo(f"breakpoint {bp.id}: commands cleared")

    @dot_command("catch", group="Debugger")
    def _catch(self, arg: str) -> None:
        """Set exception breakpoints — `.catch uncaught|all|test|suite|off`, or bare to show."""
        if not self._require_controller():
            return
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        tokens = arg.split()
        if not tokens:
            filters = controller.exception_filters
            self._echo(f"catching: {', '.join(sorted(filters)) if filters else '(none)'}")
            return
        if tokens in (["off"], ["none"]):
            controller.set_exception_breakpoints([])
            self._echo("catching: (none)")
            return
        mapped: Set[str] = set()
        for token in tokens:
            target = _CATCH_SHORTHANDS.get(token.lower())
            if target is None:
                self._echo(f"unknown catch filter: {token}; try uncaught, all, test, suite, off")
                return
            mapped.add(target)
        controller.set_exception_breakpoints(mapped)
        self._echo(f"catching: {', '.join(sorted(mapped))}")

    @dot_command("debug", group="Debugger")
    def _debug(self, arg: str) -> None:
        """Attach or detach the debugger — `.debug on|off`, or bare to show state.

        When **attached** (`.debug on`) breakpoints, an embedded `Breakpoint`
        keyword, and the armed exception breaks (`.catch`) pause a keyword you
        run into the `(rdb)` prompt. When **detached** (`.debug off`, the default
        for `robotcode repl`) nothing pauses — a failing keyword just prints its
        error and you stay at the prompt. Detaching keeps your breakpoints and
        `.catch` filters intact, so `.debug on` resumes with the same setup.
        """
        if not self._require_controller():
            return
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        token = arg.strip().lower()
        if not token:
            self._echo(f"debugger: {'attached' if controller.attached else 'detached'}")
            return
        if token == "on":
            controller.set_attached(True)
            self._echo("debugger: attached")
        elif token == "off":
            controller.set_attached(False)
            self._echo("debugger: detached")
        else:
            self._echo("usage: .debug on|off")

    @dot_command("detach", group="Debugger")
    def _detach(self, arg: str) -> None:
        """Detach the debugger; at a stop, also let the run finish without pausing.

        Keeps your breakpoints and `.catch` filters (re-arm with `.debug on`).
        """
        del arg
        if not self._require_controller():
            return
        controller = self._controller
        assert controller is not None  # narrowed by _require_controller
        controller.set_attached(False)
        if self._stop is not None:
            self._pending_action = ResumeAction.CONTINUE
            self._echo("debugger: detached")
        else:
            self._echo("debugger: detached (cannot continue)")

    @dot_command("abort", group="Debugger")
    def _abort(self, arg: str) -> None:
        """Abort the run and exit. Use `.detach` to let the suite finish instead."""
        del arg
        if self._stop is None:
            self._echo("no run to abort")
            return
        # Robot can't be cleanly stopped mid-keyword from a logger callback — a
        # raised exception is swallowed by suite.run() — so exit via SystemExit,
        # the one exception Robot does propagate.
        self._echo("aborting the run")
        sys.exit(1)

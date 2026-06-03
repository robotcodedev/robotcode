"""prompt_toolkit pieces shared by `PromptToolkitConsoleInterpreter`.

Everything in this module is a leaf — completer, history class,
key-bindings builder, bottom toolbar callback, style sheet,
continuation-prompt helper. The interpreter wires them together;
each is unit-testable in isolation.
"""

import itertools
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, List, Optional, Tuple

from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_completions
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.styles import Style

from .._indent import compute_indent, has_open_block
from .._keyword_lookup import lookup_keyword_doc
from .completion import (
    CELL_SEPARATOR,
    candidates_for_rich,
    command_prefix,
    complete_commands,
    current_keyword_and_arg_index,
    current_named_arg_in_cell,
    find_cell_end,
    spec_arg_position,
    tokenize,
)
from .history import max_history_size


class _ReplFileHistory(FileHistory):
    """`FileHistory` with first-class `clear` / `delete` and a bounded size.

    `append_string` drops the oldest entry whenever a new one would push
    the file past `max_entries`, so the on-disk size stays bounded as
    the REPL is used over many sessions. Reads are also sliced to the
    cap as defense-in-depth against externally-edited files.
    """

    def __init__(self, filename: str, *, max_entries: Optional[int] = None) -> None:
        super().__init__(filename)
        self._max_entries = max_entries if max_entries is not None else max_history_size()

    def load_history_strings(self) -> Iterable[str]:
        # FileHistory yields newest-first; cap the iterator so prompt_toolkit
        # never sees more than `max_entries` regardless of file size.
        return itertools.islice(super().load_history_strings(), self._max_entries)

    def append_string(self, string: str) -> None:
        """Append, then enforce the cap by dropping the oldest entries."""
        super().append_string(string)
        # Read uncapped to learn the actual on-disk count after the append.
        entries = list(super().load_history_strings())  # newest-first
        if len(entries) <= self._max_entries:
            return
        survivors = entries[: self._max_entries]
        try:
            Path(str(self.filename)).write_text("", encoding="utf-8")
        except OSError:
            return
        # store_string appends to file → write oldest-first to preserve order.
        for entry in reversed(survivors):
            super().store_string(entry)
        if self._loaded:
            self._loaded_strings = survivors

    def clear(self) -> bool:
        """Wipe all entries — file and in-memory cache.

        Returns True on success; False on OSError (e.g. permission denied).
        """
        try:
            Path(str(self.filename)).write_text("", encoding="utf-8")
        except OSError:
            return False
        self._loaded = False
        self._loaded_strings = []
        return True

    def delete(self, idx: int) -> bool:
        """Drop the 1-based entry at `idx`. Returns True on success.

        FileHistory's on-disk format is multi-line per entry, so there's
        no line-index-based delete that would work — we read the entries,
        drop the one at `idx-1`, and re-store the survivors. Their
        timestamps get refreshed to "now"; the dot-commands don't surface
        timestamps so the user sees no difference.
        """
        entries = list(reversed(list(self.load_history_strings())))
        if not (1 <= idx <= len(entries)):
            return False
        del entries[idx - 1]
        try:
            Path(str(self.filename)).write_text("", encoding="utf-8")
        except OSError:
            return False
        self._loaded = False
        self._loaded_strings = []
        for entry in entries:
            self.store_string(entry)
        return True


class _RobotCompleter(Completer):
    """Adapts `candidates_for_rich` to prompt_toolkit's Completion protocol.

    Each candidate's ``detail`` becomes the popup's ``display_meta``,
    shown grey-italic beside the label. ``suppress_once`` is a one-shot
    fuse the Esc-revert path sets to keep ``complete_while_typing``
    from re-firing on the restored buffer.
    """

    def __init__(
        self,
        *,
        command_names: Iterable[str] = (),
        context_provider: Optional[Callable[[], Tuple[Any, Any]]] = None,
    ) -> None:
        super().__init__()
        self.suppress_once = False
        # Dot-commands to offer (REPL or debugger); empty disables that path.
        self._command_names = tuple(command_names)
        # () -> (namespace_context, variables_store) to complete against; a paused
        # frame's scope for the debugger. None ⇒ the live execution context.
        self._context_provider = context_provider

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterator[Completion]:
        del complete_event
        if self.suppress_once:
            self.suppress_once = False
            return
        text = document.text_before_cursor

        if self._command_names:
            cmd_prefix = command_prefix(text)
            if cmd_prefix is not None:
                start = -len(text.lstrip())  # replace the whole `.word`
                for cand in complete_commands(cmd_prefix, self._command_names):
                    yield Completion(cand.label, start_position=start, display_meta=cand.detail)
                return

        ctx = tokenize(text, len(text))
        context, variables = self._context_provider() if self._context_provider is not None else (None, None)
        candidates = candidates_for_rich(ctx, context=context, variables=variables)
        # `start_position` is signed and negative — chars before the
        # cursor that prompt_toolkit should replace.
        start = ctx.replace_start - len(text)
        for cand in candidates:
            yield Completion(cand.label, start_position=start, display_meta=cand.detail)


def _find_robot_completer(buf: Buffer) -> Optional["_RobotCompleter"]:
    """Locate the buffer's `_RobotCompleter`, walking past wrappers like `ThreadedCompleter`."""
    c: Optional[Completer] = buf.completer
    while c is not None:
        if isinstance(c, _RobotCompleter):
            return c
        # Wrapper chain (`ThreadedCompleter.completer`, …) — the attribute
        # isn't on the `Completer` base class, so the read stays defensive.
        c = getattr(c, "completer", None)
    return None


def _accept_highlighted_completion(buf: Buffer) -> None:
    """Commit the popup's highlighted candidate as-is.

    Clearing ``complete_state`` keeps prompt_toolkit's live preview as
    the final buffer text. (Calling ``apply_completion`` here would
    re-do delete+insert from the post-preview cursor and produce
    duplicated prefixes like ``LoLog``.) For keyword completions we
    also trim any leftover text in the current cell and append a cell
    separator so the user can start typing the first argument.
    """
    buf.complete_state = None
    text = buf.text
    pos = buf.cursor_position
    if tokenize(text[:pos], pos).kind != "keyword":
        return
    cell_end = find_cell_end(text, pos)
    if cell_end > pos:
        buf.text = text[:pos] + text[cell_end:]
        buf.cursor_position = pos
    line_remaining = buf.text[buf.cursor_position :].split("\n", 1)[0]
    if not line_remaining:
        buf.insert_text(CELL_SEPARATOR, fire_event=False)


def _on_completion_state_changed(buf: Buffer) -> None:
    """Bookkeeping fired once when the completion popup first opens.

    Snapshots the buffer state under ``state._literal_original`` so
    the Esc handler can restore it, and trims any forward-cell text
    from ``state.original_document`` so picking a longer keyword
    mid-cell renders cleanly (otherwise ``Log<cursor>  hello`` →
    ``Log To Console`` would render as ``Log To Consoleog  hello``).
    """
    state = buf.complete_state
    if state is None:
        return
    if state.complete_index is not None:
        return  # arrow navigation, not a fresh popup
    if getattr(state, "_literal_original", None) is not None:
        return
    text = state.original_document.text
    pos = state.original_document.cursor_position
    state._literal_original = (text, pos)  # type: ignore[attr-defined]
    if tokenize(text[:pos], pos).kind != "keyword":
        return
    cell_end = find_cell_end(text, pos)
    if cell_end <= pos:
        return
    state.original_document = Document(text[:pos] + text[cell_end:], pos)


def _insert_indented_newline(buf: Buffer) -> None:
    """Insert a newline + auto-indent for the line the user is about to type."""
    # `+ [""]` extends the list with an empty sentinel so `compute_indent`
    # works out the indent for the *next* line, not the one just finished.
    indent = compute_indent([*buf.text.splitlines(), ""])
    buf.insert_text("\n" + indent)


def _build_keybindings(bind_help_key: bool = False) -> KeyBindings:
    """Bindings for the multi-line buffer:

    - `Enter` is smart: accepts a highlighted completion if the popup
      has one selected, else inserts a newline + auto-indent if a
      Robot block is open, else submits.
    - `Escape` closes an open completion popup. Gated by
      `has_completions` so Esc keeps its default Alt-chord-prefix
      role when no popup is visible. Uses `eager=True` so the
      dismiss is instant — without it prompt_toolkit waits for the
      chord-match timeout (up to ~2 s total) before reacting.
      Trade-off: Alt-Enter (Esc-Enter chord) does NOT fire while a
      popup is open. Use `Ctrl-J` to insert a newline instead — same
      effect, no chord conflict.
    - `Alt-Enter` (Esc Enter, *only* when no popup is visible) and
      `Ctrl-J` (any time) insert a newline + auto-indent regardless
      of block state — useful for adding a step to an
      already-balanced block.
    - `Tab` in argument context inserts a cell separator instead of
      triggering the completion popup. Robot has no meaningful
      argument-name completions, so Tab is repurposed as a typing
      accelerator. In keyword / variable / import contexts Tab keeps
      prompt_toolkit's default completion behaviour.
    - `F1` types `.help` into the buffer and submits when
      ``bind_help_key`` is true. The outer `get_input` loop then
      dispatches it — running `.help` directly from inside the
      prompt's event loop is unsafe (the doc viewer is a separate
      fullscreen Application, and prompt_toolkit doesn't support
      nested ``run()`` calls). Other dot-command shortcuts (`^L`
      clear, `^D` exit, `^R` reverse-search) stay on prompt_toolkit's
      built-in bindings — overriding them would mean re-implementing
      a feature we already get for free.

    Shift-Enter is not bound: most terminals send the same byte as
    plain Enter, so the binding couldn't fire portably. Alt-Enter
    and Ctrl-J work everywhere.
    """
    kb = KeyBindings()

    @kb.add("escape", "enter")
    @kb.add("c-j")
    def _insert_newline(event: KeyPressEvent) -> None:
        _insert_indented_newline(event.current_buffer)

    @kb.add("enter")
    def _smart_submit(event: KeyPressEvent) -> None:
        buf = event.current_buffer
        state = buf.complete_state
        if state is not None and state.current_completion is not None:
            _accept_highlighted_completion(buf)
            return
        if has_open_block(buf.text):
            _insert_indented_newline(buf)
        else:
            buf.validate_and_handle()

    @kb.add("escape", filter=has_completions, eager=True)
    def _cancel_completion(event: KeyPressEvent) -> None:
        # Instant dismiss — `eager=True` skips the chord-match timeout
        # that otherwise makes Esc feel sluggish (up to ~2 s). Cost:
        # Alt-Enter (Esc-Enter chord) is suppressed while the popup is
        # open; users should reach for Ctrl-J instead.
        buf = event.current_buffer
        state = buf.complete_state
        # If the user previewed a candidate (arrowed), restore the
        # literal buffer state from before the popup opened.
        if state is not None and state.complete_index is not None:
            snapshot = getattr(state, "_literal_original", None)
            if snapshot is None:
                text = state.original_document.text
                pos = state.original_document.cursor_position
            else:
                text, pos = snapshot
            completer = _find_robot_completer(buf)
            if completer is not None:
                completer.suppress_once = True
            buf.document = Document(text, pos)
        buf.cancel_completion()

    if bind_help_key:

        @kb.add("f1")
        def _help_shortcut(event: KeyPressEvent) -> None:
            # Type `.help` and submit instead of dispatching directly:
            # the doc viewer runs a separate fullscreen Application and
            # prompt_toolkit doesn't support nested `run()`. The outer
            # `get_input` loop picks the `.help` line up after the
            # prompt exits and dispatches it then.
            buf = event.current_buffer
            buf.text = ".help"
            buf.validate_and_handle()

    @kb.add("tab")
    def _smart_tab(event: KeyPressEvent) -> None:
        # Tab's role depends on what's on screen, *and* on the buffer
        # context. The order matters: once a candidate preview has been
        # applied to the buffer, tokenize() would re-classify the cursor
        # as `argument` (closed `${var}` in cell 2), so a context-first
        # check would jump from "cycle" to "insert cell-sep" mid-cycle.
        # Popup-state-first keeps cycling sane.
        buf = event.current_buffer
        if buf.complete_state:
            buf.complete_next()
            return
        text = buf.document.text_before_cursor
        # Both `argument` and `named_arg_value` are argument cells —
        # Tab inserts a cell separator in either case.
        if tokenize(text, len(text)).kind in ("argument", "named_arg_value"):
            buf.insert_text(CELL_SEPARATOR)
        else:
            buf.start_completion(insert_common_part=True)

    return kb


def _continuation_prompt(width: int, line_number: int, soft_wrapped: int) -> str:
    del line_number, soft_wrapped
    return ("... ").rjust(width)


def _spec_arg_items(spec: Any) -> List[str]:
    """Flatten an ``ArgumentSpec`` into ordered display labels.

    Each label carries its kind marker (``*args``, ``**kwargs``) and
    default value when one is set. The order matches the indices
    `spec_arg_position` returns.
    """
    items: List[str] = []
    defaults = getattr(spec, "defaults", None) or {}
    for name in getattr(spec, "positional_only", ()) or ():
        items.append(name)
    for name in getattr(spec, "positional_or_named", ()) or ():
        items.append(name)
    var_positional = getattr(spec, "var_positional", None)
    if var_positional:
        items.append(f"*{var_positional}")
    for name in getattr(spec, "named_only", ()) or ():
        items.append(name)
    var_named = getattr(spec, "var_named", None)
    if var_named:
        items.append(f"**{var_named}")

    def with_default(label: str) -> str:
        bare = label.lstrip("*")
        if bare in defaults:
            return f"{label}={defaults[bare]!r}"
        return label

    return [with_default(i) for i in items]


def _render_signature(name: str, spec: Any, active: int) -> List[Tuple[str, str]]:
    """Styled `<keyword>    arg1 · arg2 · …` with `active` highlighted."""
    parts: List[Tuple[str, str]] = [("class:rf.keyword", name)]
    items = _spec_arg_items(spec)
    if not items:
        return parts
    parts.append(("", "    "))
    for i, label in enumerate(items):
        if i > 0:
            parts.append(("", " · "))
        style = "class:rf.toolbar.active-arg" if i == active else "class:rf.argument"
        parts.append((style, label))
    return parts


def _bottom_toolbar() -> Optional[List[Tuple[str, str]]]:
    """Bottom status line — keyword signature when the cursor sits in an
    argument cell, else nothing (the bar is hidden).

    Returning ``None`` lets prompt_toolkit collapse the toolbar row
    entirely, so the prompt stays clean when there's no context-specific
    help to render.
    """
    try:
        buf = get_app().current_buffer
    except Exception:
        return None

    pos = current_keyword_and_arg_index(buf.text, buf.cursor_position)
    if pos is None:
        return None
    name, idx = pos
    kw = lookup_keyword_doc(name)
    if kw is None:
        return None
    spec = getattr(kw, "args", None) or getattr(kw, "arguments", None)
    if spec is None:
        return None
    # If the cursor sits in a `name=value` cell, follow the named arg's
    # spec position instead of the positional cell index — otherwise
    # `Log    msg    html=True` would still highlight `level`.
    named = current_named_arg_in_cell(buf.text, buf.cursor_position)
    if named is not None:
        named_idx = spec_arg_position(spec, named)
        if named_idx is not None:
            idx = named_idx
    return [("", " "), *_render_signature(name, spec, idx)]


# Default colour theme. Maps the style classes the `RobotLexer` emits
# (and the popup default classes) to ANSI / true-colour declarations.
# `rf.log.*` entries colour `log_message` / `message` output emitted by
# `PromptToolkitConsoleInterpreter` so the prompt and the Robot log lines
# share one palette.
_DEFAULT_STYLE = Style.from_dict(
    {
        "rf.keyword": "#5fafd7 bold",
        "rf.argument": "",
        "rf.assign": "#d75f87",
        "rf.comment": "#5f5f5f italic",
        "rf.block": "#d78700 bold",
        "rf.bdd": "#d78700 italic",
        "rf.variable.brace": "#5fd7af",
        "rf.variable.name": "#af87d7",
        "rf.variable.extended": "#af87d7 italic",
        "rf.variable.operator": "#5fd7af",
        "rf.variable.type": "#d7af5f",
        "rf.variable.expr": "#d75faf bold",
        "rf.variable.python": "#af87d7",
        "rf.toolbar.active-arg": "bold #d75f87",
        "rf.log.info": "#5faf5f",
        "rf.log.warn": "#d7af00",
        "rf.log.error": "#d75f5f",
        "rf.log.fail": "#d75f5f bold",
        "rf.log.skip": "#5f5f5f",
        "rf.log.debug": "#5f5f5f",
        "rf.log.trace": "#5f5f5f italic",
        "rf.kw.indicator": "#5fafd7",
    }
)


# Map Robot log levels to the corresponding `_DEFAULT_STYLE` class.
# Used by `PromptToolkitConsoleInterpreter.log_message` to colour the
# level tag without re-implementing `click.style`.
_LOG_LEVEL_STYLES = {
    "INFO": "class:rf.log.info",
    "WARN": "class:rf.log.warn",
    "ERROR": "class:rf.log.error",
    "FAIL": "class:rf.log.fail",
    "SKIP": "class:rf.log.skip",
    "DEBUG": "class:rf.log.debug",
    "TRACE": "class:rf.log.trace",
}

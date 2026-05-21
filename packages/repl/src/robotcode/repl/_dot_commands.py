"""Dot-prefixed REPL meta-commands.

Lines that start with ``.<word>`` are intercepted in
`ConsoleInterpreter.get_input` *before* Robot's parser ever sees
them — there's no Robot syntax that legitimately starts with a dot,
so the prefix is collision-free.

A dot-command never produces a Robot Keyword. It prints to stdout
through `Application.echo` (plain text) or `Application.echo_as_markdown`
(rich-rendered Markdown) and returns. Some commands raise `EOFError`
to drop out of the REPL or mutate the input backend's history file.
"""

import argparse
import inspect
import re
import shlex
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from robot.running.context import EXECUTION_CONTEXTS

from robotcode.robot.diagnostics.library_doc import (
    REST_DOC_FORMAT,
    ROBOT_DOC_FORMAT,
    convert_from_rest,
    get_library_doc,
)
from robotcode.robot.utils.markdownformatter import MarkDownFormatter

from ._completion import _LIB_KEYWORDS_ATTR, lookup_keyword_doc, lookup_library_doc
from ._session_export import render_robot_file

# The runtime `app` is a `robotcode.plugin.Application`; we type it as
# `Any` so test stubs and structural fakes work without subclassing.
# Handlers rely on `app.echo` / `app.echo_as_markdown`, which both
# real Applications and reasonable stubs provide.
Application = Any

# Line-shape: leading whitespace, dot, identifier, optional space + free-form rest.
_COMMAND_RE = re.compile(r"^\s*\.(\w+)(?:\s+(.*))?$")

# Variables that Robot itself sets in every suite — filtered out by
# `.vars --user` so the listing focuses on what the user assigned.
_ROBOT_INTERNAL_PREFIXES = (
    "CURDIR",
    "DEBUG_FILE",
    "EXEC",
    "FAILED",
    "KEYWORD",
    "LOG_",
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

_Handler = Callable[[Application, Any, str], None]
_REGISTRY: Dict[str, Tuple[_Handler, str]] = {}


def register(*names: str, help: str) -> Callable[[_Handler], _Handler]:
    """Bind one or more dot-command names to a handler.

    Aliases (e.g. ``.exit`` / ``.quit``) share their handler and help
    text by passing both names in one ``register`` call.
    """

    def decorator(fn: _Handler) -> _Handler:
        for name in names:
            _REGISTRY[name] = (fn, help)
        return fn

    return decorator


def dispatch(line: str, app: Application, interpreter: Any) -> bool:
    """Run the dot-command in ``line`` and return ``True`` on hit.

    Returns ``False`` when ``line`` doesn't match the ``.command``
    shape so the caller can route it through Robot's parser as a
    normal step.
    """
    m = _COMMAND_RE.match(line)
    if not m:
        return False
    name = m.group(1)
    arg = (m.group(2) or "").strip()
    entry = _REGISTRY.get(name)
    if entry is None:
        app.echo(f"Unknown dot-command: .{name}. Try .help.")
        return True
    handler, _ = entry
    handler(app, interpreter, arg)
    return True


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


def _short_doc_of(kw: Any) -> str:
    return (getattr(kw, "short_doc", None) or getattr(kw, "shortdoc", None) or "").split("\n", 1)[0]


# ---------------------------------------------------------------------------
# .help — list registered commands + shortcut hints
# ---------------------------------------------------------------------------


@register("help", help="List dot-commands. `.help <cmd>` shows details for one.")
def _help(app: Application, interpreter: Any, arg: str) -> None:
    """
    Without an argument: print the summary table of all dot-commands.
    With an argument: print the detailed help for that command (the
    leading dot is optional).

    Examples:
      .help
      .help save
      .help .history
    """
    del interpreter
    target = arg.strip().lstrip(".")
    if target:
        entry = _REGISTRY.get(target)
        if entry is None:
            app.echo(f"Unknown dot-command: .{target}. Try .help.")
            return
        handler, summary = entry
        detail = inspect.getdoc(handler) or "(no further details)"
        app.echo(f".{target} — {summary}\n\n{detail}")
        return

    width = max(len(name) for name in _REGISTRY)
    lines: List[str] = []
    for name in sorted(_REGISTRY):
        _, help_text = _REGISTRY[name]
        lines.append(f"  .{name:<{width}}  {help_text}")
    lines.append("")
    lines.append("  Type `.help <command>` for usage details.")
    lines.append("  Shortcuts: F1=help · Tab=complete · ^R=search · ^L=clear · ^D=exit")
    app.echo("\n".join(lines))


# ---------------------------------------------------------------------------
# .imports — loaded libraries / resources
# ---------------------------------------------------------------------------


@register("imports", help="List loaded libraries and resource files")
def _imports(app: Application, interpreter: Any, arg: str) -> None:
    """
    List every library and resource file the active REPL session has
    imported, along with the number of keywords each contributes and
    its source path.

    Usage:
      .imports
    """
    del interpreter, arg
    ctx = EXECUTION_CONTEXTS.current
    if ctx is None:
        app.echo("(no active context)")
        return
    store = getattr(ctx.namespace, "_kw_store", None)
    if store is None:
        app.echo("(no keyword store)")
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
        app.echo("(nothing imported)")
        return

    name_w = max(len(r[1]) for r in rows)
    for kind, name, source, count in rows:
        app.echo(f"  {kind:<8} {name:<{name_w}}  {count:>4} kw   {source}")


# ---------------------------------------------------------------------------
# .vars — variables in scope
# ---------------------------------------------------------------------------


@register("vars", help="Show variables in scope. Use --user to skip Robot internals.")
def _vars(app: Application, interpreter: Any, arg: str) -> None:
    """
    Print every variable visible in the current scope along with a
    truncated `repr()` of its value.

    Usage:
      .vars [--user]

    Options:
      --user   Hide Robot's built-in variables (`${SUITE_NAME}`,
               `${OUTPUT_DIR}`, `${TEMPDIR}`, …) so the listing focuses
               on what the user assigned in the session.
    """
    del interpreter
    ctx = EXECUTION_CONTEXTS.current
    if ctx is None:
        app.echo("(no active context)")
        return
    only_user = "--user" in arg.split()

    rows: List[Tuple[str, str]] = []
    for decorated, value in ctx.variables.as_dict().items():
        name = str(decorated)
        bare = name
        if len(name) > 2 and name[0] in "$@&%" and name[1] == "{" and name[-1] == "}":
            bare = name[2:-1]
        if only_user and any(bare.startswith(prefix) for prefix in _ROBOT_INTERNAL_PREFIXES):
            continue
        try:
            rep = repr(value)
        except Exception:
            rep = "<unprintable>"
        if len(rep) > 60:
            rep = rep[:59] + "…"
        rows.append((name, rep))

    if not rows:
        app.echo("(no variables)")
        return
    name_w = max(len(r[0]) for r in rows)
    for name, rep in rows:
        app.echo(f"  {name:<{name_w}}  {rep}")


# ---------------------------------------------------------------------------
# .kw — full doc for a single keyword
# ---------------------------------------------------------------------------


@register("kw", help="Show full documentation for a keyword: .kw <name>")
def _kw(app: Application, interpreter: Any, arg: str) -> None:
    """
    Render the full documentation of a single keyword as Markdown:
    signature, tags, docstring body, and source location. Name lookup
    is case-/whitespace-/underscore-insensitive (`Set Variable`,
    `set variable`, `set_variable` all match).

    Usage:
      .kw <keyword-name>

    Examples:
      .kw Log
      .kw Get From Dictionary
    """
    del interpreter
    if not arg:
        app.echo("Usage: .kw <keyword-name>")
        return
    kw = lookup_keyword_doc(arg)
    if kw is None:
        app.echo(f"No keyword found: {arg!r}")
        return

    md: List[str] = [f"### {getattr(kw, 'name', arg)}", ""]

    spec = getattr(kw, "args", None) or getattr(kw, "arguments", None)
    if spec is not None:
        try:
            sig = str(spec)
        except Exception:
            sig = ""
        if sig:
            md.append(f"`{kw.name}    {sig}`")
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

    app.echo_as_markdown("\n".join(md))


# ---------------------------------------------------------------------------
# .doc — full doc for a library / resource
# ---------------------------------------------------------------------------


@register("doc", help="Show full documentation for a library or resource: .doc <name>")
def _doc(app: Application, interpreter: Any, arg: str) -> None:
    """
    Render the full documentation of a library or resource file as
    Markdown: name, version, introduction, and the list of contained
    keywords with their short docstrings.

    Libraries that aren't currently imported are loaded fresh via
    `get_library_doc()` — that's a heavier call, but acceptable since
    it's an explicit user action.

    Usage:
      .doc <library-or-resource-name>

    Examples:
      .doc BuiltIn
      .doc Collections
      .doc SeleniumLibrary
    """
    del interpreter
    if not arg:
        app.echo("Usage: .doc <library-or-resource-name>")
        return
    lib = lookup_library_doc(arg)
    if lib is None:
        try:
            lib = get_library_doc(arg)
        except Exception as e:
            app.echo(f"Could not load {arg!r}: {e}")
            return

    md: List[str] = []
    header = f"## {getattr(lib, 'name', arg)}"
    version = getattr(lib, "version", None)
    if version:
        header += f"  _v{version}_"
    md.append(header)
    md.append("")
    scope = getattr(lib, "scope", None)
    if scope:
        md.append(f"_Scope: {scope}_")
        md.append("")

    doc = getattr(lib, "doc", None) or ""
    if doc:
        md.append(_format_doc_to_md(doc, getattr(lib, "doc_format", ROBOT_DOC_FORMAT)))

    # Both runtime libraries (`_kw_store.libraries.values()`) and
    # diagnostics LibraryDoc instances expose iterable keyword lists
    # via the same attribute we use for completion (`_LIB_KEYWORDS_ATTR`).
    keywords = list(getattr(lib, _LIB_KEYWORDS_ATTR, None) or [])
    if keywords:
        md.append("")
        md.append("### Keywords")
        md.append("")
        for kw in keywords:
            kw_name = getattr(kw, "name", "?")
            short = _short_doc_of(kw)
            md.append(f"- **{kw_name}** — {short}" if short else f"- **{kw_name}**")

    source = getattr(lib, "source", None)
    if source:
        md.append("")
        md.append(f"_Source: {source}_")

    app.echo_as_markdown("\n".join(md))


# ---------------------------------------------------------------------------
# .history — show, clear, delete entries
# ---------------------------------------------------------------------------


@register("history", help="Show / manage history: .history [N] | .history clear | .history del <N>")
def _history(app: Application, interpreter: Any, arg: str) -> None:
    """
    Show or manage the persistent REPL history. Entries are numbered
    so subsequent subcommands can refer to them by index.

    Usage:
      .history [N]        Show the last N entries (default 20).
      .history clear      Wipe all entries (in-memory + on-disk).
      .history del <N>    Delete a single entry by its 1-based index
                          (use `.history` to look up the number).

    Examples:
      .history 50
      .history del 12
    """
    tokens = arg.split()
    if tokens and tokens[0] == "clear":
        interpreter._input.clear_history()
        app.echo("History cleared.")
        return
    if tokens and tokens[0] == "del":
        if len(tokens) < 2 or not tokens[1].lstrip("-").isdigit():
            app.echo("Usage: .history del <N>")
            return
        idx = int(tokens[1])
        if interpreter._input.delete_history_entry(idx):
            app.echo(f"Deleted history entry {idx}.")
        else:
            app.echo(f"No history entry at index {idx}.")
        return

    n = int(tokens[0]) if tokens and tokens[0].isdigit() else 20
    entries = interpreter._input.get_history()
    if not entries:
        app.echo("(no history)")
        return
    start = max(0, len(entries) - n)
    width = len(str(len(entries)))
    for i in range(start, len(entries)):
        first, *rest = entries[i].split("\n")
        app.echo(f"  {i + 1:>{width}}  {first}")
        for line in rest:
            app.echo(f"  {' ' * width}  {line}")


# ---------------------------------------------------------------------------
# .clear — wipe the screen
# ---------------------------------------------------------------------------


@register("clear", help="Clear the screen")
def _clear_screen(app: Application, interpreter: Any, arg: str) -> None:
    """Erase the terminal screen and move the cursor back to the top."""
    del interpreter, arg
    # Standard "erase display + cursor home" ANSI sequence.
    app.echo("\x1b[2J\x1b[H", nl=False)


# ---------------------------------------------------------------------------
# .cwd — show the current working directory
# ---------------------------------------------------------------------------


@register("cwd", help="Show the current working directory")
def _cwd(app: Application, interpreter: Any, arg: str) -> None:
    """
    Print the current working directory — the base path that relative
    `Import Resource`, `Import Library`, and file-based variable
    references resolve against.
    """
    del interpreter, arg
    try:
        app.echo(str(Path.cwd()))
    except OSError as e:
        app.echo(f"(working directory unavailable: {e})")


# ---------------------------------------------------------------------------
# .exit / .quit — drop out of the REPL
# ---------------------------------------------------------------------------


@register("exit", "quit", help="Exit the REPL")
def _exit(app: Application, interpreter: Any, arg: str) -> None:
    """
    Leave the REPL. Equivalent to pressing Ctrl-D on an empty prompt.
    `.exit` and `.quit` are aliases.
    """
    del app, interpreter, arg
    raise EOFError


# ---------------------------------------------------------------------------
# .save — export the session as a runnable `.robot` file
# ---------------------------------------------------------------------------


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


@register("save", help="Save session as a .robot file: .save [-a] [-t NAME] FILENAME")
def _save(app: Application, interpreter: Any, arg: str) -> None:
    """
    Save the current REPL session as a runnable `.robot` file. Only
    inputs that round-tripped through Robot's parser are exported;
    failed lines are silently skipped so the result stays runnable
    with `robot <filename>`.

    Imports are hoisted into a `*** Settings ***` section (so
    `Import Library    Collections` becomes `Library    Collections`).
    Everything else lands in a single `*** Test Cases ***` block.

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
    parser = _build_save_parser()
    try:
        opts = parser.parse_args(_split_command_args(arg))
    except (argparse.ArgumentError, SystemExit, ValueError):
        app.echo("Usage: .save [-a] [-t NAME] FILENAME")
        return

    lines: List[str] = list(getattr(interpreter, "_session_lines", []) or [])
    if not lines:
        app.echo("Nothing to save — the session has no recorded inputs yet.")
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
        app.echo(f"Could not write {opts.filename}: {e}")
        return

    app.echo(f"Wrote {path} ({len(lines)} entries)")

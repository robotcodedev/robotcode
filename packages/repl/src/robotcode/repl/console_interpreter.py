"""Plain-mode interactive Robot Framework interpreter.

The ``ConsoleInterpreter`` is the REPL's plain implementation: it wraps
Robot's runtime, reads lines from stdin (via ``input()``), routes
dot-commands through `@dot_command`-decorated methods, and emits log
output via ``click.style`` + ``app.echo``. The prompt_toolkit-aware
version overrides only the methods that benefit from prompt_toolkit's
richer surface (see ``prompt_toolkit_interpreter`` for that subclass).
"""

import argparse
import inspect
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, TypeVar, Union

import click
from robot import result, running
from robot.running import Keyword
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.plugin import Application
from robotcode.robot.diagnostics.library_doc import (
    REST_DOC_FORMAT,
    ROBOT_DOC_FORMAT,
    convert_from_rest,
    get_library_doc,
)
from robotcode.robot.utils import get_robot_version_str
from robotcode.robot.utils.markdownformatter import MarkDownFormatter

from .__version__ import __version__
from ._indent import compute_indent
from ._keyword_lookup import _LIB_KEYWORDS_ATTR, lookup_keyword_doc, lookup_library_doc
from ._session_export import render_robot_file
from .base_interpreter import BaseInterpreter, is_true

F = TypeVar("F", bound=Callable[..., Any])

# Line shape: optional whitespace, dot, identifier, optional space + free-form rest.
# No Robot syntax legitimately starts with a dot, so the prefix is collision-free.
_COMMAND_RE = re.compile(r"^\s*\.(\w+)(?:\s+(.*))?$")


def dot_command(*names: str) -> Callable[[F], F]:
    """Mark a ``ConsoleInterpreter`` method as a dot-command handler.

    Method signature: ``def _name(self, arg: str) -> None``. The first
    non-blank line of the docstring is the short summary that ``.help``
    lists; the full docstring is what ``.help <name>`` prints in the
    doc viewer. Multiple names register the same method as aliases —
    ``.exit`` / ``.quit`` share their handler that way.
    """

    def decorator(method: F) -> F:
        method._dot_command_names = names  # type: ignore[attr-defined]
        return method

    return decorator


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


def _upgrade_to_diagnostics_keyword(runtime_kw: Any, kw_name: str) -> Optional[Any]:
    """Try to load the diagnostics `KeywordDoc` for a runtime keyword.

    `lookup_keyword_doc` returns the runtime object (a `StaticKeyword`
    in RF 7+, an old-style handler before that) — those carry `name` /
    `args` / `doc` strings but no `to_markdown`. The diagnostics
    `KeywordDoc` does, with proper signature + arg table rendering.

    We bridge by reading the runtime keyword's library name (`owner`
    in RF 7+, falls back to the `libname` carried on some keyword
    types), re-loading that library via `get_library_doc`, and
    looking up the keyword by name in the resulting `KeywordStore`.

    Returns ``None`` for resource keywords, user keywords, or any
    case where the diagnostics loader can't help — the caller falls
    back to hand-building markdown from runtime fields.
    """
    owner = getattr(runtime_kw, "owner", None) or getattr(runtime_kw, "parent", None)
    owner_name = getattr(owner, "name", None) or getattr(runtime_kw, "libname", None)
    if not owner_name:
        return None
    try:
        lib_doc = get_library_doc(owner_name)
    except Exception:
        return None
    matches: List[Any] = []
    keywords = getattr(lib_doc, "keywords", None)
    if keywords is None:
        return None
    get_all = getattr(keywords, "get_all", None)
    if callable(get_all):
        try:
            matches = list(get_all(kw_name))
        except Exception:
            matches = []
    return matches[0] if matches else None


def _render_runtime_library_md(lib: Any, arg: str) -> str:
    """Hand-built fallback library page for resources / dynamic libs.

    Used only when `get_library_doc(arg)` can't load the import — the
    diagnostics path covers every regular library so this code only
    fires for `Import Resource` files and similar. Keeps the rendering
    minimal: heading, optional version + scope, raw markdown of the
    doc, then a flat keyword listing.
    """
    lib_name = getattr(lib, "name", arg)
    md: List[str] = []
    header = f"## {lib_name}"
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

    keywords = list(getattr(lib, _LIB_KEYWORDS_ATTR, None) or [])
    if keywords:
        md.append("")
        md.append("### Keywords")
        md.append("")
        for kw in keywords:
            kw_name = getattr(kw, "name", "?")
            md.append(f"- **{kw_name}**")

    source = getattr(lib, "source", None)
    if source:
        md.append("")
        md.append(f"_Source: {source}_")
    return "\n".join(md)


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

    # ------------------------------------------------------------------
    # Dot-command dispatch — the table is computed once per interpreter
    # class (`cls.__dict__.get` skips the base's cache when looking from
    # a subclass, so `PromptToolkitConsoleInterpreter` builds its own
    # the first time `.history` is dispatched).
    # ------------------------------------------------------------------

    @classmethod
    def _dot_command_table(cls) -> Dict[str, str]:
        """Per-class ``{name: method_attr_name}`` for every ``@dot_command`` on this class or its bases."""
        cached: Optional[Dict[str, str]] = cls.__dict__.get("_DOT_COMMAND_TABLE")
        if cached is not None:
            return cached
        table: Dict[str, str] = {}
        for klass in reversed(cls.__mro__):
            for attr_name, attr in vars(klass).items():
                for name in getattr(attr, "_dot_command_names", ()):
                    table[name] = attr_name
        cls._DOT_COMMAND_TABLE = table  # type: ignore[attr-defined]
        return table

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
        attr_name = type(self)._dot_command_table().get(name)
        if attr_name is None:
            if self.app is not None:
                self.app.echo(f"Unknown dot-command: .{name}. Try .help.")
            return True
        getattr(self, attr_name)(arg)
        return True

    # ------------------------------------------------------------------
    # I/O — the prompt_toolkit subclass overrides both to drive its own
    # Application; the plain implementation here uses stdlib `input()`
    # and pages markdown through the Application's pager helper.
    # ------------------------------------------------------------------

    def read_line(self, prompt: str, *, multiline_continuation: bool = False, prefill: str = "") -> str:
        del multiline_continuation, prefill  # no editor, no prefill, no continuation prompt
        return input(prompt)

    def show_doc(self, title: str, markdown: str) -> None:
        """Display markdown to the user.

        Plain mode pages the raw markdown source with colour off — the
        backend choice signals "low-fi terminal", so we don't surface
        rich-rendered markdown the user explicitly opted out of. The
        prompt_toolkit interpreter overrides this with the scrollable
        doc-viewer Float.
        """
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
        return super().run()

    # ------------------------------------------------------------------
    # Robot integration
    # ------------------------------------------------------------------

    def set_last_result(self, result: Any) -> None:
        """Mirror the last keyword's return value into Robot as ``${_}``.

        ``None`` results are skipped so noisy ``Log`` / ``Set Suite
        Variable`` calls don't wipe a meaningful previous value.
        """
        super().set_last_result(result)
        if result is None:
            return
        ctx = EXECUTION_CONTEXTS.current
        if ctx is None:
            return
        try:
            ctx.variables["${_}"] = result
        except Exception:
            # Locked scope / shutdown phase — drop the binding rather
            # than crash the REPL.
            pass

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

        self.app.echo(f"{'  ' * self.indent}[ {level} ] {message}", file=sys.__stdout__ if std_err else sys.__stderr__)

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
        target = arg.strip().lstrip(".")
        table = type(self)._dot_command_table()
        if target:
            attr_name = table.get(target)
            if attr_name is None:
                if self.app is not None:
                    self.app.echo(f"Unknown dot-command: .{target}. Try .help.")
                return
            method = getattr(self, attr_name)
            detail = inspect.getdoc(method) or "(no further details)"
            summary = _first_doc_line(method)
            body = f"**{summary}**\n\n```\n{detail}\n```"
            self.show_doc(f".{target}", body)
            return

        md_lines: List[str] = ["## Dot-commands", ""]
        for name in sorted(table):
            summary = _first_doc_line(getattr(self, table[name])) or "(no description)"
            md_lines.append(f"- **`.{name}`** — {summary}")
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

    @dot_command("vars")
    def _vars(self, arg: str) -> None:
        """Show variables in scope. Use --user to skip Robot internals.

        Print every variable visible in the current scope along with a
        truncated `repr()` of its value.

        Usage:
          .vars [--user]

        Options:
          --user   Hide Robot's built-in variables (`${SUITE_NAME}`,
                   `${OUTPUT_DIR}`, `${TEMPDIR}`, …) so the listing focuses
                   on what the user assigned in the session.
        """
        if self.app is None:
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
            self.app.echo("(no variables)")
            return
        name_w = max(len(r[0]) for r in rows)
        for name, rep in rows:
            self.app.echo(f"  {name:<{name_w}}  {rep}")

    @dot_command("kw")
    def _kw(self, arg: str) -> None:
        """Show full documentation for a keyword: .kw <name>

        Renders the keyword's signature (with argument types + defaults),
        full docstring, tags, and source via the project's own
        `KeywordDoc.to_markdown(...)` — the same routine the language
        server uses for hover/signature help, so the bash view matches
        what the editor surfaces.

        Name lookup is case-/whitespace-/underscore-insensitive
        (`Set Variable`, `set variable`, `set_variable` all match).

        Usage:
          .kw <keyword-name>

        Examples:
          .kw Log
          .kw Get From Dictionary
        """
        if self.app is None:
            return
        if not arg:
            self.app.echo("Usage: .kw <keyword-name>")
            return
        kw = lookup_keyword_doc(arg)
        if kw is None:
            self.app.echo(f"No keyword found: {arg!r}")
            return

        kw_name = getattr(kw, "name", arg)

        # Prefer the diagnostics `KeywordDoc` — it carries
        # `to_markdown(...)` with proper signature + arg table + types,
        # which the runtime keyword object (`StaticKeyword`) doesn't.
        diag_kw = _upgrade_to_diagnostics_keyword(kw, kw_name)
        if diag_kw is not None:
            self.show_doc(kw_name, diag_kw.to_markdown(header_level=1))
            return

        # Fallback for resource keywords / dynamic libraries the
        # diagnostics loader can't introspect — hand-build a minimal
        # page from whatever the runtime object exposes.
        self.show_doc(kw_name, _render_runtime_keyword_md(kw, kw_name))

    @dot_command("doc")
    def _doc(self, arg: str) -> None:
        """Show full documentation for a library or resource: .doc <name>

        Renders the full library page via
        `LibraryDoc.to_markdown(only_doc=False, header_level=1)` —
        version + scope table, introduction (with `%TOC%` expanded
        and inline `[Other Kw](\\#anchor)` links resolved), then every
        keyword with its signature, argument table, and full doc body.
        Same renderer the language server uses for hover info, so this
        view stays in sync with what the editor shows.

        Libraries that aren't currently imported are loaded fresh via
        `get_library_doc()` — heavier call, but acceptable since it's
        an explicit user action.

        Usage:
          .doc <library-or-resource-name>

        Examples:
          .doc BuiltIn
          .doc Collections
        """
        if self.app is None:
            return
        if not arg:
            self.app.echo("Usage: .doc <library-or-resource-name>")
            return

        # Try the diagnostics loader first — it returns a `LibraryDoc`
        # whose `to_markdown` is the renderer we want. Resources
        # imported via `Import Resource` aren't libraries; for those
        # the diagnostics loader raises and we fall back to the
        # runtime store, where we hand-build a minimal page.
        diag_error: Optional[Exception] = None
        lib: Optional[Any] = None
        try:
            lib = get_library_doc(arg)
        except Exception as e:
            diag_error = e
            lib = lookup_library_doc(arg)

        if lib is None:
            self.app.echo(f"Could not load {arg!r}: {diag_error}")
            return

        lib_name = getattr(lib, "name", arg)

        if hasattr(lib, "to_markdown"):
            body = lib.to_markdown(only_doc=False, header_level=1)
        else:
            body = _render_runtime_library_md(lib, arg)

        self.show_doc(lib_name, body)

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
        `.exit` and `.quit` are aliases.
        """
        del arg
        raise EOFError

    @dot_command("save")
    def _save(self, arg: str) -> None:
        """Save session as a .robot file: .save [-a] [-t NAME] FILENAME

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
